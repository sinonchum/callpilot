"""One-command mock demo. No phone and no API keys."""

from __future__ import annotations

import json
from pathlib import Path

from executor.fake import FakeExecutor
from gui.holo import holo_from_env
from intent.extract import extractor_from_env
from orchestrator.pipeline import RunResult, run_call
from stt.mock import MockGladiaStream
from stt.pcm import encode_frame

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "demo_script.jsonl"
ENDED = {
    "v": 1,
    "type": "call.ended",
    "ts": "2026-11-08T09:01:00+01:00",
    "call_id": "call_demo",
    "reason": "hangup",
}


def load_jsonl(path: Path = FIXTURE) -> list[dict]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            lines.append(json.loads(line))
    return lines


def run_demo() -> RunResult:
    raw = load_jsonl()
    started = [event for event in raw if event["type"] == "call.started"]
    frame = encode_frame(
        {
            "v": 1,
            "type": "audio.frame",
            "call_id": "call_demo",
            "seq": 1,
            "ts_mono_ms": 0,
            "sample_rate": 16000,
            "channels": 1,
            "encoding": "pcm_s16le",
            "capture": "voice_call",
        },
        b"\x00\x00" * 160,
    )
    heard = MockGladiaStream(raw).transcribe([frame])
    return run_call(
        started + heard + [ENDED],
        auto_undo=True,
        extractor=extractor_from_env(),
        executor=FakeExecutor(),
        holo=holo_from_env(),
    )


def main() -> int:
    result = run_demo()
    for line in result.log:
        print(line)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
