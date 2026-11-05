"""Pydantic models for the v1 messages in docs/DEV_PLAN.md.

Field names match the plan. `from` is a Python keyword, so the correction
model accepts it via alias.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TranscriptEvent(BaseModel):
    v: int = 1
    type: Literal["transcript.partial", "transcript.final"]
    ts: str
    call_id: str
    utterance_id: str
    is_final: bool
    text: str
    channel: int | None = None
    speaker: Literal["me", "them", "unknown"] = "unknown"
    language: str | None = None
    start: float | None = None
    end: float | None = None
    confidence: float | None = None


class CallStarted(BaseModel):
    v: int = 1
    type: Literal["call.started"] = "call.started"
    ts: str
    call_id: str
    capture: str = "voice_call"
    timezone: str = "Europe/Paris"


class CallEnded(BaseModel):
    v: int = 1
    type: Literal["call.ended"] = "call.ended"
    ts: str
    call_id: str
    reason: str = "hangup"


class FieldState(BaseModel):
    stability: Literal["preview", "stable"]
    confidence: float


class Correction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_id: str
    field: str
    from_value: str = Field(alias="from")
    to: str
    utterance_id: str


class CalendarFields(BaseModel):
    id: str
    title: str = ""
    date: str = ""
    time: str = ""
    timezone: str = "Europe/Paris"
    duration_min: int = 60
    location: str = ""
    beginTime: int | None = None
    endTime: int | None = None
    status: Literal["proposed", "corrected", "executed", "reverted"] = "proposed"
    stability: Literal["preview", "stable"] = "preview"
    fields: dict[str, FieldState] = Field(default_factory=dict)


class ReminderFields(BaseModel):
    id: str
    title: str = ""
    date: str = ""
    time: str = ""
    beginTime: int | None = None
    endTime: int | None = None
    stability: Literal["preview", "stable"] = "preview"
    fields: dict[str, FieldState] = Field(default_factory=dict)


class NoteFields(BaseModel):
    id: str
    text: str = ""
    stability: Literal["preview", "stable"] = "preview"


class IntentSnapshot(BaseModel):
    v: int = 1
    type: Literal["intent.snapshot"] = "intent.snapshot"
    ts: str
    call_id: str
    revision: int = 0
    preview: str = ""
    event: CalendarFields | None = None
    reminder: ReminderFields | None = None
    note: NoteFields | None = None
    corrections: list[Correction] = Field(default_factory=list)


class UpsertOp(BaseModel):
    op: Literal["upsert"] = "upsert"
    entity: Literal["event", "reminder", "note"]
    id: str
    fields: dict[str, Any] = Field(default_factory=dict)
    reason: Literal["extract", "correction"] = "extract"
    evidence: str = ""
    confidence: float = 0.9
    field_confidence: dict[str, float] = Field(default_factory=dict)


class IntentPatch(BaseModel):
    v: int = 1
    type: Literal["intent.patch"] = "intent.patch"
    ts: str
    call_id: str
    utterance_id: str
    ops: list[UpsertOp] = Field(default_factory=list)


class Inverse(BaseModel):
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    action_id: str
    kind: str
    strategy: Literal["intent_prefill", "gui", "panel", "content"]
    payload: dict[str, Any] = Field(default_factory=dict)
    inverse: Inverse


class PlanCreated(BaseModel):
    v: int = 1
    type: Literal["plan.created"] = "plan.created"
    ts: str
    call_id: str
    plan_id: str
    revision: int
    actions: list[Action]


class ExecRequest(BaseModel):
    v: int = 1
    id: str
    op: Literal[
        "tap",
        "swipe",
        "text",
        "keyevent",
        "screencap",
        "am_start",
        "content_query",
        "content_delete",
        "wait",
    ]
    x: int | None = None
    y: int | None = None
    x1: int | None = None
    y1: int | None = None
    x2: int | None = None
    y2: int | None = None
    duration_ms: int | None = None
    text: str | None = None
    keycode: int | None = None
    action: str | None = None
    data: str | None = None
    extras: dict[str, Any] | None = None
    uri: str | None = None
    projection: str | None = None
    title: str | None = None
    dtstart: int | None = None
    wait_ms: int | None = None


class ExecResult(BaseModel):
    v: int = 1
    id: str
    ok: bool
    width: int = 0
    height: int = 0
    screenshot_png_b64: str = ""
    stdout: str = ""
    latency_ms: int = 0
    error: str | None = None


class Pixel(BaseModel):
    x: int
    y: int


class AgentStep(BaseModel):
    v: int = 1
    type: Literal["agent.step"] = "agent.step"
    ts: str
    call_id: str
    action_id: str
    step_index: int
    model: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    pixel: Pixel | None = None
    screenshot_width: int | None = None
    screenshot_height: int | None = None
    ok: bool = True
    latency_ms: int = 0
    error: str | None = None


class ActionFinished(BaseModel):
    v: int = 1
    type: Literal["action.finished"] = "action.finished"
    ts: str
    call_id: str
    action_id: str
    ok: bool
    stop: Literal["answer", "step_budget", "executor_error"]
    steps: int
    answer: str = ""


class CalendarRow(BaseModel):
    title: str
    dtstart: int
    dtend: int | None = None
    eventLocation: str = ""


class VerifyResult(BaseModel):
    v: int = 1
    type: Literal["verify.result"] = "verify.result"
    ts: str
    call_id: str
    action_id: str
    method: str
    uri: str = ""
    matched: bool
    row: CalendarRow | None = None


class ConfirmItem(BaseModel):
    action_id: str
    label: str
    summary: str


class ConfirmRequest(BaseModel):
    v: int = 1
    type: Literal["confirm.request"] = "confirm.request"
    card_id: str
    call_id: str
    items: list[ConfirmItem]


class ConfirmDecision(BaseModel):
    v: int = 1
    type: Literal["confirm.decision"] = "confirm.decision"
    card_id: str
    decision: Literal["confirm", "undo_reminder"]


class LedgerEntry(BaseModel):
    v: int = 1
    type: Literal["ledger.entry"] = "ledger.entry"
    entry_id: str
    action_id: str
    status: Literal["applied", "reverted"]
    forward_kind: str
    inverse_kind: str


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "transcript.final": TranscriptEvent,
    "intent.patch": IntentPatch,
    "intent.snapshot": IntentSnapshot,
    "plan.created": PlanCreated,
    "exec.request": ExecRequest,
    "exec.result": ExecResult,
    "agent.step": AgentStep,
    "action.finished": ActionFinished,
    "verify.result": VerifyResult,
    "confirm.request": ConfirmRequest,
    "confirm.decision": ConfirmDecision,
    "ledger.entry": LedgerEntry,
}

CALENDAR_URI = "content://com.android.calendar/events"
POC_15_BEGIN = 1794319200000
POC_15_END = 1794322800000
POC_16_BEGIN = 1794322800000
POC_16_END = 1794326400000
DECK_BEGIN = 1794470400000
DECK_END = 1794474000000
