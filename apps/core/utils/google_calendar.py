import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DAILY_API_KEY = os.getenv("DAILY_API_KEY")
if not DAILY_API_KEY:
    raise ValueError("Missing DAILY_API_KEY in environment variables.")

class DailyCoAPI:
    BASE_URL = "https://api.daily.co/v1/rooms"

    def __init__(self, api_key: str = DAILY_API_KEY):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_room(
        self,
        name: str,
        end_time: datetime,
        privacy: str = "public",
        enable_chat: bool = True,
        enable_screenshare: bool = True,
        start_audio_off: bool = False,
        start_video_off: bool = False,
        enable_prejoin_ui: bool = True,
        enable_people_ui: bool = True,
        enable_network_ui: bool = True,
        enable_pip_ui: bool = True,
        enable_emoji_reactions: bool = True,
        enable_noise_cancellation: bool = True,
        enable_video_processing: bool = True,
        enable_advanced_chat: bool = True,
    ) -> dict:
        """
        Create a Daily.co room.
        Returns a dictionary with room URL and details.
        """
        properties = {
            "enable_chat": enable_chat,
            "enable_screenshare": enable_screenshare,
            "start_audio_off": start_audio_off,
            "start_video_off": start_video_off,
            "exp": int(end_time.timestamp()),
            "enable_prejoin_ui": enable_prejoin_ui,
            "enable_people_ui": enable_people_ui,
            "enable_network_ui": enable_network_ui,
            "enable_pip_ui": enable_pip_ui,
            "enable_emoji_reactions": enable_emoji_reactions,
            "enable_advanced_chat": enable_advanced_chat,
        }

        payload = {
            "name": name,
            "privacy": privacy,
            "properties": properties
        }

        try:
            response = requests.post(self.BASE_URL, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            room_data = response.json()

            room_url = room_data.get("url")
            if not room_url:
                raise ValueError(f"Daily.co API did not return a room URL. Response: {room_data}")

            return {
                "url": room_url,
                "name": room_data.get("name"),
                "privacy": room_data.get("privacy"),
                "expires_at": end_time.isoformat(),
                "id": room_data.get("id"),
                "features": {
                    "chat": enable_chat,
                    "screenshare": enable_screenshare,
                    "prejoin_ui": enable_prejoin_ui,
                    "emoji_reactions": enable_emoji_reactions,
                }
            }

        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to create Daily.co room: {error_text}") from e

    def create_owner_token(
        self, 
        room_name: str, 
        user_id: str, 
        user_name: str,
        enable_recording: bool = True,
    ) -> dict:
        """
        Create a meeting token for room owner with full permissions.
        """
        token_payload = {
            "properties": {
                "room_name": room_name,
                "user_id": user_id,
                "user_name": user_name,
                "is_owner": True,  # This gives owner permissions
                "enable_recording": enable_recording,
                "start_audio_off": False,
                "start_video_off": False,
            }
            # Removed 'exp' parameter as it's not supported
        }

        try:
            response = requests.post(
                "https://api.daily.co/v1/meeting-tokens",
                headers=self.headers,
                json=token_payload,
                timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            
            return {
                "token": token_data.get("token"),
                "room_url": f"https://studybuddyafrica.daily.co/{room_name}?t={token_data.get('token')}",
                "user_id": user_id,
                "user_name": user_name,
                "is_owner": True
            }
            
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to create owner token: {error_text}") from e

    def create_participant_token(
        self, 
        room_name: str, 
        user_id: str, 
        user_name: str,
    ) -> dict:
        """
        Create a meeting token for regular participant.
        """
        token_payload = {
            "properties": {
                "room_name": room_name,
                "user_id": user_id,
                "user_name": user_name,
                "is_owner": False,  # Regular participant
                "enable_recording": False,
            }
        }

        try:
            response = requests.post(
                "https://api.daily.co/v1/meeting-tokens",
                headers=self.headers,
                json=token_payload,
                timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            
            return {
                "token": token_data.get("token"),
                "room_url": f"https://studybuddyafrica.daily.co/{room_name}?t={token_data.get('token')}",
                "user_id": user_id,
                "user_name": user_name,
                "is_owner": False
            }
            
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to create participant token: {error_text}") from e

    def get_room(self, room_name: str) -> dict:
        """
        Get details of an existing room.
        """
        try:
            response = requests.get(f"{self.BASE_URL}/{room_name}", headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to get room details: {error_text}") from e

    def delete_room(self, room_name: str) -> bool:
        """
        Delete a room.
        Returns True if successful.
        """
        try:
            response = requests.delete(f"{self.BASE_URL}/{room_name}", headers=self.headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to delete room: {error_text}") from e

    def list_rooms(self) -> list:
        """
        List all existing rooms.
        """
        try:
            response = requests.get(self.BASE_URL, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to list rooms: {error_text}") from e


# Example usage to test:
if __name__ == "__main__":
    api = DailyCoAPI()
    
    # Create room
    room_info = api.create_room(
        name=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        end_time=datetime.now() + timedelta(hours=2),
        enable_chat=True,
        enable_screenshare=True,
        enable_emoji_reactions=True
    )
    print("Room created successfully:", room_info["url"])
    
    # Create owner token to join as owner
    try:
        owner_token = api.create_owner_token(
            room_name=room_info["name"],
            user_id="teacher_001",
            user_name="Teacher Davis",
            enable_recording=True
        )
        print("\n🎯 OWNER ACCESS LINK:")
        print(f"URL: {owner_token['room_url']}")
        print(f"Token: {owner_token['token']}")
        
        # Also create a participant token for testing
        participant_token = api.create_participant_token(
            room_name=room_info["name"],
            user_id="student_001", 
            user_name="Test Student"
        )
        print("\n👥 PARTICIPANT ACCESS LINK:")
        print(f"URL: {participant_token['room_url']}")
        print(f"Token: {participant_token['token']}")
        
    except Exception as e:
        print(f"Token creation failed: {e}")
        print(f"\nBasic room URL: {room_info['url']}")