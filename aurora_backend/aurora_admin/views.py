from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from authentication.models import User
from dispensers.models import Dispenser, DispenserModel
from .serializers import (
    AdminUserSerializer,
    AdminDispenserSerializer,
    DispenserModelSerializer,
)


class AdminUsersListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()


class AdminDispenserListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminDispenserSerializer
    queryset = Dispenser.objects.select_related("owner", "dispenser_model").all()


class AdminDispenserRenameView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminDispenserSerializer
    queryset = Dispenser.objects.all()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        dispenser = self.get_object()
        new_name = request.data.get("name")
        if not new_name:
            return Response({"detail": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
        dispenser.name = new_name
        dispenser.save()
        serializer = self.get_serializer(dispenser)
        return Response(serializer.data)


class AdminDispenserModelListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = DispenserModelSerializer
    queryset = DispenserModel.objects.all()

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

