from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .device_auth import DeviceAuthentication, DeviceSessionAuthentication
from .models import Dispenser, Container, Schedule, ScheduleEvent
from .serializers import DeviceConfigSerializer, DeviceEventSerializer, DeviceContainerSerializer
from .device_tokens import issue_device_token


class DeviceConfigView(APIView):
    authentication_classes = [DeviceSessionAuthentication, DeviceAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, serial_id):
        dispenser = Dispenser.objects.select_related().prefetch_related(
            "containers__schedules"
        ).filter(serial_id=serial_id).first()
        if not dispenser:
            return Response({"detail": "Dispenser not found"}, status=status.HTTP_404_NOT_FOUND)

        dispenser.last_seen_at = timezone.now()
        dispenser.dirty = False
        dispenser.save(update_fields=["last_seen_at", "dirty"])

        data = {
            "serial_id": dispenser.serial_id,
            "schedule_version": dispenser.schedule_version,
            "containers": DeviceContainerSerializer(dispenser.containers.all(), many=True).data,
        }
        return Response(data)


class DeviceEventView(APIView):
    authentication_classes = [DeviceSessionAuthentication, DeviceAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request, serial_id):
        dispenser = Dispenser.objects.filter(serial_id=serial_id).first()
        if not dispenser:
            return Response({"detail": "Dispenser not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeviceEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        container = None
        schedule = None
        if payload.get("container_slot") is not None:
            container = Container.objects.filter(dispenser=dispenser, slot_number=payload["container_slot"]).first()
        if payload.get("schedule_id") is not None:
            schedule = Schedule.objects.filter(pk=payload["schedule_id"], container__dispenser=dispenser).first()

        ScheduleEvent.objects.create(
            dispenser=dispenser,
            container=container,
            schedule=schedule,
            status=payload["status"],
            occurred_at=payload["occurred_at"],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class DeviceSessionView(APIView):
    """
    Issues a short-lived bearer token for device requests.
    Authenticated with X-Device-Secret; returns JWT + expiry.
    """

    authentication_classes = [DeviceAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request, serial_id):
        dispenser = Dispenser.objects.filter(serial_id=serial_id).first()
        if not dispenser:
            return Response({"detail": "Dispenser not found"}, status=status.HTTP_404_NOT_FOUND)

        token, exp = issue_device_token(dispenser)
        return Response(
            {
                "token": token,
                "expires_at": exp.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


