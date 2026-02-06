"""Railway platform handler."""
import os
import time
from typing import Dict, Optional
import requests
from .base import PlatformHandler


class RailwayHandler(PlatformHandler):
    """Handler for Railway platform operations using GraphQL API."""
    
    BASE_URL = "https://backboard.railway.com/graphql/v2"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get('token') or os.getenv('RAILWAY_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.user_info = None
        self.workspace_id = None
    
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
        """Verify Railway token is valid and get workspace/team info."""
        try:
            # Try account token first (query me)
            query = """
            query {
              me {
                id
                email
                teams {
                  edges {
                    node {
                      id
                      name
                    }
                  }
                }
              }
            }
            """
            result = self._graphql_request(query)
            
            if 'data' in result and result['data'].get('me') is not None:
                self.user_info = result['data']['me']
                
                # Get first team as workspace
                teams = result['data']['me'].get('teams', {}).get('edges', [])
                if teams and len(teams) > 0:
                    self.workspace_id = teams[0]['node']['id']
                
                return True
            return False
        except Exception:
            # If me query fails, try workspace token query (get projects)
            try:
                query = """
                query {
                  projects {
                    edges {
                      node {
                        id
                        name
                        team {
                          id
                          name
                        }
                      }
                    }
                  }
                }
                """
                result = self._graphql_request(query)
                
                if 'data' in result and result['data'].get('projects') is not None:
                    projects = result['data']['projects'].get('edges', [])
                    if projects and len(projects) > 0:
                        # Get workspace from first project
                        team = projects[0]['node'].get('team')
                        if team:
                            self.workspace_id = team['id']
                    return True
                return False
            except Exception:
                return False
    
    def create_project(self) -> str:
        """Create a new project on Railway."""
        if not self.workspace_id:
            raise Exception("Workspace ID not found. Please authenticate first or join a team.")
        
        project_name = self.config.get('name', 'my-project')
        
        query = """
        mutation ProjectCreate($input: ProjectCreateInput!) {
          projectCreate(input: $input) {
            id
            name
          }
        }
        """
        
        variables = {
            'input': {
                'name': project_name,
                'teamId': self.workspace_id
            }
        }
        
        try:
            result = self._graphql_request(query, variables)
            
            # Check for GraphQL errors
            if 'errors' in result:
                errors = result.get('errors', [])
                error_msg = errors[0].get('message', 'Unknown error') if errors else 'Unknown error'
                raise Exception(f"GraphQL Error: {error_msg}")
            
            # Extract project ID
            data = result.get('data')
            if not data or not data.get('projectCreate'):
                raise Exception("Invalid response: missing projectCreate data")
            
            return data['projectCreate']['id']
        except Exception as e:
            raise Exception(f"Failed to create Railway project: {str(e)}")
    
    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment variables for a Railway project."""
        # Note: Railway requires service ID, not just project ID
        # This is a simplified implementation
        query = """
        mutation VariablesSet($projectId: String!, $environmentId: String!, $variables: EnvironmentVariables!) {
          variablesSet(
            input: {
              projectId: $projectId
              environmentId: $environmentId
              variables: $variables
            }
          )
        }
        """
        
        # Would need actual environment ID - simplified here
        pass
    
    def trigger_deploy(self, project_id: str) -> str:
        """Trigger a new deployment (via git push typically)."""
        query = """
        mutation DeploymentTrigger($projectId: String!) {
          deploymentTrigger(input: {projectId: $projectId}) {
            id
          }
        }
        """
        
        variables = {'projectId': project_id}
        result = self._graphql_request(query, variables)
        
        return result.get('data', {}).get('deploymentTrigger', {}).get('id', '')
    
    def get_status(self, project_id: str) -> Dict:
        """Get project deployment status."""
        query = """
        query Project($id: String!) {
          project(id: $id) {
            id
            name
            services {
              edges {
                node {
                  id
                  name
                }
              }
            }
          }
        }
        """
        
        variables = {'id': project_id}
        result = self._graphql_request(query, variables)
        
        project = result.get('data', {}).get('project', {})
        return {
            'state': 'ACTIVE' if project else 'UNKNOWN',
            'url': None
        }
    
    def get_logs(self, project_id: str) -> str:
        """Get deployment logs."""
        return "Logs available in Railway dashboard"
    
    def list_deployments(self, limit: int = 10) -> list:
        """List projects."""
        query = """
        query Projects {
          projects {
            edges {
              node {
                id
                name
                createdAt
                services {
                  edges {
                    node {
                      id
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        try:
            result = self._graphql_request(query)
            projects = result.get('data', {}).get('projects', {}).get('edges', [])
            
            deployments = []
            for edge in projects[:limit]:
                project = edge.get('node', {})
                deployments.append({
                    'name': project.get('name', 'N/A'),
                    'url': 'N/A',  # Railway doesn't expose URLs via API
                    'status': 'active' if project.get('services', {}).get('edges') else 'inactive',
                    'created_at': project.get('createdAt', 'N/A')
                })
            
            return deployments
        except Exception:
            return []
    
    def get_url(self, project_id: str) -> Optional[str]:
        """Get the deployed project URL."""
        # Railway URLs are service-specific
        return f"https://railway.app/project/{project_id}"
