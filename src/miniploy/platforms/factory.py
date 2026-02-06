from .vercel import VercelHandler
from .netlify import NetlifyHandler
from .render import RenderHandler
from .railway import RailwayHandler
from .flyio import FlyioHandler

class PlatformHandler:
    def setup(self, config):
        raise NotImplementedError

    def deploy(self, config):
        raise NotImplementedError


def get_platform_handler(platform_name: str):
    """Return the appropriate platform handler based on the platform name."""
    handlers = {
        'vercel': VercelHandler,
        'netlify': NetlifyHandler,
        'render': RenderHandler,
        'railway': RailwayHandler,
        'flyio': FlyioHandler,
    }
    return handlers.get(platform_name.lower())
