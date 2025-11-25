from django.db import models
from django.conf import settings
from django.utils import timezone


class Dispenser(models.Model):
    DISPENSER_SIZES = {
        'S': ('small', 4),
        'M': ('medium', 6),
        'L': ('large', 10)
    }

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dispensers")
    name = models.CharField(max_length=100)
    serial_id = models.CharField(max_length=20, unique=True)
    size = models.CharField(max_length=1, choices=[
        ('S', 'Small - 4 containers'),
        ('M', 'Medium - 6 containers'),
        ('L', 'Large - 10 containers')
    ])
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (owned by {self.owner.username})"

    @property
    def max_containers(self):
        return self.DISPENSER_SIZES[self.size][1]

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