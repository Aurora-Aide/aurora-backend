from django.db import transaction, IntegrityError
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

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


class ShowAllDispensers(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DispenserSerializer

    def get_queryset(self):
        return list_dispensers_for_user(self.request.user)


class GetDispenserView(generics.RetrieveAPIView):
    serializer_class = DispenserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Dispenser.objects.all()

    def get_queryset(self):
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


class ContainerScheduleListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScheduleReadSerializer

    def get_container(self):
        return get_container_for_user(self.request.user, self.kwargs["container_id"])

    def get_queryset(self):
        container = self.get_container()
        return container.schedules.all()


class ContainerScheduleCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScheduleWriteSerializer

    def get_container(self):
        return get_container_for_user(self.request.user, self.kwargs["container_id"])

    @transaction.atomic
    def perform_create(self, serializer):
        container = self.get_container()
        # Prevent duplicates before hitting the DB constraint
        if container.schedules.filter(
            day_of_week=serializer.validated_data["day_of_week"],
            hour=serializer.validated_data["hour"],
            minute=serializer.validated_data["minute"],
        ).exists():
            raise ValidationError({"detail": "A schedule already exists for that time."})

        try:
            create_schedule_for_container(
                container=container,
                owner=self.request.user,
                **serializer.validated_data,
            )
        except IntegrityError:
            raise ValidationError({"detail": "A schedule already exists for that time."})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return the last created schedule for this container
        read = ScheduleReadSerializer(self.get_container().schedules.latest("id"))
        headers = self.get_success_headers(read.data)
        return Response(read.data, status=status.HTTP_201_CREATED, headers=headers)


class ScheduleRetrieveView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScheduleReadSerializer
    queryset = Schedule.objects.all()

    def get_object(self):
        return get_schedule_for_user(self.request.user, self.kwargs["pk"])


class ScheduleUpdateView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScheduleWriteSerializer
    queryset = Schedule.objects.all()

    def get_object(self):
        return get_schedule_for_user(self.request.user, self.kwargs["pk"])

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        schedule = self.get_object()
        serializer = self.get_serializer(schedule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            update_schedule(
                schedule=schedule,
                owner=request.user,
                **serializer.validated_data,
            )
        except IntegrityError:
            raise ValidationError({"detail": "A schedule already exists for that time."})
        read_serializer = ScheduleReadSerializer(schedule)
        return Response(read_serializer.data)


class ScheduleDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Schedule.objects.all()

    def get_object(self):
        return get_schedule_for_user(self.request.user, self.kwargs["pk"])

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        schedule = self.get_object()
        delete_schedule(schedule=schedule, owner=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
from django.shortcuts import render

# Create your views here.
