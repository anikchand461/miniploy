class PlatformHandler:
    """Abstract base class for platform handlers."""

    def __init__(self, config: dict):
        self.config = config

    def authenticate(self) -> bool:
        """Authenticate with the platform. Returns True if successful."""
        raise NotImplementedError

    def create_project(self) -> str:
        """Create a project on the platform. Returns project ID."""
        raise NotImplementedError

    def set_env_vars(self, project_id: str, envs: dict):
        """Set environment variables for the project."""
        raise NotImplementedError

    def trigger_deploy(self, project_id: str):
        """Trigger deployment for the project."""
        raise NotImplementedError

    def get_status(self, project_id: str):
        """Get the deployment status of the project."""
        raise NotImplementedError

    def get_logs(self, project_id: str):
        """Get logs for the deployment."""
        raise NotImplementedError

    def get_url(self, project_id: str):
        """Get the URL of the deployed project."""
        raise NotImplementedError
