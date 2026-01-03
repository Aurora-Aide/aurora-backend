from django.urls import path

from .views import (
    RegisterDispenserView,
    DeleteDispenserView,
    ShowAllDispensers,
    GetDispenserView,
    UpdatePillNameView,
    UpdateDispenserNameView,
    ContainerScheduleListCreateView,
    ScheduleDetailView,
)

urlpatterns = [
    path('register-dispenser/', RegisterDispenserView.as_view(), name='register-dispenser'),
    path('delete-dispenser/<str:name>/', DeleteDispenserView.as_view(), name='delete-dispenser'),
    path('list-all-user-dispensers/', ShowAllDispensers.as_view(), name='list-all-user-dispensers'),
    path('dispenser/<int:pk>/', GetDispenserView.as_view(), name='get-dispenser'),
    path('update-pill-name/', UpdatePillNameView.as_view(), name='update-pill-name'),
    path('update-dispenser-name/', UpdateDispenserNameView.as_view(), name='update-dispenser-name'),
    path('containers/<int:container_id>/schedules/', ContainerScheduleListCreateView.as_view(), name='container-schedules'),
    path('schedules/<int:pk>/', ScheduleDetailView.as_view(), name='schedule-detail'),
]

