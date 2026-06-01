import json
import logging
import os
import time
from datetime import timedelta
from urllib import error, request

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from .models import MobilePushToken

logger = logging.getLogger(__name__)
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_cached_credentials = None
_cached_credentials_file = None
_google_auth_request = GoogleAuthRequest()


def _get_access_token(credentials_file: str):
    """
    Retrieve a valid Google OAuth access token with lightweight retries.
    Cache credentials object in-process so we don't refresh for every event.
    """
    global _cached_credentials, _cached_credentials_file

    if (
        _cached_credentials is None
        or _cached_credentials_file != credentials_file
    ):
        _cached_credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=[FCM_SCOPE],
        )
        _cached_credentials_file = credentials_file

    credentials = _cached_credentials

    # Refresh if missing or nearing expiry.
    needs_refresh = (
        not credentials.token
        or not credentials.expiry
        or credentials.expiry <= timezone.now() + timedelta(seconds=60)
    )
    if not needs_refresh:
        return credentials.token

    last_exc = None
    for attempt in range(1, 4):
        try:
            credentials.refresh(_google_auth_request)
            if credentials.token:
                return credentials.token
        except Exception as exc:  # pragma: no cover - network/runtime variability
            last_exc = exc
            logger.warning(
                "FCM token refresh attempt %s/3 failed: %s",
                attempt,
                exc,
            )
            if attempt < 3:
                time.sleep(0.5 * attempt)

    raise RuntimeError(f"Failed to refresh FCM access token: {last_exc}")


def _build_message(*, status: str, pill_name: str, dispenser_name: str):
    if status == "completed":
        title = "Pill dropped"
        body = f"{pill_name} was dispensed from {dispenser_name}."
    else:
        title = "Missed pill"
        body = f"Missed dose for {pill_name} on {dispenser_name}."
    return title, body


def send_push_for_schedule_event(*, dispenser, container, status: str, occurred_at, schedule_id=None):
    """
    Send FCM push notifications for dropped/missed events.
    Failures are logged and never raised to keep device ingestion stable.
    """
    if not getattr(settings, "FCM_PUSH_ENABLED", False):
        logger.info("Skipping FCM push: disabled by FCM_PUSH_ENABLED=False")
        return
    project_id = getattr(settings, "FCM_PROJECT_ID", "").strip()
    credentials_file = getattr(settings, "FCM_SERVICE_ACCOUNT_FILE", "").strip() or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not project_id:
        logger.warning("Skipping FCM push: FCM_PROJECT_ID is not configured")
        return
    if not credentials_file:
        logger.warning("Skipping FCM push: FCM_SERVICE_ACCOUNT_FILE/GOOGLE_APPLICATION_CREDENTIALS is not configured")
        return
    if dispenser.owner_id is None:
        logger.info("Skipping FCM push: dispenser has no owner")
        return

    tokens = list(
        MobilePushToken.objects.filter(user_id=dispenser.owner_id, is_active=True).values_list("token", flat=True)
    )
    if not tokens:
        logger.info("Skipping FCM push: no active MobilePushToken for user_id=%s", dispenser.owner_id)
        return

    pill_name = container.pill_name if container else "Pill"
    title, body = _build_message(status=status, pill_name=pill_name, dispenser_name=dispenser.name)

    try:
        access_token = _get_access_token(credentials_file)
    except Exception as exc:
        logger.warning("Skipping FCM push: failed to load service account credentials: %s", exc)
        return

    invalid_tokens = []
    sent_count = 0
    for token in tokens:
        payload = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": {
                    "status": status,
                    "dispenser_id": str(dispenser.id),
                    "container_slot": str(container.slot_number) if container else "",
                    "occurred_at": occurred_at.isoformat(),
                    "schedule_id": str(schedule_id) if schedule_id is not None else "",
                    "title": title,
                    "body": body,
                },
                "android": {"priority": "high"},
            }
        }
        http_request = request.Request(
            url=f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json; UTF-8",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )

        sent = False
        for attempt in range(1, 4):
            try:
                with request.urlopen(http_request, timeout=5):
                    sent_count += 1
                    sent = True
                    break
            except error.HTTPError as exc:
                raw = exc.read().decode("utf-8") if exc.fp else ""
                if exc.code in {400, 404} and ("UNREGISTERED" in raw or "registration-token-not-registered" in raw):
                    invalid_tokens.append(token)
                logger.warning("FCM v1 send failed for token: code=%s body=%s", exc.code, raw)
                break
            except (error.URLError, TimeoutError) as exc:
                logger.warning("FCM transport failure for token (attempt %s/3): %s", attempt, exc)
                if attempt < 3:
                    time.sleep(0.3 * attempt)
            except Exception as exc:  # pragma: no cover - safety net
                logger.exception("Unexpected FCM push failure for token: %s", exc)
                break
        if not sent:
            logger.info("FCM push not sent for token after retries")

    logger.info("FCM v1 push done: user_id=%s, sent=%s/%s", dispenser.owner_id, sent_count, len(tokens))
    if invalid_tokens:
        MobilePushToken.objects.filter(token__in=invalid_tokens).update(
            is_active=False,
            last_seen_at=timezone.now(),
        )

    return
