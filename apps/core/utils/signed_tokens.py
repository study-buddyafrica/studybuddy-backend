from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from django.conf import settings


class SignedTokenService:
    def __init__(
        self,
        secret: str | None = None,
        default_ttl_seconds: int = 900,
        namespace: str = "default",
    ):
        self.secret = secret or settings.SECRET_KEY
        self.default_ttl_seconds = default_ttl_seconds
        self.namespace = namespace

    @staticmethod
    def _b64encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def _b64decode(encoded: str) -> bytes:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(encoded + padding)

    def issue(self, payload: dict[str, Any], ttl_seconds: int | None = None) -> str:
        expires_at = int(time.time()) + (ttl_seconds or self.default_ttl_seconds)
        envelope = {
            "exp": expires_at,
            "namespace": self.namespace,
            "payload": payload,
        }
        encoded = self._b64encode(
            json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = hmac.new(
            self.secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return f"{encoded}.{signature}"

    def verify(self, token: str) -> dict[str, Any]:
        try:
            encoded, signature = token.rsplit(".", 1)
        except ValueError as exc:
            raise ValueError("Invalid token format") from exc

        expected_signature = hmac.new(
            self.secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        envelope = json.loads(self._b64decode(encoded).decode("utf-8"))
        if envelope.get("namespace") != self.namespace:
            raise ValueError("Invalid token namespace")

        if int(envelope.get("exp", 0)) < int(time.time()):
            raise ValueError("Token expired")

        return envelope["payload"]
