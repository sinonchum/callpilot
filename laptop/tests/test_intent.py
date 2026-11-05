from datetime import datetime
from zoneinfo import ZoneInfo

from contracts.models import POC_15_BEGIN, POC_16_BEGIN, DECK_BEGIN
from intent.dates import parse_ts
from intent.extract import RuleExtractor
from intent.reducer import apply_patch, apply_preview, empty_snapshot

PARIS = ZoneInfo("Europe/Paris")
SAT = datetime(2026, 11, 7, 10, 0, tzinfo=PARIS)
SUN = datetime(2026, 11, 8, 9, 0, tzinfo=PARIS)
FULL = (
    "On se voit mardi prochain à 15h à Station F pour le POC… "
    "and can you send me the deck before Thursday?"
)


def _final(text: str, utterance_id: str = "u", ts: str = "2026-11-08T09:00:08+01:00") -> dict:
    return {
        "v": 1,
        "type": "transcript.final",
        "ts": ts,
        "call_id": "call_demo",
        "utterance_id": utterance_id,
        "is_final": True,
        "text": text,
        "confidence": 0.9,
    }


def _fold(texts: list[str], started: datetime = SUN):
    snapshot = empty_snapshot("call_demo", started.isoformat())
    extractor = RuleExtractor()
    for index, text in enumerate(texts):
        event = _final(text, utterance_id=f"u{index}")
        patch = extractor.propose(snapshot, event, started)
        assert patch is not None
        snapshot = apply_patch(snapshot, patch)
    return snapshot


def test_t1_full_sentence_is_stable() -> None:
    snapshot = _fold([FULL], SAT)
    event = snapshot.event
    assert event is not None
    assert event.title == "POC"
    assert event.date == "2026-11-10"
    assert event.time == "15:00"
    assert event.location == "Station F"
    assert event.stability == "stable"
    assert event.beginTime == POC_15_BEGIN
    assert snapshot.reminder is not None
    assert snapshot.reminder.title == "Send the deck"
    assert snapshot.reminder.beginTime == DECK_BEGIN
    assert snapshot.reminder.stability == "stable"
    assert snapshot.note is not None
    assert "Station F" in snapshot.note.text
    assert snapshot.note.stability == "stable"


def test_t2_split_finals_match_t1() -> None:
    french = "On se voit mardi prochain à 15h à Station F pour le POC"
    english = "and can you send me the deck before Thursday?"
    split = _fold([french, english], SAT)
    whole = _fold([FULL], SAT)
    assert split.event is not None and whole.event is not None
    assert split.event.date == whole.event.date
    assert split.event.time == whole.event.time
    assert split.event.location == whole.event.location
    assert split.event.title == whole.event.title
    assert split.reminder is not None and whole.reminder is not None
    assert split.reminder.beginTime == whole.reminder.beginTime
    assert split.note is not None and split.note.text == whole.note.text


def test_t3_partial_does_not_stabilize() -> None:
    snapshot = empty_snapshot("call_demo", SUN.isoformat())
    preview = apply_preview(snapshot, "à 15h", SUN.isoformat())
    assert preview.preview == "à 15h"
    assert preview.revision == 0
    assert preview.event is None
    assert RuleExtractor().propose(snapshot, {**_final("à 15h"), "is_final": False, "type": "transcript.partial"}, SUN) is None


def test_t4_correction_keeps_the_same_event() -> None:
    snapshot = _fold([FULL, "Ah non, plutôt 16h."], SAT)
    event = snapshot.event
    assert event is not None
    assert event.id == "evt_1"
    assert event.time == "16:00"
    assert event.date == "2026-11-10"
    assert event.location == "Station F"
    assert event.title == "POC"
    assert event.status == "corrected"
    assert event.beginTime == POC_16_BEGIN
    assert snapshot.corrections[0].from_value == "15:00"
    assert snapshot.corrections[0].to == "16:00"


def test_t5_conflicting_times_stay_preview_until_one_remains() -> None:
    extractor = RuleExtractor()
    snapshot = empty_snapshot("call_demo", SAT.isoformat())
    conflict = _final("mardi prochain à 15h ou à 16h à Station F")
    patch = extractor.propose(snapshot, conflict, SAT)
    assert patch is not None
    snapshot = apply_patch(snapshot, patch)
    assert snapshot.event is not None
    assert snapshot.event.stability == "preview"
    follow = extractor.propose(snapshot, _final("16h", "u9"), SAT)
    assert follow is not None
    snapshot = apply_patch(snapshot, follow)
    assert snapshot.event is not None
    assert snapshot.event.time == "16:00"
    assert snapshot.event.fields["time"].stability == "stable"


def test_t6_next_tuesday_from_saturday_and_sunday() -> None:
    for started in (SAT, SUN):
        snapshot = _fold([FULL], started)
        assert snapshot.event is not None
        assert snapshot.event.date == "2026-11-10"
        assert parse_ts(started.isoformat()).date().isoformat() in {"2026-11-07", "2026-11-08"}


def test_missing_poc_defaults_title() -> None:
    snapshot = _fold(["mardi prochain à 15h"], SAT)
    assert snapshot.event is not None
    assert snapshot.event.title == "Appel"
