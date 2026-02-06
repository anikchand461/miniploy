"""Netlify platform handler."""
import os
import time
import zipfile
from pathlib import Path
from typing import Dict, Optional
import requests
from .base import PlatformHandler


class NetlifyHandler(PlatformHandler):
    """Handler for Netlify platform operations using REST API v1."""
    
    BASE_URL = "https://api.netlify.com/api/v1"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get('token') or os.getenv('NETLIFY_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def authenticate(self) -> bool:
        """Verify Netlify token is valid."""
        try:
            url = f"{self.BASE_URL}/user"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def create_project(self) -> str:
        """Create a new site on Netlify."""
        site_name = self.config.get('name', 'my-site')
        
        # Create a minimal site without repo - can be linked later
        payload = {
            'name': site_name
        }
        
        url = f"{self.BASE_URL}/sites"
        
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
            if not data or 'id' not in data:
                raise Exception("Invalid response: missing site ID")
            
            return data['id']
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Failed to create Netlify site: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to create Netlify site: {str(e)}")
    
    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment variables for a Netlify site."""
        url = f"{self.BASE_URL}/accounts/{project_id}/env"
        
        for key, value in envs.items():
            payload = {
                'key': key,
                'values': [{'value': value, 'context': 'all'}]
            }
            requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
    
    def trigger_deploy(self, project_id: str) -> str:
        """Trigger a new build."""
        url = f"{self.BASE_URL}/sites/{project_id}/builds"
        
        response = requests.post(
            url,
            headers=self.headers,
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get('id', '')
    
    def get_status(self, project_id: str) -> Dict:
        """Get site deployment status."""
        url = f"{self.BASE_URL}/sites/{project_id}"
        
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return {
            'state': data.get('published_deploy', {}).get('state', 'UNKNOWN'),
            'url': data.get('url')
        }
    
    def get_logs(self, project_id: str) -> str:
        """Get recent deploy logs."""
        url = f"{self.BASE_URL}/sites/{project_id}/deploys"
        params = {'per_page': 1}
        
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        
        if response.status_code == 200:
            deploys = response.json()
            if deploys:
                return deploys[0].get('summary', {}).get('messages', [])
        
        return "No logs available"
    
    def get_url(self, project_id: str) -> Optional[str]:
        """Get the deployed site URL."""
        status = self.get_status(project_id)
        return status.get('url')
    
    def deploy_static_files(self, site_name: str, files_dir: str = ".") -> Dict:
        """
        Deploy static files to Netlify using ZIP upload.
        
        Args:
            site_name: Name for the site
            files_dir: Directory containing files to deploy
            
        Returns:
            Deployment information including URL
        """
        import random
        import string
        
        files_path = Path(files_dir).resolve()
        
        # Make site name unique by adding random suffix
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        unique_site_name = f"{site_name}-{random_suffix}"
        
        # Create a zip file of all files
        import tempfile
        zip_path = Path(tempfile.mktemp(suffix='.zip'))
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files_path.rglob('*'):
                    if file_path.is_file():
                        # Skip hidden files and common ignores
                        if file_path.name.startswith('.') or 'node_modules' in file_path.parts:
                            continue
                        
                        relative_path = file_path.relative_to(files_path)
                        zipf.write(file_path, relative_path)
            
            # First, create a site
            create_url = f"{self.BASE_URL}/sites"
            site_payload = {'name': unique_site_name}
            
            create_response = requests.post(
                create_url,
                headers=self.headers,
                json=site_payload,
                timeout=15
            )
            
            if create_response.status_code >= 400:
                error_data = create_response.json() if create_response.text else {}
                error_msg = error_data.get('message', create_response.text)
                raise Exception(f"{create_response.status_code} - {error_msg}")
            
            site_data = create_response.json()
            site_id = site_data.get('id')
            
            # Upload the zip file
            deploy_url = f"{self.BASE_URL}/sites/{site_id}/deploys"
            
            with open(zip_path, 'rb') as f:
                files = {'file': ('site.zip', f, 'application/zip')}
                headers_without_content_type = {k: v for k, v in self.headers.items() if k != 'Content-Type'}
                
                deploy_response = requests.post(
                    deploy_url,
                    headers=headers_without_content_type,
                    files=files,
                    timeout=60
                )
            
            if deploy_response.status_code >= 400:
                error_data = deploy_response.json() if deploy_response.text else {}
                error_msg = error_data.get('message', deploy_response.text)
                raise Exception(f"{deploy_response.status_code} - {error_msg}")
            
            deploy_data = deploy_response.json()
            
            # Wait for deployment to be ready
            deploy_id = deploy_data.get('id')
            max_wait = 30  # seconds
            waited = 0
            
            while waited < max_wait:
                status_url = f"{self.BASE_URL}/sites/{site_id}/deploys/{deploy_id}"
                status_response = requests.get(status_url, headers=self.headers, timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    state = status_data.get('state', '')
                    
                    if state == 'ready':
                        # Get the final site info with correct URL
                        site_url = f"{self.BASE_URL}/sites/{site_id}"
                        site_response = requests.get(site_url, headers=self.headers, timeout=10)
                        if site_response.status_code == 200:
                            final_site = site_response.json()
                            return {
                                'id': deploy_id,
                                'site_id': site_id,
                                'url': final_site.get('ssl_url') or final_site.get('url'),
                                'status': 'ready',
                                'admin_url': final_site.get('admin_url')
                            }
                    elif state == 'error':
                        raise Exception(f"Deployment failed: {status_data.get('error_message', 'Unknown error')}")
                
                time.sleep(2)
                waited += 2
            
            # If we timed out, still return what we have
            return {
                'id': deploy_id,
                'site_id': site_id,
                'url': site_data.get('ssl_url') or site_data.get('url'),
                'status': deploy_data.get('state', 'processing'),
                'admin_url': site_data.get('admin_url')
            }
            
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Failed to deploy to Netlify: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to deploy to Netlify: {str(e)}")
        finally:
            # Clean up zip file
            if zip_path.exists():
                zip_path.unlink()
    
    def list_deployments(self, limit: int = 10) -> list:
        """List all sites."""
        url = f"{self.BASE_URL}/sites"
        params = {'per_page': limit}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            sites = response.json()
            
            result = []
            for site in sites:
                result.append({
                    'name': site.get('name', 'N/A'),
                    'url': site.get('ssl_url') or site.get('url', 'N/A'),
                    'status': 'active' if site.get('published_deploy') else 'inactive',
                    'created_at': site.get('created_at', 'N/A')
                })
            
            return result
        except Exception:
            return []
