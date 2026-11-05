"""Turn a final transcript into an intent patch.

The default proposer is a deterministic rule extractor so the demo and the
unit tests run without an INTENT_API_KEY. A live JSON client is used only
when that key is set and CALLPILOT_FORCE_MOCK is not 1.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime
from typing import Protocol

from contracts.dump import dump
from contracts.models import IntentPatch, IntentSnapshot, UpsertOp
from intent.dates import next_weekday, parse_ts

TIME_RE = re.compile(
    r"\b(\d{1,2})\s*h\b|\b(\d{1,2}):(\d{2})\b|\b(\d{1,2})\s*([ap]m)\b",
    re.IGNORECASE,
)
WEEKDAY_WORD = re.compile(r"\bmardi\b|\btuesday\b", re.IGNORECASE)
THURSDAY_WORD = re.compile(r"\bthursday\b|\bjeudi\b", re.IGNORECASE)
DECK_WORD = re.compile(r"\bdeck\b", re.IGNORECASE)
POC_WORD = re.compile(r"\bPOC\b")
STATION_WORD = re.compile(r"station\s+f", re.IGNORECASE)
TRIGGER_WORD = re.compile(r"plutôt|plutot|\bnon\b|actually|instead|改成", re.IGNORECASE)


def extract_times(text: str) -> list[str]:
    found: list[str] = []
    for match in TIME_RE.finditer(text):
        if match.group(1) is not None:
            hour = int(match.group(1))
            minute = 0
        elif match.group(2) is not None:
            hour = int(match.group(2))
            minute = int(match.group(3))
        else:
            hour = int(match.group(4))
            meridiem = match.group(5).lower()
            if meridiem == "pm" and hour < 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0
            minute = 0
        if hour > 23 or minute > 59:
            continue
        label = f"{hour:02d}:{minute:02d}"
        if label not in found:
            found.append(label)
    return found


class Proposer(Protocol):
    def propose(
        self,
        snapshot: IntentSnapshot,
        event: dict,
        call_started: datetime,
    ) -> IntentPatch | None: ...


class RuleExtractor:
    """Demo-script rules. Partials never produce a patch."""

    def propose(
        self,
        snapshot: IntentSnapshot,
        event: dict,
        call_started: datetime,
    ) -> IntentPatch | None:
        if not event.get("is_final", False):
            return None
        text = event.get("text") or ""
        ops: list[UpsertOp] = []
        event_fields, field_confidence, reason = self._event_fields(snapshot, text, call_started)
        if event_fields:
            ops.append(
                UpsertOp(
                    entity="event",
                    id="evt_1",
                    fields=event_fields,
                    reason=reason,
                    evidence=text,
                    confidence=0.9,
                    field_confidence=field_confidence,
                )
            )
        reminder_fields = self._reminder_fields(text, call_started)
        if reminder_fields:
            ops.append(
                UpsertOp(
                    entity="reminder",
                    id="rem_1",
                    fields=reminder_fields,
                    reason="extract",
                    evidence=text,
                    confidence=0.9,
                )
            )
        if not ops:
            return None
        return IntentPatch(
            ts=event["ts"],
            call_id=event["call_id"],
            utterance_id=event["utterance_id"],
            ops=ops,
        )

    def _event_fields(
        self,
        snapshot: IntentSnapshot,
        text: str,
        call_started: datetime,
    ) -> tuple[dict, dict[str, float], str]:
        fields: dict = {}
        confidence: dict[str, float] = {}
        times = extract_times(text)
        if len(times) > 1:
            fields["_time_conflict"] = True
            confidence["time"] = 0.4
        elif len(times) == 1:
            fields["time"] = times[0]
            confidence["time"] = 0.9
        if WEEKDAY_WORD.search(text):
            fields["date"] = next_weekday(call_started.date(), 1).isoformat()
            confidence["date"] = 0.9
        if STATION_WORD.search(text):
            fields["location"] = "Station F"
            confidence["location"] = 0.9
        scheduling = any(key in fields for key in ("time", "date", "location")) or len(times) > 1
        if POC_WORD.search(text):
            fields["title"] = "POC"
            confidence["title"] = 0.9
        elif scheduling and not (snapshot.event and snapshot.event.title):
            fields["title"] = "Appel"
            confidence["title"] = 0.7

        reason = "extract"
        current = snapshot.event.time if snapshot.event else ""
        new_time = fields.get("time")
        if current and isinstance(new_time, str) and new_time != current:
            reason = "correction"
        return fields, confidence, reason


    def _reminder_fields(self, text: str, call_started: datetime) -> dict:
        if not (DECK_WORD.search(text) and THURSDAY_WORD.search(text)):
            return {}
        day = next_weekday(call_started.date(), 3)
        return {"title": "Send the deck", "date": day.isoformat(), "time": "09:00"}


class LiveExtractor:
    """OpenAI-compatible JSON patch proposer. Not used in CI."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def propose(
        self,
        snapshot: IntentSnapshot,
        event: dict,
        call_started: datetime,
    ) -> IntentPatch | None:
        if not event.get("is_final", False):
            return None
        payload = build_intent_request(
            self.model,
            event.get("text") or "",
            call_started.isoformat(),
            dump(snapshot),
        )
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode())
        content = body["choices"][0]["message"]["content"]
        return parse_patch_content(content, event)


def build_intent_request(model: str, text: str, call_started: str, snapshot: dict) -> dict:
    schema = IntentPatch.model_json_schema()
    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return one JSON object matching this schema and nothing else: "
                    f"{json.dumps(schema)}. Use reason=correction when the time changes. "
                    "Timezone is Europe/Paris."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"call_started": call_started, "text": text, "snapshot": snapshot},
                    ensure_ascii=False,
                ),
            },
        ],
    }


def parse_patch_content(content: str, event: dict) -> IntentPatch:
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        raise ValueError("intent model did not return JSON")
    data = json.loads(content[start : end + 1])
    data.setdefault("ts", event["ts"])
    data.setdefault("call_id", event["call_id"])
    data.setdefault("utterance_id", event["utterance_id"])
    data["type"] = "intent.patch"
    return IntentPatch.model_validate(data)


def extractor_from_env() -> Proposer:
    if os.getenv("CALLPILOT_FORCE_MOCK") == "1" or not os.getenv("INTENT_API_KEY"):
        return RuleExtractor()
    return LiveExtractor(
        api_key=os.environ["INTENT_API_KEY"],
        base_url=os.getenv("INTENT_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("INTENT_MODEL", "gpt-4.1-mini"),
    )


def call_started_from_event(event: dict, fallback_ts: str) -> datetime:
    return parse_ts(event.get("ts") or fallback_ts)
