"""Vercel platform handler."""
import os
import time
import base64
from pathlib import Path
from typing import Dict, Optional, List
import requests
from .base import PlatformHandler


class VercelHandler(PlatformHandler):
    """Handler for Vercel platform operations using REST API v10+."""
    
    BASE_URL = "https://api.vercel.com"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get('token') or os.getenv('VERCEL_TOKEN')
        self.team_id = config.get('team_id')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.user_info = None
    
    def authenticate(self) -> bool:
        """Verify Vercel token is valid and get user info."""
        try:
            url = f"{self.BASE_URL}/v2/user"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                self.user_info = response.json()
                return True
            return False
        except Exception:
            return False
    
    def create_project(self) -> str:
        """Create a new project on Vercel."""
        project_name = self.config.get('name', 'my-project')
        framework = self.config.get('framework', 'other')
        
        url = f"{self.BASE_URL}/v9/projects"
        params = {}
        if self.team_id:
            params['teamId'] = self.team_id
        
        # Simplified payload - Vercel can create empty projects
        payload = {
            'name': project_name,
            'framework': framework if framework != 'unknown' else None
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            response = requests.post(
                url, 
                headers=self.headers, 
                json=payload, 
                params=params,
                timeout=15
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', response.text)
                raise Exception(f"{response.status_code} - {error_msg}")
            
            data = response.json()
            return data.get('id') or data.get('name') or str(data)
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Failed to create Vercel project: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to create Vercel project: {str(e)}")
    
    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment variables for a Vercel project."""
        url = f"{self.BASE_URL}/v9/projects/{project_id}/env"
        params = {}
        if self.team_id:
            params['teamId'] = self.team_id
        
        for key, value in envs.items():
            payload = {
                'key': key,
                'value': value,
                'type': 'encrypted',
                'target': ['production', 'preview', 'development']
            }
            requests.post(
                url, 
                headers=self.headers, 
                json=payload, 
                params=params,
                timeout=10
            )
    
    def trigger_deploy(self, project_id: str) -> str:
        """Trigger a new deployment (requires git integration)."""
        url = f"{self.BASE_URL}/v13/deployments"
        params = {}
        if self.team_id:
            params['teamId'] = self.team_id
        
        payload = {
            'name': project_id,
            'gitSource': self.config.get('git_repository', {})
        }
        
        response = requests.post(
            url,
            headers=self.headers,
            json=payload,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get('id', '')
    
    def get_status(self, project_id: str) -> Dict:
        """Get deployment status."""
        url = f"{self.BASE_URL}/v6/deployments"
        params = {'projectId': project_id, 'limit': 1}
        if self.team_id:
            params['teamId'] = self.team_id
        
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        deployments = data.get('deployments', [])
        if deployments:
            return {
                'state': deployments[0].get('readyState', 'UNKNOWN'),
                'url': deployments[0].get('url')
            }
        return {'state': 'NONE', 'url': None}
    
    def get_logs(self, project_id: str) -> str:
        """Get deployment logs (limited in API)."""
        return "Logs available in Vercel dashboard"
    
    def get_url(self, project_id: str) -> Optional[str]:
        """Get the deployed URL."""
        status = self.get_status(project_id)
        url = status.get('url')
        return f"https://{url}" if url else None
    
    def deploy_static_files(self, project_name: str, files_dir: str = ".") -> Dict:
        """
        Deploy static files to Vercel.
        
        Args:
            project_name: Name for the deployment
            files_dir: Directory containing files to deploy
            
        Returns:
            Deployment information including URL
        """
        files_path = Path(files_dir).resolve()
        
        # Collect all files
        file_list = []
        for file_path in files_path.rglob('*'):
            if file_path.is_file():
                # Skip hidden files and common ignores
                if file_path.name.startswith('.') or 'node_modules' in file_path.parts:
                    continue
                
                relative_path = file_path.relative_to(files_path)
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Base64 encode the content
                encoded_content = base64.b64encode(content).decode('utf-8')
                
                file_list.append({
                    'file': str(relative_path).replace('\\', '/'),
                    'data': encoded_content,
                    'encoding': 'base64'
                })
        
        if not file_list:
            raise Exception("No files found to deploy")
        
        # Create deployment payload
        url = f"{self.BASE_URL}/v13/deployments"
        params = {}
        if self.team_id:
            params['teamId'] = self.team_id
        
        payload = {
            'name': project_name,
            'files': file_list,
            'projectSettings': {
                'framework': None
            }
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                params=params,
                timeout=60  # Longer timeout for file upload
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', response.text)
                raise Exception(f"{response.status_code} - {error_msg}")
            
            data = response.json()
            
            return {
                'id': data.get('id'),
                'url': data.get('url'),
                'status': data.get('readyState', 'BUILDING'),
                'inspectorUrl': data.get('inspectorUrl')
            }
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Failed to deploy to Vercel: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to deploy to Vercel: {str(e)}")
    
    def list_deployments(self, limit: int = 10) -> list:
        """List recent deployments."""
        url = f"{self.BASE_URL}/v6/deployments"
        params = {'limit': limit}
        if self.team_id:
            params['teamId'] = self.team_id
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            deployments = data.get('deployments', [])
            
            result = []
            for deploy in deployments:
                result.append({
                    'name': deploy.get('name', 'N/A'),
                    'url': deploy.get('url', 'N/A'),
                    'status': deploy.get('readyState', 'UNKNOWN'),
                    'created_at': deploy.get('createdAt', 'N/A')
                })
            
            return result
        except Exception:
            return []
