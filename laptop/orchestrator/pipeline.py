"""Mock call: transcripts in, verified calendar rows out."""

from __future__ import annotations

from dataclasses import dataclass, field

from confirm.ledger import Ledger, build_card
from contracts.dump import dump
from contracts.models import (
    CALENDAR_URI,
    POC_15_BEGIN,
    POC_16_BEGIN,
    Action,
    ActionFinished,
    ConfirmDecision,
    ExecRequest,
)
from executor.fake import FakeExecutor, query_request
from gui.holo import HoloClient, ScriptedHolo, default_save_script
from gui.loop import run_gui
from intent.dates import parse_ts
from intent.extract import RuleExtractor
from intent.reducer import apply_patch, apply_preview, empty_snapshot
from planner.plan import Applied, Capabilities, build_plan
from verify.calendar import parse_content_query, verify_action


@dataclass
class RunResult:
    ok: bool
    reason: str
    events: list[dict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


def run_call(
    events: list[dict],
    *,
    auto_undo: bool = False,
    extractor: RuleExtractor | None = None,
    executor: FakeExecutor | None = None,
    holo: HoloClient | None = None,
    capabilities: Capabilities | None = None,
) -> RunResult:
    extractor = extractor or RuleExtractor()
    executor = executor or FakeExecutor()
    holo = holo or ScriptedHolo(default_save_script())
    capabilities = capabilities or Capabilities()
    applied = Applied()
    ledger = Ledger()
    snapshot = None
    call_started = None
    out: list[dict] = []
    log: list[str] = []

    def emit(payload: dict) -> None:
        out.append(payload)

    for event in events:
        emit(event)
        kind = event.get("type")
        if kind == "call.started":
            call_started = parse_ts(event["ts"])
            snapshot = empty_snapshot(event["call_id"], event["ts"])
            log.append(f"[call] started {event.get('capture', 'voice_call')}")
            continue
        if kind in {"transcript.partial", "transcript.final"}:
            if snapshot is None:
                call_started = parse_ts(event["ts"])
                snapshot = empty_snapshot(event["call_id"], event["ts"])
            is_final = bool(event.get("is_final")) and kind == "transcript.final"
            if not is_final:
                snapshot = apply_preview(snapshot, event.get("text") or "", event["ts"])
                emit(dump(snapshot))
                log.append(f"[preview] {event.get('text')}")
                continue
            assert call_started is not None
            patch = extractor.propose(snapshot, event, call_started)
            if patch is None:
                snapshot = apply_preview(snapshot, event.get("text") or "", event["ts"])
                emit(dump(snapshot))
                continue
            emit(dump(patch))
            snapshot = apply_patch(snapshot, patch)
            emit(dump(snapshot))
            when = snapshot.event.time if snapshot.event else "-"
            log.append(f"[snapshot r{snapshot.revision}] time={when} stable={snapshot.event.stability if snapshot.event else '-'}")
            plan = build_plan(snapshot, capabilities, applied)
            if plan is None:
                continue
            emit(dump(plan))
            log.append("[plan] " + ", ".join(action.kind for action in plan.actions))
            for action in plan.actions:
                _run_action(action, executor, holo, snapshot.ts, snapshot.call_id, applied, ledger, emit, log)
            continue
        if kind == "call.ended":
            if snapshot is None:
                continue
            card = build_card(snapshot)
            emit(dump(card))
            log.append("[confirm] " + " | ".join(item.summary for item in card.items))
            if auto_undo:
                decision = ConfirmDecision(card_id=card.card_id, decision="undo_reminder")
                emit(dump(decision))
                undo = ledger.handle(snapshot, "undo_reminder")
                if undo is not None:
                    _run_action(undo, executor, holo, event["ts"], snapshot.call_id, applied, ledger, emit, log)
                    ledger.mark_reverted("act_rem")
                    log.append("[undo] reminder")

    rows = [_row_dict(row) for row in _read_rows(executor)]
    ok, reason = _judge(rows, out, auto_undo)
    if ok:
        log.append("[ok] POC at 16:00, reminder undone" if auto_undo else "[ok] POC at 16:00")
    else:
        log.append(f"[fail] {reason}")
    return RunResult(ok=ok, reason=reason, events=out, log=log, rows=rows)


def _run_action(action, executor, holo, ts, call_id, applied, ledger, emit, log) -> None:
    steps, finished = _perform(action, executor, holo, ts, call_id)
    for step in steps:
        emit(step)
        if step.get("tool") == "click" and step.get("pixel"):
            pixel = step["pixel"]
            log.append(f"[gui] click -> ({pixel['x']}, {pixel['y']})")
    emit(dump(finished))
    rows = _read_rows(executor)
    result = verify_action(action, rows, ts, call_id)
    emit(dump(result))
    log.append(f"[verify] {action.kind} matched={result.matched}")
    if result.matched:
        ledger.record(action)
        if action.kind in {"calendar.create", "calendar.update"}:
            applied.event_begin = int(action.payload["beginTime"])
        elif action.kind == "reminder.create":
            applied.reminder = True
        elif action.kind == "note.create":
            applied.note_text = str(action.payload.get("text") or "")


def _perform(action: Action, executor: FakeExecutor, holo: HoloClient, ts: str, call_id: str):
    if action.strategy == "panel" or action.kind == "note.create":
        return [], ActionFinished(
            ts=ts,
            call_id=call_id,
            action_id=action.action_id,
            ok=True,
            stop="answer",
            steps=0,
            answer=str(action.payload.get("text") or ""),
        )
    if action.kind == "calendar.delete" or action.strategy == "content":
        match = action.payload.get("match") or {}
        executor.execute(
            ExecRequest(
                id=f"{action.action_id}-delete",
                op="content_delete",
                uri=CALENDAR_URI,
                title=str(match.get("title") or ""),
                dtstart=int(match["beginTime"]),
            )
        )
        return [], ActionFinished(
            ts=ts,
            call_id=call_id,
            action_id=action.action_id,
            ok=True,
            stop="answer",
            steps=0,
            answer="deleted",
        )
    extras = {
        key: action.payload[key]
        for key in ("title", "eventLocation", "description", "beginTime", "endTime")
        if key in action.payload
    }
    executor.execute(
        ExecRequest(
            id=f"{action.action_id}-insert",
            op="am_start",
            action="android.intent.action.INSERT",
            data=CALENDAR_URI,
            extras=extras,
        )
    )
    steps: list[dict] = []
    finished = ActionFinished(
        ts=ts,
        call_id=call_id,
        action_id=action.action_id,
        ok=False,
        stop="executor_error",
        steps=0,
    )
    for _attempt in range(3):
        more, finished = run_gui(action, executor, holo, ts=ts, call_id=call_id)
        steps.extend(more)
        if verify_action(action, _read_rows(executor), ts, call_id).matched:
            return steps, finished
    executor.execute(
        ExecRequest(id=f"{action.action_id}-fallback", op="tap", x=executor.save_xy[0], y=executor.save_xy[1])
    )
    if verify_action(action, _read_rows(executor), ts, call_id).matched:
        finished = ActionFinished(
            ts=ts,
            call_id=call_id,
            action_id=action.action_id,
            ok=True,
            stop="answer",
            steps=len(steps),
            answer="saved with calibrated tap",
        )
    return steps, finished


def _read_rows(executor: FakeExecutor):
    result = executor.execute(query_request())
    return parse_content_query(result.stdout)


def _row_dict(row) -> dict:
    return dump(row)


def _judge(rows: list[dict], events: list[dict], auto_undo: bool) -> tuple[bool, str]:
    poc = [row for row in rows if row.get("title") == "POC"]
    deck = [row for row in rows if row.get("title") == "Send the deck"]
    if len(poc) != 1:
        return False, f"expected one POC row, found {len(poc)}"
    if poc[0].get("dtstart") != POC_16_BEGIN:
        return False, f"POC dtstart is {poc[0].get('dtstart')}"
    if "Station F" not in str(poc[0].get("eventLocation") or ""):
        return False, "POC location is not Station F"
    if auto_undo and deck:
        return False, "Send the deck is still on the calendar"
    if not auto_undo and not deck:
        return False, "Send the deck was not created"
    saw_15 = any(
        event.get("type") == "verify.result"
        and event.get("matched")
        and (event.get("row") or {}).get("dtstart") == POC_15_BEGIN
        for event in events
    )
    if not saw_15:
        return False, "15:00 draft was not verified"
    if not any(event.get("type") == "agent.step" and event.get("tool") == "click" for event in events):
        return False, "GUI loop did not click"
    if not any(event.get("type") == "confirm.request" for event in events):
        return False, "confirm card was not emitted"
    if poc[0].get("dtstart") != POC_16_BEGIN:
        return False, "correction did not stick"
    return True, "ok"
