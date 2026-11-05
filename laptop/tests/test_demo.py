import json
from pathlib import Path

from contracts.models import SCHEMA_MODELS
from gui.holo import MissingSaveHolo
from orchestrator.demo import FIXTURE, load_jsonl, run_demo
from orchestrator.pipeline import _perform
from executor.fake import FakeExecutor
from contracts.models import Action, Inverse, POC_16_BEGIN

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "schema" / "v1.json"
REPLAY_PATH = ROOT / "fixtures" / "panel_replay.jsonl"


def test_demo_script_fixture_matches_the_plan() -> None:
    events = load_jsonl(FIXTURE)
    assert [event["type"] for event in events] == ["call.started", "transcript.final", "transcript.final"]
    assert "15h" in events[1]["text"]
    assert "16h" in events[2]["text"]


def test_mock_demo_end_to_end() -> None:
    result = run_demo()
    assert result.ok, result.reason
    assert result.rows == [
        {
            "title": "POC",
            "dtstart": POC_16_BEGIN,
            "dtend": POC_16_BEGIN + 3_600_000,
            "eventLocation": "Station F",
        }
    ]
    kinds = [event["type"] for event in result.events]
    assert "intent.snapshot" in kinds
    assert "plan.created" in kinds
    assert "agent.step" in kinds
    assert "verify.result" in kinds
    assert "confirm.request" in kinds
    click = next(event for event in result.events if event.get("tool") == "click")
    assert click["pixel"] == {"x": 90, "y": 20}
    recorded = [json.loads(line) for line in REPLAY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert recorded == result.events


def test_calibrated_tap_saves_when_holo_misses() -> None:
    executor = FakeExecutor()
    action = Action(
        action_id="act_evt",
        kind="calendar.create",
        strategy="intent_prefill",
        payload={
            "title": "POC",
            "eventLocation": "Station F",
            "beginTime": 15,
            "endTime": 16,
            "description": "CallPilot",
        },
        inverse=Inverse(kind="calendar.delete"),
    )
    _steps, finished = _perform(action, executor, MissingSaveHolo(), "t", "call_demo")
    assert finished.ok
    assert executor.rows[0].title == "POC"
    assert executor.calls.count("tap") > 1


def test_schema_file_matches_models() -> None:
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    fresh = {name: model.model_json_schema() for name, model in SCHEMA_MODELS.items()}
    assert committed == fresh
