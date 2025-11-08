from google.oauth2.credentials import Credentials
from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_google_meet_event(
    teacher,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    description: str = "",
    attendees_emails: list = None
) -> str:
    """
    Create a Google Meet event on the teacher's primary calendar.

    Args:
        teacher: TeacherProfile instance with google_access_token & google_refresh_token stored.
        summary: Event title.
        start_time: Event start datetime.
        end_time: Event end datetime.
        description: Optional event description.
        attendees_emails: List of email strings to invite (optional).

    Returns:
        hangoutLink: The Google Meet join URL.

    Raises:
        ValueError: If required credentials are missing.
        HttpError: If Google API returns an error.
    """

    if not teacher.google_access_token or not teacher.google_refresh_token:
        raise ValueError("Teacher OAuth credentials are missing.")

    # Ensure attendees list
    attendees = [{"email": email} for email in attendees_emails] if attendees_emails else []

    # Create Credentials object
    creds = Credentials(
        token=teacher.google_access_token,
        refresh_token=teacher.google_refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,  
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )

    try:
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Africa/Nairobi"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "Africa/Nairobi"},
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "attendees": attendees,
        }

        created_event = service.events().insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1
        ).execute()

        hangout_link = created_event.get("hangoutLink")
        if not hangout_link:
            logger.warning("Event created but hangoutLink is missing.")
            hangout_link = f"https://meet.google.com/new?authuser=0"  # fallback placeholder

        return hangout_link

    except HttpError as e:
        logger.error(f"Google Calendar API error: {e}")
        raise e
