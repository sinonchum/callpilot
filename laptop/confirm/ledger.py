"""Hang-up card, idempotent confirm, and reminder undo."""

from __future__ import annotations

from contracts.models import (
    Action,
    ConfirmItem,
    ConfirmRequest,
    IntentSnapshot,
    Inverse,
    LedgerEntry,
)
from intent.dates import WEEKDAY_ZH
from datetime import date


class Ledger:
    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []
        self.confirmed = False
        self.undone = False
        self._seq = 0

    def record(self, action: Action) -> LedgerEntry:
        self._seq += 1
        entry = LedgerEntry(
            entry_id=f"led_{self._seq}",
            action_id=action.action_id,
            status="applied",
            forward_kind=action.kind,
            inverse_kind=action.inverse.kind,
        )
        self.entries.append(entry)
        return entry

    def mark_reverted(self, action_id: str) -> None:
        for entry in self.entries:
            if entry.action_id == action_id and entry.inverse_kind == "calendar.delete":
                entry.status = "reverted"

    def handle(self, snapshot: IntentSnapshot, decision: str) -> Action | None:
        if decision == "confirm":
            self.confirmed = True
            return None
        if decision != "undo_reminder" or self.undone:
            return None
        action = decision_action(snapshot, decision)
        if action is not None:
            self.undone = True
        return action


def build_card(snapshot: IntentSnapshot, card_id: str = "card_1") -> ConfirmRequest:
    items: list[ConfirmItem] = []
    event = snapshot.event
    if event and event.beginTime is not None and event.date:
        weekday = WEEKDAY_ZH[date.fromisoformat(event.date).weekday()]
        items.append(
            ConfirmItem(
                action_id="act_evt",
                label="日历",
                summary=f"{weekday} {event.time} · {event.location} · {event.title}",
            )
        )
    reminder = snapshot.reminder
    if reminder and reminder.date:
        weekday = WEEKDAY_ZH[date.fromisoformat(reminder.date).weekday()]
        items.append(
            ConfirmItem(
                action_id="act_rem",
                label="提醒",
                summary=f"{weekday} {reminder.time} · 发 deck",
            )
        )
    if snapshot.note and snapshot.note.text:
        items.append(
            ConfirmItem(action_id="act_note", label="便签", summary=snapshot.note.text)
        )
    return ConfirmRequest(card_id=card_id, call_id=snapshot.call_id, items=items)


def decision_action(snapshot: IntentSnapshot, decision: str) -> Action | None:
    """Confirm keeps results. Undo deletes the deck reminder from the calendar."""
    if decision != "undo_reminder":
        return None
    reminder = snapshot.reminder
    if reminder is None or reminder.beginTime is None:
        return None
    return Action(
        action_id="act_undo_rem",
        kind="calendar.delete",
        strategy="content",
        payload={"match": {"title": reminder.title, "beginTime": reminder.beginTime}},
        inverse=Inverse(kind="noop", payload={}),
    )
