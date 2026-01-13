from django.contrib.auth import get_user_model
from rest_framework import serializers

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
    class Meta:
        model = DispenserModel
        fields = ["id", "code", "name", "slot_count", "serial_prefix", "next_sequence"]
        read_only_fields = ["next_sequence"]

