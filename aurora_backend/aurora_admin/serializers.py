from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from dispensers.models import Dispenser, DispenserModel


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email", "first_name", "last_name", "is_active", "is_staff"]


class AdminDispenserSerializer(serializers.ModelSerializer):
    # Only expose owner email/id for admin listing.
    owner = serializers.SerializerMethodField(required=False)
    model = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Dispenser
        fields = ["id", "name", "serial_id", "size", "owner", "model"]
        validators = []

    def get_owner(self, obj):
        if not obj.owner:
            return None
        return {"email": obj.owner.email}

    def get_model(self, obj):
        if not obj.dispenser_model:
            return None
        return {
            "id": obj.dispenser_model.id,
            "code": obj.dispenser_model.code,
            "name": obj.dispenser_model.name,
            "slot_count": obj.dispenser_model.slot_count,
        }

    def to_representation(self, instance):
        """
        Ensure owner/model keys are always present, even when null.
        """
        data = super().to_representation(instance)
        if "owner" not in data:
            data["owner"] = None
        if "model" not in data:
            data["model"] = None
        return data


class DispenserModelSerializer(serializers.ModelSerializer):
    @staticmethod
    def _normalize_prefix(value: str) -> str:
        return value.strip().upper().rstrip("-")

    def validate_code(self, value):
        code = self._normalize_prefix(value)
        if not code:
            raise serializers.ValidationError(_("Model code cannot be empty."))
        if not code.isalnum():
            raise serializers.ValidationError(_("Model code can only contain letters and numbers."))
        return code

    def validate_serial_prefix(self, value):
        serial_prefix = self._normalize_prefix(value)
        if not serial_prefix:
            raise serializers.ValidationError(_("Serial prefix cannot be empty."))
        if not serial_prefix.isalnum():
            raise serializers.ValidationError(_("Serial prefix can only contain letters and numbers."))
        return serial_prefix

    def validate(self, attrs):
        code = attrs.get("code", getattr(self.instance, "code", ""))
        serial_prefix = attrs.get("serial_prefix", code)
        attrs["serial_prefix"] = self._normalize_prefix(serial_prefix or code)
        return attrs

    class Meta:
        model = DispenserModel
        fields = ["id", "code", "name", "slot_count", "serial_prefix", "next_sequence"]
        read_only_fields = ["next_sequence"]
        extra_kwargs = {
            "serial_prefix": {"required": False, "allow_blank": True},
        }

