import os
import requests
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()


class MiroAPI:
    """
    Simple wrapper for Miro REST API (whiteboards only).
    """

    BASE_URL = "https://api.miro.com/v2"

    def __init__(self, access_token: Optional[str] = None):
        """
        :param access_token: Miro personal access token or OAuth token.
        """
        self.access_token = access_token or os.getenv("MIRO_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("Missing MIRO_ACCESS_TOKEN in environment variables or constructor.")

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }


    def create_board(
        self,
        name: str,
        description: Optional[str] = "",
        sharing_policy: str = "PRIVATE",
    ) -> Dict[str, str]:
        """
        Create a new Miro whiteboard.

        :param name: Board name
        :param description: Optional board description
        :param sharing_policy: 'private', 'team_visible', 'public'
        :return: Dict with 'id' and 'url'
        """
        payload = {
            "name": name,
            "description": description,
            "sharingPolicy": {"access": sharing_policy}
        }

        try:
            response = requests.post(f"{self.BASE_URL}/boards", headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "id": data.get("id"),
                "url": data.get("viewLink")
            }

        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to create Miro board: {error_text}") from e

    def get_board(self, board_id: str) -> Dict:
        """
        Retrieve a board by its ID.
        """
        try:
            response = requests.get(f"{self.BASE_URL}/boards/{board_id}", headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to get Miro board: {error_text}") from e

    def delete_board(self, board_id: str) -> bool:
        """
        Delete a board.
        Returns True if deletion was successful.
        """
        try:
            response = requests.delete(f"{self.BASE_URL}/boards/{board_id}", headers=self.headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to delete Miro board: {error_text}") from e


    def share_board_with_users(self, board_id: str, user_emails: List[str], role: str = "editor") -> Dict:
        """
        Share board with specific users.
        Uses Miro's collaborators endpoint with PUT request.
        
        :param board_id: Miro board ID
        :param user_emails: List of emails
        :param role: 'viewer', 'commenter', or 'editor'
        """
        url = f"{self.BASE_URL}/boards/{board_id}/collaborators"
        payload = {
            "collaborators": [{"email": email, "role": role.lower()} for email in user_emails]
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            error_text = getattr(e.response, "text", str(e))
            raise RuntimeError(f"Failed to share Miro board: {error_text}") from e


# ---------------------- Example Usage ---------------------- #
if __name__ == "__main__":
    miro = MiroAPI()  

    board = miro.create_board(name="Math Session Whiteboard", description="Board for Algebra lesson")
    print("Board created:", board["url"])

  
