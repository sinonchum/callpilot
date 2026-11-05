"""Pure reducer: patch in, snapshot out. Partials only touch preview."""

from __future__ import annotations

from contracts.models import (
    CalendarFields,
    Correction,
    FieldState,
    IntentPatch,
    IntentSnapshot,
    NoteFields,
    ReminderFields,
    UpsertOp,
)
from intent.dates import add_minutes_ms, epoch_ms
from datetime import date


def empty_snapshot(call_id: str, ts: str) -> IntentSnapshot:
    return IntentSnapshot(ts=ts, call_id=call_id, revision=0)


def apply_preview(snapshot: IntentSnapshot, text: str, ts: str) -> IntentSnapshot:
    updated = snapshot.model_copy(deep=True)
    updated.ts = ts
    updated.preview = text
    return updated


def apply_patch(snapshot: IntentSnapshot, patch: IntentPatch) -> IntentSnapshot:
    updated = snapshot.model_copy(deep=True)
    updated.ts = patch.ts
    updated.revision += 1
    updated.preview = patch.ops[0].evidence if patch.ops else updated.preview
    for op in patch.ops:
        if op.entity == "event":
            updated.event = _apply_event(updated, op, patch.utterance_id)
        elif op.entity == "reminder":
            updated.reminder = _apply_reminder(updated.reminder, op)
    _refresh_note(updated)
    return updated


def _confidence(op: UpsertOp, key: str) -> float:
    return op.field_confidence.get(key, op.confidence)


def _apply_event(snapshot: IntentSnapshot, op: UpsertOp, utterance_id: str) -> CalendarFields:
    event = snapshot.event.model_copy(deep=True) if snapshot.event else CalendarFields(id=op.id)
    event.id = op.id or event.id
    conflict = bool(op.fields.get("_time_conflict"))
    for key, value in op.fields.items():
        if key.startswith("_"):
            continue
        previous = getattr(event, key, None)
        setattr(event, key, value)
        stable = _confidence(op, key) >= 0.6 and not (key == "time" and conflict)
        event.fields[key] = FieldState(
            stability="stable" if stable else "preview",
            confidence=_confidence(op, key),
        )
        if (
            key == "time"
            and op.reason == "correction"
            and isinstance(previous, str)
            and previous
            and previous != value
        ):
            snapshot.corrections.append(
                Correction(
                    target_id=event.id,
                    field="time",
                    from_value=previous,
                    to=str(value),
                    utterance_id=utterance_id,
                )
            )
            event.status = "corrected"
    time_state = event.fields.get("time")
    date_state = event.fields.get("date")
    time_ok = bool(event.time) and time_state is not None and time_state.stability == "stable" and not conflict
    date_ok = bool(event.date) and (date_state is None or date_state.stability == "stable")
    if time_ok and date_ok:
        event.stability = "stable"
        _fill_bounds(event)
    else:
        event.stability = "preview"
        if time_ok and event.date:
            _fill_bounds(event)
    return event


def _fill_bounds(event: CalendarFields) -> None:
    if not event.date or not event.time:
        return
    hour, minute = (int(part) for part in event.time.split(":"))
    begin = epoch_ms(date.fromisoformat(event.date), hour, minute)
    event.beginTime = begin
    event.duration_min = 60
    event.endTime = add_minutes_ms(begin, 60)
    event.timezone = "Europe/Paris"


def _apply_reminder(current: ReminderFields | None, op: UpsertOp) -> ReminderFields:
    reminder = current.model_copy(deep=True) if current else ReminderFields(id=op.id)
    reminder.id = op.id or reminder.id
    for key, value in op.fields.items():
        if key.startswith("_"):
            continue
        setattr(reminder, key, value)
        reminder.fields[key] = FieldState(stability="stable", confidence=op.confidence)
    if reminder.date and reminder.time:
        hour, minute = (int(part) for part in reminder.time.split(":"))
        begin = epoch_ms(date.fromisoformat(reminder.date), hour, minute)
        reminder.beginTime = begin
        reminder.endTime = add_minutes_ms(begin, 60)
        reminder.stability = "stable" if op.confidence >= 0.6 else "preview"
    return reminder


def _refresh_note(snapshot: IntentSnapshot) -> None:
    event = snapshot.event
    if event is None or not event.time:
        return
    when = date.fromisoformat(event.date).strftime("%A") if event.date else ""
    place = f" at {event.location}" if event.location else ""
    text = f"{event.title}{place}, {when} {event.time}."
    if snapshot.reminder and snapshot.reminder.title:
        text += " Send the deck before Thursday."
    stability = "stable" if event.stability == "stable" else "preview"
    snapshot.note = NoteFields(id="note_1", text=text, stability=stability)
