"""
Settings loader that delegates to environment-specific profiles.
Defaults to base settings; use DJANGO_SETTINGS_PROFILE=local|prod to override.
"""

import os
from importlib import import_module

from .settings_base import *  # noqa: F401,F403

PROFILE = os.getenv("DJANGO_SETTINGS_PROFILE")
if PROFILE:
    try:
        module = import_module(f"aurora_backend.settings_{PROFILE}")
        globals().update({k: v for k, v in module.__dict__.items() if k.isupper()})
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"Unknown DJANGO_SETTINGS_PROFILE '{PROFILE}'") from exc