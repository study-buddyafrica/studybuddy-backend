from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

def generate_google_meet_link(summary, description, start_time, end_time):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'path/to/calendar-service-account.json'
    CALENDAR_ID = 'primary'  # Or the shared calendar’s ID

    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    service = build('calendar', 'v3', credentials=credentials)

    # Create event with Meet link
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Africa/Nairobi'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Africa/Nairobi'},
        'conferenceData': {
            'createRequest': {
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                'requestId': f"meet-{datetime.now().timestamp()}",
            }
        },
    }

    created_event = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event,
        conferenceDataVersion=1
    ).execute()

    return created_event['hangoutLink']
