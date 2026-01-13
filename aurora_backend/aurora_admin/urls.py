from django.urls import path

from .views import (
    AdminUsersListView,
    AdminDispenserListView,
    AdminDispenserRenameView,
    AdminDispenserModelListCreateView,
)

urlpatterns = [
    path('users/', AdminUsersListView.as_view(), name='admin-users'),
    path('dispensers/', AdminDispenserListView.as_view(), name='admin-dispensers'),
    path('dispensers/<int:pk>/rename/', AdminDispenserRenameView.as_view(), name='admin-dispenser-rename'),
    path('dispenser-models/', AdminDispenserModelListCreateView.as_view(), name='admin-dispenser-models'),
]

