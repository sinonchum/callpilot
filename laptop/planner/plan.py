"""Choose intent-prefill vs GUI and attach an inverse for every action."""

from __future__ import annotations

from dataclasses import dataclass

from contracts.dump import dump
from contracts.models import Action, IntentSnapshot, Inverse, PlanCreated


@dataclass
class Applied:
    """What has already been written. A second pass becomes an update."""

    event_begin: int | None = None
    reminder: bool = False
    note_text: str | None = None


@dataclass
class Capabilities:
    calendar_insert: bool = True


def build_plan(
    snapshot: IntentSnapshot,
    capabilities: Capabilities,
    applied: Applied,
) -> PlanCreated | None:
    actions: list[Action] = []
    event = snapshot.event
    if event and event.stability == "stable" and event.beginTime is not None and event.endTime is not None:
        actions.append(_calendar_action(snapshot, capabilities, applied))
    reminder = snapshot.reminder
    if (
        reminder
        and reminder.stability == "stable"
        and reminder.beginTime is not None
        and not applied.reminder
    ):
        actions.append(_reminder_action(snapshot, capabilities))
    note = snapshot.note
    if note and note.stability == "stable" and note.text and note.text != applied.note_text:
        actions.append(
            Action(
                action_id="act_note",
                kind="note.create",
                strategy="panel",
                payload={"text": note.text},
                inverse=Inverse(kind="note.hide", payload={}),
            )
        )
    actions = [action for action in actions if action is not None]
    if not actions:
        return None
    return PlanCreated(
        ts=snapshot.ts,
        call_id=snapshot.call_id,
        plan_id=f"plan_{snapshot.revision}",
        revision=snapshot.revision,
        actions=actions,
    )


def _strategy(capabilities: Capabilities) -> str:
    return "intent_prefill" if capabilities.calendar_insert else "gui"


def _calendar_action(
    snapshot: IntentSnapshot,
    capabilities: Capabilities,
    applied: Applied,
) -> Action:
    event = snapshot.event
    assert event is not None and event.beginTime is not None and event.endTime is not None
    payload = {
        "title": event.title,
        "eventLocation": event.location,
        "description": "CallPilot",
        "beginTime": event.beginTime,
        "endTime": event.endTime,
    }
    if applied.event_begin is None:
        return Action(
            action_id="act_evt",
            kind="calendar.create",
            strategy=_strategy(capabilities),
            payload=payload,
            inverse=Inverse(
                kind="calendar.delete",
                payload={"match": {"title": event.title, "beginTime": event.beginTime}},
            ),
        )
    payload["match"] = {"title": event.title, "beginTime": applied.event_begin}
    return Action(
        action_id="act_evt",
        kind="calendar.update",
        strategy=_strategy(capabilities),
        payload=payload,
        inverse=Inverse(
            kind="calendar.update",
            payload={
                "match": {"title": event.title, "beginTime": event.beginTime},
                "beginTime": applied.event_begin,
                "endTime": applied.event_begin + 60 * 60 * 1000,
            },
        ),
    )


def _reminder_action(snapshot: IntentSnapshot, capabilities: Capabilities) -> Action:
    reminder = snapshot.reminder
    assert reminder is not None and reminder.beginTime is not None and reminder.endTime is not None
    return Action(
        action_id="act_rem",
        kind="reminder.create",
        strategy=_strategy(capabilities),
        payload={
            "title": reminder.title,
            "description": "CallPilot",
            "beginTime": reminder.beginTime,
            "endTime": reminder.endTime,
        },
        inverse=Inverse(
            kind="calendar.delete",
            payload={"match": {"title": reminder.title, "beginTime": reminder.beginTime}},
        ),
    )


def plan_dict(plan: PlanCreated) -> dict:
    return dump(plan)
