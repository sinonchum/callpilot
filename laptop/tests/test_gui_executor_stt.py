import json
import threading
from urllib.request import Request, urlopen

import pytest

from contracts.models import Action, ExecRequest, Inverse
from executor.adb import AdbExecutor, AdbNotEnabled
from executor.fake import SCREEN_H, SCREEN_W, FakeExecutor
from executor.server import serve
from gui.coords import to_pixel
from gui.holo import MissingSaveHolo, ScriptedHolo, build_holo_request, holo_from_env, trim_images
from gui.loop import run_gui
from gui.tools import HOLO_TOOLS
from intent.extract import build_intent_request, extractor_from_env, parse_patch_content
from stt.gladia import gladia_from_env, init_payload
from stt.mock import MockGladiaStream
from stt.pcm import decode_frame, encode_frame


def test_coordinate_scale_matches_holo_docs() -> None:
    assert to_pixel(932, 880, 1440, 900) == (1342, 792)
    assert to_pixel(500, 500, 100, 200) == (50, 100)


def test_fake_save_tap_writes_one_row_per_title() -> None:
    executor = FakeExecutor()
    executor.execute(
        ExecRequest(
            id="open",
            op="am_start",
            extras={"title": "POC", "beginTime": 15, "endTime": 16, "eventLocation": "Station F"},
        )
    )
    missed = executor.execute(ExecRequest(id="miss", op="tap", x=0, y=0))
    assert missed.ok
    assert executor.rows == []
    px, py = to_pixel(900, 100, SCREEN_W, SCREEN_H)
    executor.execute(ExecRequest(id="save", op="tap", x=px, y=py))
    assert len(executor.rows) == 1
    executor.execute(
        ExecRequest(
            id="open2",
            op="am_start",
            extras={"title": "POC", "beginTime": 16, "endTime": 17, "eventLocation": "Station F"},
        )
    )
    executor.execute(ExecRequest(id="save2", op="tap", x=px, y=py))
    assert [row.dtstart for row in executor.rows] == [16]


def test_scripted_loop_clicks_save_in_pixels() -> None:
    action = Action(
        action_id="act_evt",
        kind="calendar.create",
        strategy="intent_prefill",
        payload={"title": "POC"},
        inverse=Inverse(kind="calendar.delete"),
    )
    executor = FakeExecutor()
    steps, finished = run_gui(
        action,
        executor,
        ScriptedHolo(
            [
                {"tool": "click", "args": {"element": "the Save button", "x": 900, "y": 100}},
                {"tool": "answer", "args": {"content": "Saved."}},
            ]
        ),
        ts="t",
        call_id="c",
    )
    assert finished.ok
    assert finished.stop == "answer"
    assert steps[0]["pixel"] == {"x": 90, "y": 20}
    assert steps[0]["screenshot_width"] == 100


def test_step_budget() -> None:
    action = Action(
        action_id="act",
        kind="calendar.create",
        strategy="gui",
        payload={},
        inverse=Inverse(kind="calendar.delete"),
    )
    script = [{"tool": "click", "args": {"element": "x", "x": 0, "y": 0}} for _ in range(20)]
    _steps, finished = run_gui(action, FakeExecutor(), ScriptedHolo(script), ts="t", call_id="c", max_steps=8)
    assert finished.stop == "step_budget"
    assert finished.ok is False


def test_holo_request_shape() -> None:
    payload = build_holo_request("holo4-35b-a3b", "Save the event", "aaaa")
    assert payload["tool_choice"] == "required"
    assert payload["temperature"] == 0.8
    assert payload["chat_template_kwargs"]["enable_thinking"] is True
    names = [tool["function"]["name"] for tool in payload["tools"]]
    assert names == [tool["function"]["name"] for tool in HOLO_TOOLS]
    chunks = payload["messages"][-1]["content"]
    assert chunks[0]["text"].startswith("<observation>")
    assert chunks[1]["image_url"]["url"] == "data:image/png;base64,aaaa"


