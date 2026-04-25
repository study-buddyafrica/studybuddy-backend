# Signals are connected here; CalendarService is imported lazily to avoid circular imports.
from django.db.models.signals import post_save
from django.dispatch import receiver


def _connect_signals():
    from apps.school.models import SessionBooking, LiveSession
    from apps.calendar.services import CalendarService

    @receiver(post_save, sender=SessionBooking, dispatch_uid="calendar_session_booking_save")
    def on_session_booking_save(sender, instance, **kwargs):
        CalendarService.on_session_booking_save(instance)

    @receiver(post_save, sender=LiveSession, dispatch_uid="calendar_live_session_save")
    def on_live_session_save(sender, instance, **kwargs):
        CalendarService.on_live_session_save(instance)


_connect_signals()
