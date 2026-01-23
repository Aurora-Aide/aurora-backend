from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone


def _device_token_ttl():
    minutes = getattr(settings, "DEVICE_TOKEN_TTL_MINUTES", 60)
    try:
        return timedelta(minutes=int(minutes))
    except (TypeError, ValueError):
        return timedelta(minutes=60)


def issue_device_token(dispenser):
    """
    Create a signed JWT for a dispenser device. Token contains:
    - sub: serial_id
    - rev: dispenser.device_session_rev (used for revocation/rotation)
    - type: "device"
    """
    now = timezone.now()
    exp = now + _device_token_ttl()
    payload = {
        "sub": dispenser.serial_id,
        "rev": dispenser.device_session_rev,
        "type": "device",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(
        payload,
        getattr(settings, "DEVICE_TOKEN_SECRET", settings.SECRET_KEY),
        algorithm=getattr(settings, "DEVICE_TOKEN_ALGORITHM", "HS256"),
    )
    return token, exp


def decode_device_token(token):
    """
    Decode and verify a device token. Raises jwt exceptions on failure/expiry.
    """
    return jwt.decode(
        token,
        getattr(settings, "DEVICE_TOKEN_SECRET", settings.SECRET_KEY),
        algorithms=[getattr(settings, "DEVICE_TOKEN_ALGORITHM", "HS256")],
    )

