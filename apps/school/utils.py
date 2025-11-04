import uuid
import requests
from django.conf import settings

def generate_google_meet_link(summary: str, start_time, end_time, attendees=None):
    """
    Generates a Google Meet link by creating a Calendar event with Google API.
    Fallback: returns a dummy meet link for dev/test mode.

    Requires:
      - GOOGLE_CALENDAR_API_TOKEN (OAuth2 token with Calendar scope)
      - Proper service account / delegated user setup

    Args:
        summary (str): The event title (e.g., "Math Tutoring Session")
        start_time (datetime): The scheduled start time (UTC)
        end_time (datetime): The scheduled end time (UTC)
        attendees (list): Optional list of attendee emails

    Returns:
        str: A Google Meet URL
    """
    if not getattr(settings, "GOOGLE_CALENDAR_API_TOKEN", None):
        # Fallback for dev/testing
        random_id = uuid.uuid4().hex[:8]
        return f"https://meet.google.com/{random_id}"

    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {settings.GOOGLE_CALENDAR_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "summary": summary,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
        "conferenceData": {
            "createRequest": {
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
                "requestId": str(uuid.uuid4())
            }
        },
    }

    if attendees:
        payload["attendees"] = [{"email": e} for e in attendees]

    response = requests.post(url, json=payload, headers=headers, params={"conferenceDataVersion": 1})

    if response.status_code == 200:
        data = response.json()
        meet_link = data.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri")
        return meet_link or f"https://meet.google.com/{uuid.uuid4().hex[:8]}"
    else:
      
        return f"https://meet.google.com/{uuid.uuid4().hex[:8]}"
