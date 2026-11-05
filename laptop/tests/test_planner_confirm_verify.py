from datetime import datetime
from zoneinfo import ZoneInfo

from confirm.ledger import Ledger, build_card
from contracts.models import POC_15_BEGIN, POC_16_BEGIN, CalendarRow
from intent.extract import RuleExtractor
from intent.reducer import apply_patch, empty_snapshot
from planner.plan import Applied, Capabilities, build_plan
from verify.calendar import parse_content_query, verify_action

PARIS = ZoneInfo("Europe/Paris")
FULL = (
    "On se voit mardi prochain à 15h à Station F pour le POC… "
    "and can you send me the deck before Thursday?"
)


def _snapshot(texts: list[str]):
    started = datetime(2026, 11, 7, 10, 0, tzinfo=PARIS)
    snapshot = empty_snapshot("call_demo", started.isoformat())
    extractor = RuleExtractor()
    for index, text in enumerate(texts):
        event = {
            "ts": started.isoformat(),
            "call_id": "call_demo",
            "utterance_id": f"u{index}",
            "is_final": True,
            "text": text,
        }
        patch = extractor.propose(snapshot, event, started)
        assert patch is not None
        snapshot = apply_patch(snapshot, patch)
    return snapshot


def test_create_then_same_snapshot_becomes_update() -> None:
    snapshot = _snapshot([FULL])
    first = build_plan(snapshot, Capabilities(), Applied())
    assert first is not None
    assert first.actions[0].kind == "calendar.create"
    assert first.actions[0].strategy == "intent_prefill"
    assert first.actions[0].payload["beginTime"] == POC_15_BEGIN
    assert first.actions[0].inverse.kind == "calendar.delete"
    reminder = next(action for action in first.actions if action.kind == "reminder.create")
    assert reminder.inverse.kind == "calendar.delete"
    note = next(action for action in first.actions if action.kind == "note.create")
    assert note.strategy == "panel"

    second = build_plan(snapshot, Capabilities(calendar_insert=True), Applied(event_begin=POC_15_BEGIN, reminder=True, note_text=note.payload["text"]))
    assert second is not None
    assert second.actions[0].kind == "calendar.update"
    assert second.actions[0].payload["match"]["beginTime"] == POC_15_BEGIN


def test_gui_strategy_when_insert_is_unavailable() -> None:
    snapshot = _snapshot([FULL])
    plan = build_plan(snapshot, Capabilities(calendar_insert=False), Applied())
    assert plan is not None
    assert plan.actions[0].strategy == "gui"


def test_correction_plan_targets_the_new_time() -> None:
    snapshot = _snapshot([FULL, "Ah non, plutôt 16h."])
    plan = build_plan(snapshot, Capabilities(), Applied(event_begin=POC_15_BEGIN, reminder=True))
    assert plan is not None
    update = plan.actions[0]
    assert update.kind == "calendar.update"
    assert update.payload["beginTime"] == POC_16_BEGIN
    assert update.payload["match"]["beginTime"] == POC_15_BEGIN


def test_confirm_is_idempotent_and_undo_once() -> None:
    snapshot = _snapshot([FULL, "Ah non, plutôt 16h."])
    card = build_card(snapshot)
    assert [item.label for item in card.items] == ["日历", "提醒", "便签"]
    assert "16:00" in card.items[0].summary
    ledger = Ledger()
    assert ledger.handle(snapshot, "confirm") is None
    assert ledger.handle(snapshot, "confirm") is None
    undo = ledger.handle(snapshot, "undo_reminder")
    assert undo is not None
    assert undo.kind == "calendar.delete"
    assert ledger.handle(snapshot, "undo_reminder") is None


def test_verify_match_mismatch_empty_and_multihit() -> None:
    snapshot = _snapshot([FULL])
    plan = build_plan(snapshot, Capabilities(), Applied())
    assert plan is not None
    action = plan.actions[0]
    hit = CalendarRow(title="POC", dtstart=POC_15_BEGIN, dtend=POC_15_BEGIN + 3600_000, eventLocation="Station F")
    assert verify_action(action, [hit], "t", "call_demo").matched
    late = CalendarRow(title="POC", dtstart=POC_15_BEGIN + 3600_000, dtend=0, eventLocation="Station F")
    assert not verify_action(action, [late], "t", "call_demo").matched
    assert not verify_action(action, [], "t", "call_demo").matched
    other = CalendarRow(title="Other", dtstart=1, dtend=2, eventLocation="")
    assert verify_action(action, [other, hit], "t", "call_demo").matched


def test_content_query_parser_reads_recorded_rows() -> None:
    sample = "\n".join(
        [
            "Row: 0 _id=1, title=POC, dtstart=1794319200000, dtend=1794322800000, eventLocation=Station F",
            "No result found.",
        ]
    )
    rows = parse_content_query(sample)
    assert len(rows) == 1
    assert rows[0].title == "POC"
    assert rows[0].eventLocation == "Station F"
