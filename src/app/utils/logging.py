import logging
import logging.config
from pathlib import Path
from typing import Optional, Dict, Any
import json
from ..config import settings

def configure_logging(
    config_file: Optional[str] = None,
    default_level: int = logging.INFO,
    env_override: bool = True
) -> None:
    """
    Configure logging for the application.
    
    Args:
        config_file: Path to logging configuration JSON file
        default_level: Default logging level if config file not found
        env_override: Whether to override config with environment variables
    """
    config = get_base_config(default_level)
    
    # Try to load config file if specified
    if config_file:
        try:
            file_path = Path(config_file)
            with open(file_path, 'r') as f:
                file_config = json.load(f)
            config = merge_configs(config, file_config)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load logging config: {e}. Using defaults.")

    # Apply environment overrides
    if env_override:
        config = apply_env_overrides(config)

    # Apply configuration
    logging.config.dictConfig(config)
    
    # Capture warnings via logging
    logging.captureWarnings(True)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured")

def get_base_config(default_level: int) -> Dict[str, Any]:
    """Return base logging configuration"""
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '''
                    asctime: %(asctime)s
                    levelname: %(levelname)s
                    name: %(name)s
                    message: %(message)s
                    pathname: %(pathname)s
                    lineno: %(lineno)d
                '''
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'level': default_level,
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'json',
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'file'],
                'level': default_level,
                'propagate': True
            },
            'src.app': {
                'level': logging.DEBUG,
                'propagate': False
            }
        }
    }

def merge_configs(base: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two logging configurations"""
    # Deep merge dictionaries
    merged = base.copy()
    for key, value in custom.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged

def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to logging config"""
    # Example: Could check settings.LOG_LEVEL, etc.
    if settings.app_env == 'production':
        config['handlers']['console']['level'] = logging.WARNING
        config['loggers']['']['level'] = logging.INFO
    elif settings.app_env == 'development':
        config['handlers']['console']['level'] = logging.DEBUG
        config['loggers']['']['level'] = logging.DEBUG
    
    return config