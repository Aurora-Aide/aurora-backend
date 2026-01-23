from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from authentication.models import User
from dispensers.models import Container, Schedule, ScheduleEvent
from dispensers.services import create_dispenser_for_user


class DeviceSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="pass12345",
            first_name="Owner",
            last_name="User",
        )
        self.dispenser = create_dispenser_for_user(
            owner=self.user, name="MyDisp", serial_id="S-20250101-0999"
        )

    def test_session_token_allows_config_access(self):
        session_url = reverse("device-session", args=[self.dispenser.serial_id])
        resp = self.client.post(session_url, HTTP_X_DEVICE_SECRET=self.dispenser.device_secret)
        self.assertEqual(resp.status_code, 200)
        token = resp.data["token"]

        config_url = reverse("device-config", args=[self.dispenser.serial_id])
        resp_config = self.client.get(config_url, HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(resp_config.status_code, 200)
        self.assertEqual(resp_config.data["serial_id"], self.dispenser.serial_id)

    def test_rev_increment_revokes_token(self):
        session_url = reverse("device-session", args=[self.dispenser.serial_id])
        resp = self.client.post(session_url, HTTP_X_DEVICE_SECRET=self.dispenser.device_secret)
        self.assertEqual(resp.status_code, 200)
        token = resp.data["token"]

        # Simulate rotation by bumping rev
        self.dispenser.device_session_rev += 1
        self.dispenser.save(update_fields=["device_session_rev"])

        config_url = reverse("device-config", args=[self.dispenser.serial_id])
        resp_config = self.client.get(config_url, HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(resp_config.status_code, 401)

    def test_device_config_updates_last_seen_and_clears_dirty(self):
        # mark dirty and clear last_seen to ensure API updates it
        self.dispenser.dirty = True
        self.dispenser.last_seen_at = None
        self.dispenser.save(update_fields=["dirty", "last_seen_at"])

        url = reverse("device-config", args=[self.dispenser.serial_id])
        resp = self.client.get(url, HTTP_X_DEVICE_SECRET=self.dispenser.device_secret)

        self.assertEqual(resp.status_code, 200)
        self.dispenser.refresh_from_db()
        self.assertFalse(self.dispenser.dirty)
        self.assertIsNotNone(self.dispenser.last_seen_at)

    def test_device_event_creates_schedule_event(self):
        container: Container = self.dispenser.containers.first()
        schedule = Schedule.objects.create(container=container, day_of_week=0, hour=8, minute=0, repeat=True)

        url = reverse("device-events", args=[self.dispenser.serial_id])
        payload = {
            "status": ScheduleEvent.STATUS_COMPLETED,
            "occurred_at": timezone.now().isoformat(),
            "container_slot": container.slot_number,
            "schedule_id": schedule.id,
        }
        resp = self.client.post(url, payload, format="json", HTTP_X_DEVICE_SECRET=self.dispenser.device_secret)

        self.assertEqual(resp.status_code, 204)
        event = ScheduleEvent.objects.get(dispenser=self.dispenser)
        self.assertEqual(event.status, ScheduleEvent.STATUS_COMPLETED)
        self.assertEqual(event.container, container)
        self.assertEqual(event.schedule, schedule)

    def test_device_session_rejects_bad_secret(self):
        session_url = reverse("device-session", args=[self.dispenser.serial_id])
        resp = self.client.post(session_url, HTTP_X_DEVICE_SECRET="bad-secret")
        self.assertEqual(resp.status_code, 401)
