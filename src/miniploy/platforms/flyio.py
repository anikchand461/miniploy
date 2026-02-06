"""Fly.io platform handler."""
import os
import time
from typing import Dict, Optional
import requests
from .base import PlatformHandler


class FlyioHandler(PlatformHandler):
    """Handler for Fly.io platform operations using GraphQL API."""
    
    BASE_URL = "https://api.fly.io/graphql"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get('token') or os.getenv('FLY_API_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.user_info = None
        self.org_slug = None
        self.org_id = None
    
    def _graphql_request(self, query: str, variables: dict = None) -> Dict:
        """Execute a GraphQL request."""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        response = requests.post(
            self.BASE_URL,
            headers=self.headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    
    def authenticate(self) -> bool:
        """Verify Fly.io token is valid and get organization info."""
        try:
            query = """
            query {
              viewer {
                id
                email
                organizations {
                  nodes {
                    id
                    slug
                    name
                  }
                }
              }
            }
            """
            result = self._graphql_request(query)
            
            if 'data' in result and result['data'].get('viewer') is not None:
                self.user_info = result['data']['viewer']
                
                # Get first organization
                orgs = result['data']['viewer'].get('organizations', {}).get('nodes', [])
                if orgs and len(orgs) > 0:
                  self.org_slug = orgs[0].get('slug')
                  self.org_id = orgs[0].get('id')
                
                return True
            return False
        except Exception:
            return False
    
    def create_project(self) -> str:
        """Create a new app on Fly.io."""
        if not self.org_id:
          raise Exception("Organization not found. Please authenticate first or create an organization.")
        
        app_name = self.config.get('name', 'my-app')
        
        query = """
        mutation CreateApp($input: CreateAppInput!) {
          createApp(input: $input) {
            app {
              id
              name
            }
          }
        }
        """
        
        variables = {
            'input': {
                'name': app_name,
                'organizationId': self.org_id
            }
        }
        
        try:
            result = self._graphql_request(query, variables)
            
            # Check for GraphQL errors
            if 'errors' in result:
                errors = result.get('errors', [])
                error_msg = errors[0].get('message', 'Unknown error') if errors else 'Unknown error'
                raise Exception(f"GraphQL Error: {error_msg}")
            
            # Extract app name
            data = result.get('data')
            if not data or not data.get('createApp'):
                raise Exception("Invalid response: missing createApp data")
            
            app = data['createApp'].get('app')
            if not app:
                raise Exception("Invalid response: missing app data")
            
            return app.get('name') or app.get('id')
        except Exception as e:
            raise Exception(f"Failed to create Fly.io app: {str(e)}")
    
    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment secrets for a Fly.io app."""
        query = """
        mutation SetSecrets($input: SetSecretsInput!) {
          setSecrets(input: $input) {
            release {
              id
              version
            }
          }
        }
        """
        
        variables = {
            'input': {
                'appId': project_id,
                'secrets': [{'key': k, 'value': v} for k, v in envs.items()]
            }
        }
        
        self._graphql_request(query, variables)
    
    def trigger_deploy(self, project_id: str) -> str:
        """Trigger a new deployment (typically via flyctl deploy)."""
        # Fly.io deployments are usually done via CLI, not API
        # This is a placeholder
        return "Deploy via: flyctl deploy"
    
    def get_status(self, project_id: str) -> Dict:
        """Get app status."""
        query = """
        query GetApp($name: String!) {
          app(name: $name) {
            id
            name
            status
            hostname
          }
        }
        """
        
        variables = {'name': project_id}
        result = self._graphql_request(query, variables)
        
        app = result.get('data', {}).get('app', {})
        return {
            'state': app.get('status', 'UNKNOWN'),
            'url': app.get('hostname')
        }
    
    def get_logs(self, project_id: str) -> str:
        """Get app logs."""
        return "Use: flyctl logs -a " + project_id
    
    def get_url(self, project_id: str) -> Optional[str]:
        """Get the deployed app URL."""
        status = self.get_status(project_id)
        hostname = status.get('url')
        return f"https://{hostname}" if hostname else None
    
    def list_deployments(self, limit: int = 10) -> list:
        """List apps."""
        query = """
        query Apps {
          apps {
            nodes {
              id
              name
              status
              hostname
              createdAt
            }
          }
        }
        """
        
        try:
            result = self._graphql_request(query)
            apps = result.get('data', {}).get('apps', {}).get('nodes', [])
            
            deployments = []
            for app in apps[:limit]:
                hostname = app.get('hostname', '')
                deployments.append({
                    'name': app.get('name', 'N/A'),
                    'url': f"https://{hostname}" if hostname else 'N/A',
                    'status': app.get('status', 'unknown').lower(),
                    'created_at': app.get('createdAt', 'N/A')
                })
            
            return deployments
        except Exception:
            return []
