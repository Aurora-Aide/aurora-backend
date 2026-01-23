from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from dispensers.models import Dispenser, Container, Schedule
from dispensers.services import create_dispenser_for_user
from authentication.models import User


class DispenserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="pass12345",
            first_name="Owner",
            last_name="User",
        )
        self.other = User.objects.create_user(
            email="other@example.com",
            password="pass12345",
            first_name="Other",
            last_name="User",
        )

    def test_list_returns_only_owned_dispensers(self):
        create_dispenser_for_user(owner=self.user, name="MyDisp", serial_id="S-20250101-0001")
        create_dispenser_for_user(owner=self.other, name="OtherDisp", serial_id="S-20250101-0002")

        self.client.force_authenticate(user=self.user)
        url = reverse("list-all-user-dispensers")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "MyDisp")

    def test_get_dispenser_detail(self):
        dispenser = create_dispenser_for_user(owner=self.user, name="MyDisp", serial_id="S-20250101-0003")

        self.client.force_authenticate(user=self.user)
        url = reverse("get-dispenser", args=[dispenser.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], dispenser.id)
        self.assertEqual(resp.data["name"], "MyDisp")
        self.assertIn("containers", resp.data)
        self.assertGreaterEqual(len(resp.data["containers"]), 1)

    def test_get_dispenser_not_owned_returns_404(self):
        dispenser = create_dispenser_for_user(owner=self.other, name="OtherDisp", serial_id="S-20250101-0004")

        self.client.force_authenticate(user=self.user)
        url = reverse("get-dispenser", args=[dispenser.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 404)

    def test_create_schedule_for_container(self):
        dispenser = create_dispenser_for_user(owner=self.user, name="MyDisp", serial_id="S-20250101-0005")
        container = Container.objects.filter(dispenser=dispenser).first()

        self.client.force_authenticate(user=self.user)
        url = reverse("container-schedules-create", args=[container.id])
        payload = {"day_of_week": 0, "hour": 9, "minute": 0, "repeat": True}
        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Schedule.objects.filter(container=container).count(), 1)

    def test_schedule_detail_respects_ownership(self):
        dispenser = create_dispenser_for_user(owner=self.other, name="OtherDisp", serial_id="S-20250101-0006")
        container = Container.objects.filter(dispenser=dispenser).first()
        schedule = Schedule.objects.create(container=container, day_of_week=1, hour=10, minute=0, repeat=True)

        self.client.force_authenticate(user=self.user)
        url = reverse("schedule-retrieve", args=[schedule.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 404)

    def test_register_dispenser_creates_containers_and_sets_owner(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("register-dispenser")
        payload = {"name": "NewDisp", "serial_id": "S-20260101-1111"}

        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 201)
        disp = Dispenser.objects.get(serial_id="S-20260101-1111")
        self.assertEqual(disp.owner, self.user)
        self.assertEqual(disp.containers.count(), disp.max_containers)

    def test_duplicate_schedule_same_time_returns_400(self):
        dispenser = create_dispenser_for_user(owner=self.user, name="DupDisp", serial_id="S-20250101-0101")
        container = Container.objects.filter(dispenser=dispenser).first()
        self.client.force_authenticate(user=self.user)
        url = reverse("container-schedules-create", args=[container.id])
        payload = {"day_of_week": 0, "hour": 9, "minute": 30, "repeat": True}

        first = self.client.post(url, payload, format="json")
        dup = self.client.post(url, payload, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(dup.status_code, 400)
        self.assertEqual(container.schedules.count(), 1)

    def test_schedule_creation_marks_dispenser_dirty_and_bumps_version(self):
        dispenser = create_dispenser_for_user(owner=self.user, name="DirtyCheck", serial_id="S-20250101-0102")
        container = Container.objects.filter(dispenser=dispenser).first()
        self.client.force_authenticate(user=self.user)
        url = reverse("container-schedules-create", args=[container.id])
        payload = {"day_of_week": 1, "hour": 7, "minute": 0, "repeat": True}

        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 201)
        dispenser.refresh_from_db()
        self.assertTrue(dispenser.dirty)
        self.assertEqual(dispenser.schedule_version, 2)
