from .main import app  # Makes 'app' available directly from package
from .config import settings

__all__ = ["app", "settings"]  # Controls what 'from src.app import *' includes