def test_image_budget_keeps_three_screenshots() -> None:
    messages = []
    for index in range(5):
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{index}"}},
                ],
            }
        )
    trim_images(messages, 3)
    kept = [
        chunk["image_url"]["url"]
        for message in messages
        for chunk in message["content"]
        if chunk.get("type") == "image_url"
    ]
    assert kept == [
        "data:image/png;base64,2",
        "data:image/png;base64,3",
        "data:image/png;base64,4",
    ]
    assert messages[0]["content"][0]["text"] == "[screenshot evicted]"


def test_adb_commands_do_not_run() -> None:
    executor = AdbExecutor(serial="ABC")
    tap = executor.build(ExecRequest(id="1", op="tap", x=10, y=20))
    assert tap == ["adb", "-s", "ABC", "shell", "su", "-c", "input tap 10 20"]
    insert = executor.build(
        ExecRequest(
            id="2",
            op="am_start",
            action="android.intent.action.INSERT",
            data="content://com.android.calendar/events",
            extras={"title": "POC", "eventLocation": "Station F", "beginTime": 1794322800000},
        )
    )
    assert "Station F" in insert
    assert insert[insert.index("Station F") - 1] == "eventLocation"
    assert "--el" in insert
    with pytest.raises(AdbNotEnabled):
        executor.execute(ExecRequest(id="3", op="screencap"))


def test_pcm_roundtrip_and_mock_stream() -> None:
    header = {"v": 1, "type": "audio.frame", "seq": 1, "sample_rate": 16000, "channels": 1, "encoding": "pcm_s16le"}
    blob = encode_frame(header, b"\x01\x02")
    decoded, pcm = decode_frame(blob)
    assert decoded["seq"] == 1
    assert pcm == b"\x01\x02"
    events = [{"type": "transcript.final", "text": "15h"}, {"type": "call.started"}]
    heard = MockGladiaStream(events).transcribe([blob])
    assert heard == [{"type": "transcript.final", "text": "15h"}]


def test_gladia_init_payload() -> None:
    payload = init_payload(channels=2)
    assert payload["model"] == "solaria-1"
    assert payload["channels"] == 2
    assert payload["language_config"]["code_switching"] is True
    assert payload["language_config"]["languages"] == ["fr", "en"]


def test_env_falls_back_to_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HAI_API_KEY", raising=False)
    monkeypatch.delenv("GLADIA_API_KEY", raising=False)
    monkeypatch.delenv("INTENT_API_KEY", raising=False)
    monkeypatch.delenv("CALLPILOT_FORCE_MOCK", raising=False)
    assert isinstance(holo_from_env(), ScriptedHolo)
    assert gladia_from_env() is None
    assert extractor_from_env().__class__.__name__ == "RuleExtractor"
    monkeypatch.setenv("HAI_API_KEY", "secret")
    monkeypatch.setenv("CALLPILOT_FORCE_MOCK", "1")
    assert isinstance(holo_from_env(), ScriptedHolo)


def test_intent_payload_and_parser() -> None:
    payload = build_intent_request("demo-model", "à 16h", "2026-11-08T09:00:00+01:00", {})
    assert payload["model"] == "demo-model"
    assert "à 16h" in payload["messages"][1]["content"]
    event = {"ts": "t", "call_id": "c", "utterance_id": "u"}
    patch = parse_patch_content(
        json.dumps({"ops": [{"op": "upsert", "entity": "event", "id": "evt_1", "fields": {"time": "16:00"}}]}),
        event,
    )
    assert patch.ops[0].fields["time"] == "16:00"


def test_executor_http_roundtrip() -> None:
    executor = FakeExecutor()
    server = serve(executor, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        body = json.dumps({"v": 1, "id": "cap", "op": "screencap"}).encode()
        request = Request(f"http://127.0.0.1:{port}/execute", data=body, method="POST")
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode())
        assert payload["ok"] is True
        assert payload["width"] == SCREEN_W
        assert payload["height"] == SCREEN_H
    finally:
        server.shutdown()
