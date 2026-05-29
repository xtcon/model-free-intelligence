"""Configuration management for MFI."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

MFI_HOME_ENV = "MFI_HOME"

DEFAULT_CONFIG: Dict[str, Any] = {
    "hermes_home": os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")),
    "sessions_dir": "sessions",
    "skills_dir": "skills",
    "retention_days": 90,
    "correction_keywords": [
        "不对", "错了", "不是", "重来", "注意",
        "应该", "不该", "不要", "别", "不是这样",
        "wrong", "incorrect", "no,", "not right",
        "fix", "correct", "that's not",
    ],
    "evolution": {
        "enabled": True,
        "max_corrections_per_run": 10,
        "min_confidence": 0.3,
        "dedup_window_hours": 24,
    },
    "dashboard": {
        "port": 9908,
        "history_days": 30,
    },
}


def default_config_path() -> Path:
    home = Path(os.environ.get(MFI_HOME_ENV, str(Path.home() / ".mfi")))
    return home / "config.json"


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load MFI config, merging with defaults."""
    config = dict(DEFAULT_CONFIG)

    cfg_path = path or default_config_path()
    if cfg_path.exists():
        try:
            with open(cfg_path) as f:
                user_config = json.load(f)
            _deep_merge(config, user_config)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[mfi] warning: failed to load config {cfg_path}: {e}")

    return config


def save_config(config: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Save config to file."""
    cfg_path = path or default_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"[mfi] config saved to {cfg_path}")


def init_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Initialize default config, preserving existing if already present."""
    cfg_path = path or default_config_path()
    if cfg_path.exists():
        print(f"[mfi] config already exists at {cfg_path}")
        return load_config(cfg_path)
    save_config(DEFAULT_CONFIG, cfg_path)
    return dict(DEFAULT_CONFIG)


def resolve_paths(config: Dict[str, Any]) -> Dict[str, Path]:
    """Resolve hermes paths from config."""
    hermes_home = Path(config["hermes_home"])
    return {
        "hermes_home": hermes_home,
        "sessions": hermes_home / config["sessions_dir"],
        "skills": hermes_home / config["skills_dir"],
        "sessions_index": hermes_home / config["sessions_dir"] / "sessions.json",
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override into base (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
