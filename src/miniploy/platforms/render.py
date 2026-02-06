"""Render platform handler."""
import os
import requests
from typing import Dict, Optional
from .base import PlatformHandler


class RenderHandler(PlatformHandler):
    """Handler for Render platform operations using REST API."""
    
    BASE_URL = "https://api.render.com/v1"

    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get('token') or os.getenv('RENDER_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.owner_id = None

    def authenticate(self) -> bool:
        """Verify Render token is valid and get owner ID."""
        try:
            url = f"{self.BASE_URL}/owners"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                owners = response.json()
                if owners and len(owners) > 0:
                    self.owner_id = owners[0].get('owner', {}).get('id')
                return True
            return False
        except Exception:
            return False

    def create_project(self) -> str:
        """Create a Render service: static_site or web_service based on config."""
        if not self.owner_id:
            raise Exception("Owner ID not found. Please authenticate first.")

        name = self.config.get('name')
        repo_url = self.config.get('repo')
        branch = self.config.get('branch', 'main')
        language = self.config.get('language', 'static')
        root_dir = self.config.get('root_directory', '')
        build_cmd = self.config.get('build_command', '')
        start_cmd = self.config.get('start_command', '')
        instance_type = self.config.get('instance_type', 'free')

        if not name:
            raise Exception("Project name is required.")
        if not repo_url:
            raise Exception("GitHub repo URL ('repo') is required.")

        # --- STATIC SITE ---
        if language == "static":
            payload = {
                "type": "static_site",
                "name": name,
                "ownerId": self.owner_id,
                "repo": repo_url,
                "branch": branch,
                "autoDeploy": False
            }
            if build_cmd:
                payload["buildCommand"] = build_cmd
            # Only include publicDirectory if it's a real subdirectory (not '.' or empty)
            if root_dir and root_dir.strip() not in ('.', ''):
                payload["publicDirectory"] = root_dir.strip()

        # --- WEB SERVICE (python, node, go, ruby, docker) ---
        else:
            runtime_map = {
                "node": "node",
                "python": "python",
                "go": "go",
                "ruby": "ruby",
                "docker": "docker"
            }
            env = runtime_map.get(language, "docker")

            payload = {
                "type": "web_service",
                "name": name,
                "ownerId": self.owner_id,
                "repo": repo_url,
                "branch": branch,
                "env": env,
                "region": "oregon",  # Default region
                "plan": instance_type,
                "autoDeploy": False
            }
            if build_cmd:
                payload["buildCommand"] = build_cmd
            if start_cmd:
                payload["startCommand"] = start_cmd
            if root_dir and root_dir.strip() not in ('.', ''):
                payload["rootDir"] = root_dir.strip()

        # Send request to Render API
        url = f"{self.BASE_URL}/services"
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    message = error_data.get('message', response.text)
                except Exception:
                    message = response.text
                raise Exception(f"{response.status_code} - {message}")

            data = response.json()
            service = data.get('service') or data
            return service.get('id') or str(service)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during Render service creation: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to create Render service: {str(e)}")

    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment variables for a Render service."""
        if not envs:
            return
        url = f"{self.BASE_URL}/services/{project_id}/env-vars"
        env_vars = [{'key': k, 'value': v} for k, v in envs.items()]
        response = requests.put(url, headers=self.headers, json=env_vars, timeout=10)
        response.raise_for_status()

    def trigger_deploy(self, project_id: str) -> str:
        """Trigger a new deploy."""
        url = f"{self.BASE_URL}/services/{project_id}/deploys"
        payload = {'clearCache': False}
        response = requests.post(url, headers=self.headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json().get('id', '')

    def get_status(self, project_id: str) -> Dict:
        """Get latest deployment status."""
        url = f"{self.BASE_URL}/services/{project_id}/deploys"
        params = {'limit': 1}
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            deploy = data[0]
            return {
                'state': deploy.get('status', 'UNKNOWN'),
                'url': None
            }
        return {'state': 'NONE', 'url': None}

    def get_logs(self, project_id: str) -> str:
        """Get deployment logs."""
        return "Logs available in Render dashboard"

    def get_url(self, project_id: str) -> Optional[str]:
        """Get the deployed service URL."""
        url = f"{self.BASE_URL}/services/{project_id}"
        response = requests.get(url, headers=self.headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('service', {}).get('serviceDetails', {}).get('url')
        return None

    def list_deployments(self, limit: int = 10) -> list:
        """List services."""
        url = f"{self.BASE_URL}/services"
        params = {'limit': limit}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            services = data if isinstance(data, list) else data.get('services', [])
            result = []
            for service in services[:limit]:
                svc = service.get('service', service)
                result.append({
                    'name': svc.get('name', 'N/A'),
                    'url': svc.get('serviceDetails', {}).get('url', 'N/A'),
                    'status': 'active' if svc.get('suspended') == 'not_suspended' else 'inactive',
                    'created_at': svc.get('createdAt', 'N/A')
                })
            return result
        except Exception:
            return []
