from django.utils.translation import gettext_lazy as _
from rest_framework import authentication, exceptions
from rest_framework.authentication import get_authorization_header

from .models import Dispenser
from .device_tokens import decode_device_token


class DeviceAuthentication(authentication.BaseAuthentication):
    """
    Simple header-based auth for dispenser devices.
    Expects:
      - URL kwarg serial_id
      - Header X-Device-Secret: <secret>
    """

    keyword = "X-Device-Secret"

    def authenticate(self, request):
        serial_id = request.parser_context.get("kwargs", {}).get("serial_id")
        if not serial_id:
            return None

        secret = request.headers.get(self.keyword)
        if not secret:
            raise exceptions.AuthenticationFailed(_("Missing device secret"))

        dispenser = Dispenser.objects.filter(serial_id=serial_id).first()
        if not dispenser or not dispenser.device_secret:
            raise exceptions.AuthenticationFailed(_("Unknown device"))

        if dispenser.device_secret != secret:
            raise exceptions.AuthenticationFailed(_("Invalid device secret"))

        # Return (user, auth) tuple. Use owner as acting user if present; otherwise anonymous.
        return (dispenser.owner if dispenser.owner else None, dispenser)


class DeviceSessionAuthentication(authentication.BaseAuthentication):
    """
    Bearer token auth for dispenser devices.
    Expects:
      - URL kwarg serial_id
      - Authorization: Bearer <device_jwt>
    """

    keyword = "bearer"

    def authenticate(self, request):
        serial_id = request.parser_context.get("kwargs", {}).get("serial_id")
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.encode():
            return None
        if len(auth) == 1:
            raise exceptions.AuthenticationFailed(_("Invalid Authorization header. No credentials provided."))
        if len(auth) > 2:
            raise exceptions.AuthenticationFailed(_("Invalid Authorization header. Token string should not contain spaces."))

        token = auth[1].decode()

        try:
            payload = decode_device_token(token)
        except Exception:
            raise exceptions.AuthenticationFailed(_("Invalid or expired device token"))

        token_serial = payload.get("sub")
        token_rev = payload.get("rev")

        if not token_serial or token_rev is None:
            raise exceptions.AuthenticationFailed(_("Invalid device token payload"))

        if serial_id and token_serial != serial_id:
            raise exceptions.AuthenticationFailed(_("Serial ID mismatch"))

        dispenser = Dispenser.objects.filter(serial_id=token_serial).first()
        if not dispenser:
            raise exceptions.AuthenticationFailed(_("Unknown device"))

        if dispenser.device_session_rev != token_rev:
            raise exceptions.AuthenticationFailed(_("Device token revoked"))

        return (dispenser.owner if dispenser.owner else None, dispenser)


