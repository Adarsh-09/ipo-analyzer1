"""
IPOVision Configuration Loader
Provides centralized, reproducible access to project settings and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict

# Base Project Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

# Attempt to load environment variables via python-dotenv if installed
try:
    from dotenv import load_dotenv
    ENV_PATH = PROJECT_ROOT / ".env"
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        load_dotenv()
except ImportError:
    # python-dotenv not yet installed in bare environment
    pass

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def get_project_root() -> Path:
    """Returns the absolute Path to the IPOVision root directory."""
    return PROJECT_ROOT


def load_settings(custom_path: str | None = None) -> Dict[str, Any]:
    """
    Loads project settings from YAML.
    Prefers 'config/settings.yaml', falls back to 'config/settings.example.yaml'.
    """
    if not _HAS_YAML:
        raise ImportError(
            "PyYAML is not installed in the current Python environment. "
            "Please create and activate your virtual environment, then install dependencies: "
            "pip install -r requirements.txt"
        )

    if custom_path:
        settings_file = Path(custom_path)
    else:
        local_settings = PROJECT_ROOT / "config" / "settings.yaml"
        example_settings = PROJECT_ROOT / "config" / "settings.example.yaml"
        settings_file = local_settings if local_settings.exists() else example_settings

    if not settings_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {settings_file}. "
            "Please ensure 'config/settings.example.yaml' exists."
        )

    with open(settings_file, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    return settings


def get_path(path_key: str, settings: Dict[str, Any] | None = None) -> Path:
    """
    Resolves a relative path defined in settings to an absolute Path.
    
    Args:
        path_key: Key in settings['paths'] (e.g. 'data_processed', 'models_dir')
        settings: Pre-loaded settings dictionary (optional)
        
    Returns:
        Absolute Path object
    """
    if settings is None:
        settings = load_settings()

    rel_path = settings.get("paths", {}).get(path_key)
    if not rel_path:
        raise KeyError(f"Path key '{path_key}' not found in configuration paths.")

    return PROJECT_ROOT / rel_path


def get_gemini_api_key() -> str | None:
    """Retrieves the Gemini API key from environment variables."""
    return os.getenv("GEMINI_API_KEY")
