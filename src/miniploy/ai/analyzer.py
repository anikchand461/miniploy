"""AI-powered project analysis using Groq LLM."""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from groq import Groq


SYSTEM_PROMPT = """You are an expert DevOps engineer analyzing projects for deployment.
Analyze the provided project files and return ONLY a valid JSON object with this exact structure:
{
  "framework": "nextjs|react|vue|angular|flask|fastapi|django|express|static|unknown",
    "runtime": "node|python|go|ruby|php|static|docker",
  "build_command": "npm run build",
  "start_command": "npm start",
  "install_command": "npm install",
  "publish_dir": "out|dist|build|public|.",
  "env_vars_needed": ["DATABASE_URL", "API_KEY"],
  "summary": "Brief description of detected project type",
  "confidence": 0.95,
  "platform_recommendations": {
    "vercel": {"score": 0.9, "reason": "Next.js detected, optimal for Vercel"},
    "netlify": {"score": 0.8, "reason": "Static site, good fit"},
    "render": {"score": 0.7, "reason": "Supports all frameworks"},
    "railway": {"score": 0.7, "reason": "Good for full-stack apps"},
    "flyio": {"score": 0.6, "reason": "Container-based deployment"}
  }
}

Be precise. Return ONLY valid JSON, no markdown, no explanations."""


def _scan_files(path: str) -> Dict[str, str]:
    """Scan project directory for key configuration files."""
    target_files = [
        'package.json', 'requirements.txt', 'pyproject.toml', 'Pipfile',
        'Dockerfile', 'docker-compose.yml', 'next.config.js', 'next.config.mjs',
        'vite.config.js', 'vite.config.ts', 'nuxt.config.js', 'nuxt.config.ts',
        'angular.json', 'vue.config.js', 'gatsby-config.js',
        'app.py', 'main.py', 'manage.py', 'wsgi.py', 'asgi.py',
        'index.html', 'index.js', 'index.ts', 'server.js', 'app.js',
        'go.mod', 'Gemfile', 'composer.json', 'Cargo.toml'
    ]
    
    found_files = {}
    path_obj = Path(path).resolve()
    
    # Scan root directory and one level deep
    for root, dirs, files in os.walk(path_obj):
        # Skip node_modules, venv, etc.
        dirs[:] = [d for d in dirs if d not in {
            'node_modules', '.git', '__pycache__', 'venv', '.venv', 
            'env', 'dist', 'build', '.next', 'out'
        }]
        
        depth = len(Path(root).relative_to(path_obj).parts)
        if depth > 2:  # Don't go too deep
            continue
            
        for file in files:
            if file in target_files:
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    # Limit content size
                    if len(content) > 5000:
                        content = content[:5000] + "\n... (truncated)"
                    found_files[str(file_path.relative_to(path_obj))] = content
                except Exception:
                    pass
    
    return found_files


def analyze_project(path: str) -> Dict:
    """
    Analyze project files and use Groq LLM for intelligent configuration suggestions.
    
    Args:
        path: Project directory path
        
    Returns:
        Dictionary with framework, build/start commands, and platform recommendations
    """
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return {
            "framework": "unknown",
            "runtime": "unknown",
            "build_command": "",
            "start_command": "",
            "install_command": "",
            "publish_dir": ".",
            "env_vars_needed": [],
            "summary": "ERROR: GROQ_API_KEY not set in environment",
            "confidence": 0.0,
            "platform_recommendations": {}
        }
    
    # Scan project files
    found_files = _scan_files(path)
    
    if not found_files:
        return {
            "framework": "static",
            "runtime": "static",
            "build_command": "",
            "start_command": "",
            "install_command": "",
            "publish_dir": ".",
            "env_vars_needed": [],
            "summary": "No configuration files found - assuming static site",
            "confidence": 0.3,
            "platform_recommendations": {
                "netlify": {"score": 0.8, "reason": "Good for static sites"},
                "vercel": {"score": 0.7, "reason": "Supports static sites"}
            }
        }
    
    # Build context for LLM
    context = {
        "files": found_files,
        "file_list": list(found_files.keys())
    }
    
    try:
        client = Groq(api_key=api_key)
        model = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, indent=2)}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Clean up markdown if present
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join(lines[1:-1] if len(lines) > 2 else lines)
        
        result = json.loads(content)

        # If Dockerfile exists, prefer docker runtime
        if any(Path(p).name == "Dockerfile" for p in found_files.keys()):
            result["runtime"] = "docker"
            result["dockerfile"] = "Dockerfile"
            summary = result.get("summary", "")
            if "Dockerfile" not in summary:
                result["summary"] = (summary + " Dockerfile detected.").strip()
        
        # Validate required fields
        required_fields = ['framework', 'summary', 'confidence']
        for field in required_fields:
            if field not in result:
                result[field] = "unknown" if field != "confidence" else 0.5
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            "framework": "unknown",
            "runtime": "unknown",
            "build_command": "",
            "start_command": "",
            "install_command": "",
            "publish_dir": ".",
            "env_vars_needed": [],
            "summary": f"AI response parsing error: {str(e)}",
            "confidence": 0.0,
            "platform_recommendations": {}
        }
    except Exception as e:
        return {
            "framework": "unknown",
            "runtime": "unknown",
            "build_command": "",
            "start_command": "",
            "install_command": "",
            "publish_dir": ".",
            "env_vars_needed": [],
            "summary": f"Analysis error: {str(e)}",
            "confidence": 0.0,
            "platform_recommendations": {}
        }
