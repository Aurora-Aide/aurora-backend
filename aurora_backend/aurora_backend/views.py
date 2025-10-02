from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from .models import Dispenser
from .serializers import (
    DispenserSerializer,
    RegisterDispenserSerializer,
)

class RegisterDispenserView(generics.CreateAPIView):
    serializer_class = RegisterDispenserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract size from serial ID (first character)
        size = serializer.validated_data['serial_id'][0]

        # Create dispenser
        dispenser = Dispenser.objects.create(
            owner=request.user,
            name=serializer.validated_data['name'],
            serial_id=serializer.validated_data['serial_id'],
            size=size
        )

        # Initialize containers and schedules
        dispenser.initialize_containers()

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
            instance = self.get_object()
            self.perform_destroy(instance)
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
        queryset = Dispenser.objects.filter(owner=request.user)
        serializer = DispenserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
