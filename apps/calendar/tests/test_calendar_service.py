# Feature: payment-escrow-calendar-exam-p2p
"""Property-based tests for CalendarService — Properties 11-16."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

CE_PATH = "apps.calendar.models.CalendarEvent"
ENROLL_PATH = "apps.school.models.CourseEnrollment"
CE_VIEW_PATH = "apps.calendar.views.CalendarEvent"

def _make_booking(status="accepted", n_parents=0):
    booking = MagicMock()
    booking.id = uuid.uuid4()
    booking.status = status
    booking.scheduled_start = datetime(2025, 9, 1, 10, 0, tzinfo=timezone.utc)
    booking.scheduled_end = datetime(2025, 9, 1, 11, 0, tzinfo=timezone.utc)
    booking.teacher = MagicMock()
    booking.teacher.user.get_full_name.return_value = "Mr. Kamau"
    booking.student = MagicMock()
    parents = [MagicMock() for _ in range(n_parents)]
    for pc in parents:
        pc.parent = MagicMock()
    booking.student.child_parents.select_related.return_value = parents
    return booking

@given(n_parents=st.integers(min_value=0, max_value=10))
@h_settings(max_examples=30)
def test_property_11_session_booking_fan_out(n_parents):
    """Feature: payment-escrow-calendar-exam-p2p, Property 11: fan-out for bookings."""
    from apps.calendar.services import CalendarService
    booking = _make_booking(n_parents=n_parents)
    with patch(CE_PATH) as mock_ce:
        mock_ce.objects.update_or_create.return_value = (MagicMock(), True)
        CalendarService.on_session_booking_save(booking)
        assert mock_ce.objects.update_or_create.call_count == 2 + n_parents

@given(n_students=st.integers(min_value=0, max_value=10))
@h_settings(max_examples=30)
def test_property_11_live_session_fan_out(n_students):
    """Feature: payment-escrow-calendar-exam-p2p, Property 11: fan-out for live sessions."""
    from apps.calendar.services import CalendarService
    ls = MagicMock()
    ls.id = uuid.uuid4()
    ls.title = "Math Live"
    ls.started_at = datetime(2025, 9, 1, 10, 0, tzinfo=timezone.utc)
    ls.ended_at = datetime(2025, 9, 1, 11, 0, tzinfo=timezone.utc)
    ls.teacher = MagicMock()
    ls.course_id = uuid.uuid4()
    enrollments = [MagicMock() for _ in range(n_students)]
    for e in enrollments:
        e.student = MagicMock()
    with patch(CE_PATH) as mock_ce, patch(ENROLL_PATH) as mock_enroll:
        mock_ce.objects.update_or_create.return_value = (MagicMock(), True)
        mock_enroll.objects.filter.return_value.select_related.return_value = enrollments
        CalendarService.on_live_session_save(ls)
        assert mock_ce.objects.update_or_create.call_count == 1 + n_students

def test_property_12_required_fields_present():
    """Feature: payment-escrow-calendar-exam-p2p, Property 12: required fields in defaults."""
    from apps.calendar.services import CalendarService
    booking = _make_booking(n_parents=0)
    with patch(CE_PATH) as mock_ce:
        mock_ce.objects.update_or_create.return_value = (MagicMock(), True)
        CalendarService.on_session_booking_save(booking)
        for call_args in mock_ce.objects.update_or_create.call_args_list:
            defaults = call_args.kwargs.get("defaults", {})
            for field in ("title", "start_datetime", "end_datetime", "event_type", "status"):
                assert field in defaults

@given(cancel_status=st.sampled_from(["cancelled", "declined"]))
@h_settings(max_examples=10)
def test_property_13_cancellation_propagates(cancel_status):
    """Feature: payment-escrow-calendar-exam-p2p, Property 13: cancellation sets status=cancelled."""
    from apps.calendar.services import CalendarService
    booking = _make_booking(status=cancel_status, n_parents=1)
    with patch(CE_PATH) as mock_ce:
        mock_ce.objects.update_or_create.return_value = (MagicMock(), True)
        CalendarService.on_session_booking_save(booking)
        for call_args in mock_ce.objects.update_or_create.call_args_list:
            assert call_args.kwargs.get("defaults", {}).get("status") == "cancelled"

def test_property_14_live_session_time_update_propagates():
    """Feature: payment-escrow-calendar-exam-p2p, Property 14: time updates propagate."""
    from apps.calendar.services import CalendarService
    new_start = datetime(2025, 10, 1, 9, 0, tzinfo=timezone.utc)
    new_end = datetime(2025, 10, 1, 10, 0, tzinfo=timezone.utc)
    ls = MagicMock()
    ls.id = uuid.uuid4()
    ls.title = "Updated"
    ls.started_at = new_start
    ls.ended_at = new_end
    ls.teacher = MagicMock()
    ls.course_id = uuid.uuid4()
    with patch(CE_PATH) as mock_ce, patch(ENROLL_PATH) as mock_enroll:
        mock_ce.objects.update_or_create.return_value = (MagicMock(), True)
        mock_enroll.objects.filter.return_value.select_related.return_value = []
        CalendarService.on_live_session_save(ls)
        for call_args in mock_ce.objects.update_or_create.call_args_list:
            defaults = call_args.kwargs.get("defaults", {})
            assert defaults["start_datetime"] == new_start
            assert defaults["end_datetime"] == new_end

def test_property_15_endpoint_filters_by_user(rf):
    """Feature: payment-escrow-calendar-exam-p2p, Property 15: endpoint filters by role."""
    from apps.calendar.views import CalendarEventListView
    request = rf.get("/api/calendar/events/")
    user = MagicMock()
    user.is_authenticated = True
    student_profile = MagicMock()
    user.student_profile = student_profile
    del user.teacher_profile
    del user.parent_profile
    request.user = user
    request.query_params = {}
    view = CalendarEventListView()
    view.request = request
    with patch(CE_VIEW_PATH) as mock_ce:
        mock_qs = MagicMock()
        mock_ce.objects.all.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        view.get_queryset()
        mock_qs.filter.assert_called_with(student=student_profile)

def test_property_16_date_range_filter(rf):
    """Feature: payment-escrow-calendar-exam-p2p, Property 16: date range filter applied."""
    from apps.calendar.views import CalendarEventListView
    request = rf.get("/api/calendar/events/")
    user = MagicMock()
    user.is_authenticated = True
    teacher_profile = MagicMock()
    user.teacher_profile = teacher_profile
    del user.student_profile
    del user.parent_profile
    request.user = user
    request.query_params = {"start_date": "2025-09-01", "end_date": "2025-09-30"}
    view = CalendarEventListView()
    view.request = request
    with patch(CE_VIEW_PATH) as mock_ce:
        mock_qs = MagicMock()
        mock_ce.objects.all.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        view.get_queryset()
        filter_calls = [str(c) for c in mock_qs.filter.call_args_list]
        assert any("start_datetime__gte" in c for c in filter_calls)
        assert any("start_datetime__lte" in c for c in filter_calls)
