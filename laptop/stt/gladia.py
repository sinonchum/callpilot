"""Gladia session init. The mock stream is what CI actually runs."""

from __future__ import annotations

import json
import os
import urllib.request


def init_payload(*, channels: int = 1, sample_rate: int = 16000) -> dict:
    return {
        "model": "solaria-1",
        "encoding": "wav/pcm",
        "sample_rate": sample_rate,
        "bit_depth": 16,
        "channels": channels,
        "endpointing": 0.05,
        "maximum_duration_without_endpointing": 5,
        "language_config": {"languages": ["fr", "en"], "code_switching": True},
        "messages_config": {
            "receive_partial_transcripts": True,
            "receive_final_transcripts": True,
        },
    }


class GladiaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.gladia.io") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def create_session(self, *, channels: int = 1, sample_rate: int = 16000) -> dict:
        payload = init_payload(channels=channels, sample_rate=sample_rate)
        request = urllib.request.Request(
            self.base_url + "/v2/live",
            data=json.dumps(payload).encode(),
            headers={"x-gladia-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())


def gladia_from_env() -> GladiaClient | None:
    if os.getenv("CALLPILOT_FORCE_MOCK") == "1" or not os.getenv("GLADIA_API_KEY"):
        return None
    return GladiaClient(
        api_key=os.environ["GLADIA_API_KEY"],
        base_url=os.getenv("GLADIA_BASE_URL", "https://api.gladia.io"),
    )
