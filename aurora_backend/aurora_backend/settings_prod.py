"""
Production settings.
"""

import os
from .settings_base import *

DEBUG = False

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", SECRET_KEY)
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host] or []

# Harden cookies/transport; adjust if behind a proxy/terminating TLS.
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True if SECURE_HSTS_SECONDS else False
SECURE_HSTS_PRELOAD = True if SECURE_HSTS_SECONDS else False
SECURE_SSL_REDIRECT = False  # enable when TLS termination is configured

