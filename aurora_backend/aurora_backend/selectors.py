from .models import Dispenser, Container, Schedule


def list_dispensers_for_user(user):
    return Dispenser.objects.filter(owner=user).prefetch_related("containers__schedules")


def get_dispenser_for_user(user, pk: int):
    return Dispenser.objects.filter(owner=user).prefetch_related("containers__schedules").get(pk=pk)


def get_container_for_user(user, pk: int):
    return (
        Container.objects.filter(dispenser__owner=user)
        .prefetch_related("schedules")
        .get(pk=pk)
    )


def get_schedule_for_user(user, pk: int):
    return (
        Schedule.objects.select_related("container", "container__dispenser", "container__dispenser__owner")
        .get(pk=pk, container__dispenser__owner=user)
    )

