from django.urls import path

from .views import (
    RegisterDispenserView,
    DeleteDispenserView,
    ShowAllDispensers,
    GetDispenserView,
    UpdatePillNameView,
    UpdateDispenserNameView,
    ContainerScheduleListView,
    ContainerScheduleCreateView,
    ScheduleRetrieveView,
    ScheduleUpdateView,
    ScheduleDeleteView,
)

urlpatterns = [
    path('register-dispenser/', RegisterDispenserView.as_view(), name='register-dispenser'),
    path('delete-dispenser/<str:name>/', DeleteDispenserView.as_view(), name='delete-dispenser'),
    path('list-all-user-dispensers/', ShowAllDispensers.as_view(), name='list-all-user-dispensers'),
    path('dispenser/<int:pk>/', GetDispenserView.as_view(), name='get-dispenser'),
    path('update-pill-name/', UpdatePillNameView.as_view(), name='update-pill-name'),
    path('update-dispenser-name/', UpdateDispenserNameView.as_view(), name='update-dispenser-name'),
    path('containers/<int:container_id>/schedules/list/', ContainerScheduleListView.as_view(), name='container-schedules-list'),
    path('containers/<int:container_id>/schedules/create/', ContainerScheduleCreateView.as_view(), name='container-schedules-create'),
    path('schedules/<int:pk>/retrieve/', ScheduleRetrieveView.as_view(), name='schedule-retrieve'),
    path('schedules/<int:pk>/update/', ScheduleUpdateView.as_view(), name='schedule-update'),
    path('schedules/<int:pk>/delete/', ScheduleDeleteView.as_view(), name='schedule-delete'),
]

