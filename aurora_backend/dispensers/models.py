# Dispenser-related models moved from the project package into this app.
from django.db import models
from django.conf import settings
from django.utils import timezone


class DispenserModel(models.Model):
    code = models.CharField(max_length=10, unique=True)  # e.g., S, M, L, XL1
    name = models.CharField(max_length=100)
    slot_count = models.PositiveIntegerField(default=4)
    serial_prefix = models.CharField(max_length=10, unique=True)
    next_sequence = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.name})"


class Dispenser(models.Model):
    DISPENSER_SIZES = {
        'S': ('small', 4),
        'M': ('medium', 6),
        'L': ('large', 10)
    }

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="dispensers")
    name = models.CharField(max_length=100)
    serial_id = models.CharField(max_length=30, unique=True)
    size = models.CharField(max_length=10)  # code; keep free-form for new models
    dispenser_model = models.ForeignKey(DispenserModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="dispensers")
    created_at = models.DateTimeField(default=timezone.now)
    # Device-facing fields
    device_secret = models.CharField(max_length=64, default='', blank=True)
    schedule_version = models.BigIntegerField(default=1)
    device_session_rev = models.PositiveIntegerField(default=1)
    dirty = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (owned by {self.owner.email if self.owner else 'unassigned'})"

    @property
    def max_containers(self):
        if self.dispenser_model:
            return self.dispenser_model.slot_count
        # Fallback to legacy size mapping
        return self.DISPENSER_SIZES.get(self.size, ('', 4))[1]

    def initialize_containers(self):
        """Create empty containers for this dispenser based on its size"""
        for slot in range(1, self.max_containers + 1):
            Container.objects.create(
                dispenser=self,
                slot_number=slot,
                pill_name=f"Empty Slot {slot}"
            )


class Container(models.Model):
    """
    One physical slot in the dispenser.
    slot_number lets you distinguish container #1, #2, etc.
    pill_name is whatever pills you load in it.
    """
    dispenser = models.ForeignKey(Dispenser, on_delete=models.CASCADE, related_name="containers")
    slot_number = models.PositiveIntegerField()
    pill_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("dispenser", "slot_number")
        ordering = ["slot_number"]

    def __str__(self):
        return f"Slot {self.slot_number}: {self.pill_name}"


class Schedule(models.Model):
    """
    A schedule entry for a container: which day/time to drop, and whether it repeats weekly.
    """

    MON, TUE, WED, THU, FRI, SAT, SUN = range(7)
    DAY_OF_WEEK_CHOICES = [
        (MON, "Monday"),
        (TUE, "Tuesday"),
        (WED, "Wednesday"),
        (THU, "Thursday"),
        (FRI, "Friday"),
        (SAT, "Saturday"),
        (SUN, "Sunday"),
    ]

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="schedules")
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_OF_WEEK_CHOICES)
    hour = models.PositiveSmallIntegerField()  # 0-23
    minute = models.PositiveSmallIntegerField(default=0)  # 0-59
    repeat = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["day_of_week", "hour", "minute"]
        constraints = [
            models.UniqueConstraint(
                fields=["container", "day_of_week", "hour", "minute"],
                name="uniq_schedule_per_container_time",
            )
        ]
        indexes = [
            models.Index(fields=["container", "day_of_week"]),
        ]

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.hour:02d}:{self.minute:02d} (repeat={self.repeat})"


class ScheduleEvent(models.Model):
    STATUS_COMPLETED = "completed"
    STATUS_MISSED = "missed"
    STATUS_CHOICES = [
        (STATUS_COMPLETED, "completed"),
        (STATUS_MISSED, "missed"),
    ]

    dispenser = models.ForeignKey(Dispenser, on_delete=models.CASCADE, related_name="events")
    container = models.ForeignKey(Container, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.dispenser.serial_id} {self.status} at {self.occurred_at}"

