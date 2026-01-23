from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Dispenser, Container, Schedule


@transaction.atomic
def create_dispenser_for_user(*, owner, name: str, serial_id: str) -> Dispenser:
    size = serial_id[0]
    dispenser = Dispenser.objects.create(
        owner=owner,
        name=name,
        serial_id=serial_id,
        size=size,
    )
    dispenser.initialize_containers()
    return dispenser


@transaction.atomic
def delete_dispenser_for_user(*, owner, name: str) -> None:
    dispenser = get_object_or_404(Dispenser, owner=owner, name=name)
    dispenser.delete()


@transaction.atomic
def update_pill_name_for_container(*, owner, dispenser_name: str, slot_number: int, pill_name: str) -> Container:
    dispenser = get_object_or_404(Dispenser, owner=owner, name=dispenser_name)
    container = get_object_or_404(Container, dispenser=dispenser, slot_number=slot_number)
    container.pill_name = pill_name
    container.save()
    return container


@transaction.atomic
def update_dispenser_name(*, owner, current_name: str, new_name: str) -> Dispenser:
    dispenser = get_object_or_404(Dispenser, owner=owner, name=current_name)
    dispenser.name = new_name
    dispenser.save()
    return dispenser


def _assert_container_owner(container: Container, owner):
    if container.dispenser.owner != owner:
        raise Container.DoesNotExist


@transaction.atomic
def create_schedule_for_container(*, container: Container, owner, day_of_week: int, hour: int, minute: int = 0, repeat: bool = True) -> Schedule:
    _assert_container_owner(container, owner)
    return Schedule.objects.create(
        container=container,
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
        repeat=repeat,
    )


@transaction.atomic
def update_schedule(*, schedule: Schedule, owner, day_of_week: int | None = None, hour: int | None = None, minute: int | None = None, repeat: bool | None = None) -> Schedule:
    _assert_container_owner(schedule.container, owner)
    if day_of_week is not None:
        schedule.day_of_week = day_of_week
    if hour is not None:
        schedule.hour = hour
    if minute is not None:
        schedule.minute = minute
    if repeat is not None:
        schedule.repeat = repeat
    schedule.save()
    return schedule


@transaction.atomic
def delete_schedule(*, schedule: Schedule, owner) -> None:
    _assert_container_owner(schedule.container, owner)
    schedule.delete()

