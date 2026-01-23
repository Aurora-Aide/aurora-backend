from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from .models import Dispenser, Container, Schedule
from .serializers import (
    DispenserSerializer,
    ContainerSerializer,
    RegisterDispenserSerializer,
    UpdatePillNameSerializer,
    UpdateDispenserNameSerializer,
    ScheduleReadSerializer,
    ScheduleWriteSerializer,
)
from .services import (
    create_dispenser_for_user,
    delete_dispenser_for_user,
    update_dispenser_name,
    update_pill_name_for_container,
    create_schedule_for_container,
    update_schedule,
    delete_schedule,
)
from .selectors import (
    list_dispensers_for_user,
    get_dispenser_for_user,
    get_container_for_user,
    get_schedule_for_user,
)

class RegisterDispenserView(generics.CreateAPIView):
    serializer_class = RegisterDispenserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dispenser = create_dispenser_for_user(
            owner=request.user,
            name=serializer.validated_data['name'],
            serial_id=serializer.validated_data['serial_id'],
        )

        # Return the created dispenser with all its containers and schedules
        response_serializer = DispenserSerializer(dispenser)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class DeleteDispenserView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'name'
    queryset = Dispenser.objects.all()

    def get_queryset(self):
        return Dispenser.objects.filter(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            delete_dispenser_for_user(owner=request.user, name=kwargs.get("name"))
            return Response(
                {"detail": "Dispenser successfully deleted"},
                status=status.HTTP_200_OK
            )
        except Dispenser.DoesNotExist:
            return Response(
                {"detail": "Dispenser not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class ShowAllDispensers(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = list_dispensers_for_user(request.user)
        serializer = DispenserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetDispenserView(generics.RetrieveAPIView):
    """
    Return a single dispenser (owned by the authenticated user) with its containers.
    """

    serializer_class = DispenserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Dispenser.objects.all()

    def get_queryset(self):
        # Restrict to the requesting user's dispensers to avoid data leaks.
        return list_dispensers_for_user(self.request.user)


class UpdatePillNameView(generics.UpdateAPIView):
    serializer_class = UpdatePillNameSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            container = update_pill_name_for_container(
                owner=request.user,
                dispenser_name=serializer.validated_data['dispenser_name'],
                slot_number=serializer.validated_data['slot_number'],
                pill_name=serializer.validated_data['pill_name'],
            )
        except Dispenser.DoesNotExist:
            return Response(
                {"detail": "Dispenser not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Container.DoesNotExist:
            return Response(
                {"detail": "Container not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        response_serializer = ContainerSerializer(container)
        return Response(response_serializer.data)

class UpdateDispenserNameView(generics.UpdateAPIView):
    serializer_class = UpdateDispenserNameSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dispenser = update_dispenser_name(
                owner=request.user,
                current_name=serializer.validated_data['current_name'],
                new_name=serializer.validated_data['new_name'],
            )
        except Dispenser.DoesNotExist:
            return Response(
                {"detail": "Dispenser not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        response_serializer = DispenserSerializer(dispenser)
        return Response(response_serializer.data)


class ContainerScheduleListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Schedule.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ScheduleWriteSerializer
        return ScheduleReadSerializer

    def get_container(self):
        return get_container_for_user(self.request.user, self.kwargs["container_id"])

    def get_queryset(self):
        container = self.get_container()
        return container.schedules.all()

    @transaction.atomic
    def perform_create(self, serializer):
        container = self.get_container()
        create_schedule_for_container(
            container=container,
            owner=self.request.user,
            **serializer.validated_data,
        )


class ScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Schedule.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ScheduleWriteSerializer
        return ScheduleReadSerializer

    def get_object(self):
        return get_schedule_for_user(self.request.user, self.kwargs["pk"])

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        schedule = self.get_object()
        serializer = self.get_serializer(schedule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        update_schedule(
            schedule=schedule,
            owner=request.user,
            **serializer.validated_data,
        )
        read_serializer = ScheduleReadSerializer(schedule)
        return Response(read_serializer.data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        schedule = self.get_object()
        delete_schedule(schedule=schedule, owner=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)