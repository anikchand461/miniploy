"""Render platform handler."""
import os
import time
from typing import Dict, Optional
import requests
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
        """Create a new service on Render."""
        if not self.owner_id:
            raise Exception("Owner ID not found. Please authenticate first.")
        
        name = self.config.get('name', 'my-service')
        runtime = self.config.get('runtime', 'python')
        repo_url = self.config.get('repo_url')
        branch = self.config.get('branch', 'main')
        dockerfile_path = self.config.get('dockerfile', 'Dockerfile')
        build_command = self.config.get('build_command')
        start_command = self.config.get('start_command')
        publish_dir = self.config.get('publish_dir', '.')

        if runtime == 'docker':
            if not repo_url:
                raise Exception("Render Docker deploy requires a Git repository URL.")
            payload = {
                'type': 'web_service',
                'name': name,
                'ownerId': self.owner_id,
                'repo': repo_url,
                'branch': branch,
                'autoDeploy': True,
                'env': 'docker'
            }
        elif runtime == 'static':
            payload = {
                'type': 'static_site',
                'name': name,
                'ownerId': self.owner_id,
                'autoDeploy': False,
                'buildCommand': build_command or '',
                'publishPath': publish_dir
            }
            if repo_url:
                payload['repo'] = repo_url
                payload['branch'] = branch
        else:
            runtime_map = {
                'python': 'python',
                'node': 'node',
                'nodejs': 'node',
                'go': 'go',
                'ruby': 'ruby',
                'php': 'php'
            }
            env = runtime_map.get(runtime, 'docker')
            payload = {
                'type': 'web_service',
                'name': name,
                'ownerId': self.owner_id,
                'autoDeploy': True,
                'env': env,
                'buildCommand': build_command or '',
                'startCommand': start_command or ''
            }
            if repo_url:
                payload['repo'] = repo_url
                payload['branch'] = branch
        
        url = f"{self.BASE_URL}/services"
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', response.text)
                raise Exception(f"{response.status_code} - {error_msg}")
            
            data = response.json()
            if not data or not data.get('service'):
                raise Exception("Invalid response: missing service data")
            
            return data['service'].get('id') or str(data['service'])
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Failed to create Render service: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to create Render service: {str(e)}")
    
    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment variables for a Render service."""
        url = f"{self.BASE_URL}/services/{project_id}/env-vars"
        
        env_vars = [{'key': k, 'value': v} for k, v in envs.items()]
        
        response = requests.put(
            url,
            headers=self.headers,
            json=env_vars,
            timeout=10
        )
        response.raise_for_status()
    
    def trigger_deploy(self, project_id: str) -> str:
        """Trigger a new deploy."""
        url = f"{self.BASE_URL}/services/{project_id}/deploys"
        
        payload = {'clearCache': False}
        
        response = requests.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get('id', '')
    
    def get_status(self, project_id: str) -> Dict:
        """Get service deployment status."""
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
            service_url = data.get('service', {}).get('serviceDetails', {}).get('url')
            return service_url
        
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
                    'status': svc.get('suspended', 'N/A') == 'not_suspended' and 'active' or 'inactive',
                    'created_at': svc.get('createdAt', 'N/A')
                })
            
            return result
        except Exception:
            return []
