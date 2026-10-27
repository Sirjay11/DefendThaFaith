import os
import json
from pathlib import Path
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HERMES_LOCAL_DIR = Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes"
HERMES_ENV_PATH = HERMES_LOCAL_DIR / ".env"
HERMES_CONFIG_PATH = HERMES_LOCAL_DIR / "config.yaml"

# Load project .env first, then fallback to local Hermes .env so OpenRouter works out of the box
load_dotenv(PROJECT_ROOT / ".env")
if HERMES_ENV_PATH.exists():
    load_dotenv(HERMES_ENV_PATH, override=False)


def load_hermes_model_settings() -> dict:
    """Reads the user's local Hermes config.yaml to inherit OpenRouter free models."""
    defaults = {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "nvidia/nemotron-3-super-120b-a12b:free",
        "fallback_models": [
            "nvidia/nemotron-3.5-lightning:free",
            "z-ai/glm-5.2:free",
            "openrouter/free",
        ],
    }
    if not HERMES_CONFIG_PATH.exists():
        return defaults
    try:
        with open(HERMES_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        model_cfg = cfg.get("model", {})
        fallbacks = [
            fb.get("model")
            for fb in cfg.get("fallback_providers", [])
            if isinstance(fb, dict) and fb.get("model")
        ]
        if "openrouter/free" not in fallbacks:
            fallbacks.append("openrouter/free")
        return {
            "provider": model_cfg.get("provider", defaults["provider"]),
            "base_url": model_cfg.get("base_url", defaults["base_url"]),
            "default_model": model_cfg.get("default", defaults["default_model"]),
            "fallback_models": fallbacks or defaults["fallback_models"],
        }
    except Exception:
        return defaults


HERMES_SETTINGS = load_hermes_model_settings()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DATABASE_PATH = DATA_DIR / "defendthafaith.db"
