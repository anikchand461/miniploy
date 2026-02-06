"""Configuration manager for miniploy.yaml."""
import os
import yaml
from pathlib import Path
from typing import Dict, Optional


CONFIG_FILENAME = "miniploy.yaml"


def find_config_file(start_path: str = ".") -> Optional[Path]:
    """Find miniploy.yaml in current directory or parents."""
    current = Path(start_path).resolve()
    
    for parent in [current] + list(current.parents):
        config_path = parent / CONFIG_FILENAME
        if config_path.exists():
            return config_path
    
    return None


def load_config(path: Optional[str] = None) -> Dict:
    """
    Load configuration from miniploy.yaml.
    
    Args:
        path: Explicit config file path, or None to search
        
    Returns:
        Configuration dictionary
    """
    if path:
        config_path = Path(path)
    else:
        config_path = find_config_file()
    
    if not config_path or not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise ValueError(f"Failed to load config from {config_path}: {e}")


def save_config(config: Dict, path: Optional[str] = None) -> Path:
    """
    Save configuration to miniploy.yaml.
    
    Args:
        config: Configuration dictionary to save
        path: Explicit config file path, or None to use current directory
        
    Returns:
        Path where config was saved
    """
    if path:
        config_path = Path(path)
    else:
        config_path = Path.cwd() / CONFIG_FILENAME
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return config_path
    except Exception as e:
        raise ValueError(f"Failed to save config to {config_path}: {e}")


def get_platform(config: Dict) -> Optional[str]:
    """Extract platform name from config."""
    return config.get('platform')


def get_project_id(config: Dict) -> Optional[str]:
    """Extract project ID from config."""
    return config.get('project_id')


def get_env_vars(config: Dict) -> Dict[str, str]:
    """Extract environment variables from config."""
    return config.get('env_vars', {})