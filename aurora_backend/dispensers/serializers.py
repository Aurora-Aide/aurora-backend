import re

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Dispenser, Container, Schedule, DispenserModel


class ScheduleReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ["id", "day_of_week", "hour", "minute", "repeat"]


class ScheduleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ["day_of_week", "hour", "minute", "repeat"]

    def validate_day_of_week(self, value):
        if value < 0 or value > 6:
            raise serializers.ValidationError(_("day_of_week must be between 0 (Monday) and 6 (Sunday)"))
        return value

    def validate_hour(self, value):
        if value < 0 or value > 23:
            raise serializers.ValidationError(_("hour must be between 0 and 23"))
        return value

    def validate_minute(self, value):
        if value < 0 or value > 59:
            raise serializers.ValidationError(_("minute must be between 0 and 59"))
        return value


class ContainerSerializer(serializers.ModelSerializer):
    schedules = ScheduleReadSerializer(many=True, read_only=True)

    class Meta:
        model = Container
        fields = ['id', 'dispenser', 'slot_number', 'pill_name', 'schedules']

    def validate_slot_number(self, value):
        if value < 1:
            raise serializers.ValidationError(_("Slot number must be positive"))
        return value

    def validate(self, data):
        # Check if slot_number is unique for this dispenser
        if self.instance is None:
            existing = Container.objects.filter(
                dispenser=data['dispenser'],
                slot_number=data['slot_number']
            ).exists()
            if existing:
                raise serializers.ValidationError(
                    _("This slot number is already in use for this dispenser")
                )

        # Validate pill name is not empty
        if not data.get('pill_name', '').strip():
            raise serializers.ValidationError(_("Pill name cannot be empty"))

        # Maximum number of containers per dispenser (e.g., 8 slots)
        MAX_SLOTS = 8
        if self.instance is None:
            current_count = Container.objects.filter(dispenser=data['dispenser']).count()
            if current_count >= MAX_SLOTS:
                raise serializers.ValidationError(
                    _(f"A dispenser cannot have more than {MAX_SLOTS} containers")
                )

        return data


class DispenserReadSerializer(serializers.ModelSerializer):
    containers = ContainerSerializer(many=True, read_only=True)
    owner = serializers.ReadOnlyField(source='owner.email')

    class Meta:
        model = Dispenser
        fields = ['id', 'name', 'serial_id', 'owner', 'containers']

    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(_("Dispenser name must be at least 3 characters long"))

        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', value):
            raise serializers.ValidationError(_("Dispenser name can only contain letters, numbers, spaces, hyphens, and underscores"))

        return value.strip()

    def validate(self, data):
        if self.instance is None:
            request = self.context.get('request')
            if request and request.user:
                existing = Dispenser.objects.filter(
                    owner=request.user,
                    name=data['name']
                ).exists()
                if existing:
                    raise serializers.ValidationError(
                        _("You already have a dispenser with this name")
                    )
        return data


# Alias to maintain existing imports/usages.
DispenserSerializer = DispenserReadSerializer


class RegisterDispenserSerializer(serializers.Serializer):
    serial_id = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=100)

    def validate_serial_id(self, value):
        # Serial ID format: CODE-YYYYMMDD-XXXX
        pattern = r'^[A-Z0-9]+-\d{8}-\d{4}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                _("Invalid serial ID format. Expected format: CODE-YYYYMMDD-XXXX (e.g., S-20250524-0001)")
            )

        code = value.split("-")[0]
        if not DispenserModel.objects.filter(code=code).exists():
            raise serializers.ValidationError(_("Unknown dispenser model code."))

        if Dispenser.objects.filter(serial_id=value).exists():
            raise serializers.ValidationError(_("This dispenser is already registered"))

        return value

    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(_("Dispenser name must be at least 3 characters long"))

        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', value):
            raise serializers.ValidationError(
                _("Dispenser name can only contain letters, numbers, spaces, hyphens, and underscores")
            )

        return value.strip()

    def validate(self, data):
        # Check if user already has a dispenser with this name
        request = self.context.get('request')
        if request and request.user:
            if Dispenser.objects.filter(owner=request.user, name=data['name']).exists():
                raise serializers.ValidationError(_("You already have a dispenser with this name"))

        return data


class UpdatePillNameSerializer(serializers.Serializer):
    dispenser_name = serializers.CharField()
    slot_number = serializers.IntegerField()
    pill_name = serializers.CharField(max_length=100)

    def validate_pill_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(_("Pill name cannot be empty"))
        return value.strip()


class UpdateDispenserNameSerializer(serializers.Serializer):
    current_name = serializers.CharField()
    new_name = serializers.CharField(max_length=100)

    def validate_new_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(_("Dispenser name must be at least 3 characters long"))

        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', value):
            raise serializers.ValidationError(
                _("Dispenser name can only contain letters, numbers, spaces, hyphens, and underscores")
            )

        return value.strip()

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user:
            if Dispenser.objects.filter(
                owner=request.user,
                name=data['new_name']
            ).exists():
                raise serializers.ValidationError(_("You already have a dispenser with this name"))
        return data


class DeviceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ["id", "day_of_week", "hour", "minute", "repeat"]


class DeviceContainerSerializer(serializers.ModelSerializer):
    schedules = DeviceScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Container
        fields = ["slot_number", "pill_name", "schedules"]


class DeviceConfigSerializer(serializers.Serializer):
    serial_id = serializers.CharField()
    schedule_version = serializers.IntegerField()
    containers = DeviceContainerSerializer(many=True)


class DeviceEventSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["completed", "missed"])
    occurred_at = serializers.DateTimeField()
    container_slot = serializers.IntegerField(required=False)
    schedule_id = serializers.IntegerField(required=False)
