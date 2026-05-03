from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from django.conf import settings


class ZoomSDKTokenService:
    def __init__(self):
        self.sdk_key = settings.ZOOM_SDK_KEY
        self.sdk_secret = settings.ZOOM_SDK_SECRET
        self.ttl_seconds = settings.ZOOM_SDK_TOKEN_TTL_SECONDS
        self.mock_mode = not (self.sdk_key and self.sdk_secret)

    @staticmethod
    def _encode_json(payload: dict[str, object]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def generate_signature(
        self,
        meeting_number: str,
        role: int,
        user_identity: str,
        user_name: str,
    ) -> dict[str, object]:
        payload = {
            "sdk_key": self.sdk_key or "mock-sdk-key",
            "meeting_number": str(meeting_number),
            "role": int(role),
            "user_identity": user_identity,
            "user_name": user_name,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.ttl_seconds,
            "token_exp": int(time.time()) + self.ttl_seconds,
            "version": 1,
        }

        if self.mock_mode:
            token = f"mock-zoom-{meeting_number}-{user_identity}"
            return {
                "signature": token,
                "mock_mode": True,
                "expires_at": payload["exp"],
                "payload": payload,
            }

        header = {"alg": "HS256", "typ": "JWT"}
        signing_input = f"{self._encode_json(header)}.{self._encode_json(payload)}"
        signature = hmac.new(
            self.sdk_secret.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        token = f"{signing_input}.{base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')}"

        return {
            "signature": token,
            "mock_mode": False,
            "expires_at": payload["exp"],
            "payload": payload,
        }
