import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


class DailyCoAPI:
    """
    Production-ready wrapper for Daily.co REST API.
    - Backwards compatible: create_room accepts either `properties` dict OR legacy keyword flags
      (e.g., enable_chat=True, enable_screenshare=True).
    - Token creation supports enable_recording for owners.
    - room_url_base is configurable so you can use your custom subdomain.
    """

    BASE_URL = "https://api.daily.co/v1"

    def __init__(self, api_key: Optional[str] = None, room_url_base: Optional[str] = None):
        self.api_key = api_key or os.getenv("DAILY_API_KEY")
        if not self.api_key:
            raise ValueError("Missing DAILY_API_KEY in environment variables or constructor.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # e.g. "https://studybuddyafrica.daily.co"
        self.room_url_base = room_url_base or os.getenv("DAILY_ROOM_URL_BASE", "https://studybuddyafrica.daily.co")

    # ---------------------- ROOM MANAGEMENT ---------------------- #

    def create_room(
        self,
        name: str,
        end_time: datetime,
        privacy: str = "public",
        properties: Optional[Dict[str, Any]] = None,
        **legacy_flags: Any,
    ) -> Dict[str, Any]:
        """
        Create a Daily.co room.

        Backwards compatible:
          - You can pass a `properties` dict (preferred), OR
          - pass legacy keyword flags like `enable_chat=True`, `enable_screenshare=True`, etc.
        Legacy flags will be merged with defaults and with `properties` (properties wins).
        """
        default_props: Dict[str, Any] = {
            "enable_chat": True,
            "enable_screenshare": True,
            "start_audio_off": False,
            "start_video_off": False,
            "enable_prejoin_ui": True,
            "enable_people_ui": True,
            "enable_network_ui": True,
            "enable_pip_ui": True,
            "enable_emoji_reactions": True,
            "enable_advanced_chat": True,
            "exp": int(end_time.timestamp()),
        }

        # Accept legacy flags and convert them to properties if provided
        legacy_props = {k: v for k, v in legacy_flags.items() if k.startswith("enable_") or k.startswith("start_") or k in default_props}
        # Merge order: defaults <- legacy_props <- explicit properties (explicit overrides all)
        final_props = {**default_props, **legacy_props, **(properties or {})}

        payload = {
            "name": name,
            "privacy": privacy,
            "properties": final_props
        }

        resp = self._request("POST", f"{self.BASE_URL}/rooms", json=payload)

        # Normalize return object
        return {
            "url": resp.get("url"),
            "name": resp.get("name") or name,
            "privacy": resp.get("privacy", privacy),
            "expires_at": datetime.fromtimestamp(final_props["exp"]).isoformat() if final_props.get("exp") else None,
            "id": resp.get("id"),
            "raw": resp
        }

    def get_room(self, room_name: str) -> Dict[str, Any]:
        """Retrieve details of a room by name."""
        return self._request("GET", f"{self.BASE_URL}/rooms/{room_name}")

    def list_rooms(self) -> List[Dict[str, Any]]:
        """List all existing rooms."""
        data = self._request("GET", f"{self.BASE_URL}/rooms")
        return data.get("data", [])

    def delete_room(self, room_name: str) -> bool:
        """Delete a room by name."""
        self._request("DELETE", f"{self.BASE_URL}/rooms/{room_name}")
        return True

    # ---------------------- TOKEN MANAGEMENT ---------------------- #

    def create_token(
        self,
        room_name: str,
        user_id: str,
        user_name: str,
        is_owner: bool = False,
        extra_properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a meeting token (owner or participant).
        Recording permissions are now controlled via room settings, not tokens.
        """
        token_payload = {
            "properties": {
                "room_name": room_name,
                "user_id": user_id,
                "user_name": user_name,
                "is_owner": is_owner,
                "start_audio_off": False,
                "start_video_off": False,
                **(extra_properties or {})
            }
        }

        token_data = self._request("POST", f"{self.BASE_URL}/meeting-tokens", json=token_payload)

        token = token_data.get("token")
        room_url = f"{self.room_url_base}/{room_name}"
        if token:
            room_url = f"{room_url}?t={token}"

        return {
            "token": token,
            "room_url": room_url,
            "user_id": user_id,
            "user_name": user_name,
            "is_owner": is_owner,
            "raw": token_data
        }

    def create_owner_token(self, room_name: str, user_id: str, user_name: str) -> Dict[str, Any]:
        """Create a token for the session owner (teacher/admin)."""
        return self.create_token(room_name, user_id, user_name, is_owner=True)

    def create_participant_token(self, room_name: str, user_id: str, user_name: str) -> Dict[str, Any]:
        """Create a token for a regular participant (student/employee)."""
        return self.create_token(room_name, user_id, user_name, is_owner=False)

    # ---------------------- INTERNAL UTIL ---------------------- #

    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Internal helper for API requests with robust error handling.
        Returns parsed JSON or raises RuntimeError with clear details.
        """
        try:
            response = requests.request(method, url, headers=self.headers, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else {}

        except requests.HTTPError as e:
            # use response from exception if available
            resp = getattr(e, "response", None)
            status = resp.status_code if resp is not None else "N/A"
            text = resp.text if resp is not None else str(e)
            raise RuntimeError(f"HTTP {status}: {text}") from e

        except requests.RequestException as e:
            raise RuntimeError(f"Request failed: {str(e)}") from e


# ---------------------- Example usage ---------------------- #
if __name__ == "__main__":
    from datetime import timedelta, datetime

    api = DailyCoAPI()  #
    # Example 1: New-style (preferred)
    room = api.create_room(
        name="math_class_2025_07",
        end_time=datetime.now() + timedelta(hours=1),
        properties={
            "enable_chat": True,
            "enable_screenshare": True,
        }
    )
    print("Room created successfully:", room["url"])

    # Example 2: Old-style legacy flags (backwards compatible)
    room2 = api.create_room(
        name="legacy_room4",
        end_time=datetime.now() + timedelta(hours=1),
        enable_chat=True,
        enable_screenshare=True,
    )
    print("Legacy room created:", room2["url"])

    # Token creation (owner with recording)
    try:
        owner = api.create_owner_token(room_name="math_class_2025_07", user_id="t123", user_name="Mr.Davis")
        print("Owner token created, link:", owner["room_url"])
    except Exception as exc:
        print("Token creation failed:", exc)

    # Participant token
    participant = api.create_participant_token(room_name="math_class_2025_07", user_id="s456", user_name="StudentA")
    print("Participant link:", participant["room_url"])
