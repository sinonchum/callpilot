"""Recorded Gladia stream. PCM frames are validated and then ignored."""

from __future__ import annotations

from collections.abc import Iterable

from stt.pcm import decode_frame


class MockGladiaStream:
    def __init__(self, events: list[dict]) -> None:
        self.events = events

    def transcribe(self, frames: Iterable[bytes] | None = None) -> list[dict]:
        if frames is not None:
            for frame in frames:
                decode_frame(frame)
        return [event for event in self.events if str(event.get("type", "")).startswith("transcript")]
