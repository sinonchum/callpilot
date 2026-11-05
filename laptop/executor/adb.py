"""Command builder for a rooted phone.

`execute` shells out only when CALLPILOT_EXECUTOR=adb. The mock demo never
sets that. Updating an existing event on a real device is not done here:
INSERT opens a form, and the GUI loop is expected to tap Save. The fake
executor collapses that into one row per title.
"""

from __future__ import annotations

import os
import subprocess

from contracts.models import CALENDAR_URI, ExecRequest, ExecResult


class AdbNotEnabled(RuntimeError):
    pass


class AdbExecutor:
    def __init__(self, serial: str | None = None) -> None:
        self.serial = serial if serial is not None else os.getenv("ANDROID_SERIAL", "")

    def build(self, request: ExecRequest | dict) -> list[str]:
        req = request if isinstance(request, ExecRequest) else ExecRequest.model_validate(request)
        prefix = ["adb"]
        if self.serial:
            prefix += ["-s", self.serial]
        if req.op == "tap":
            return prefix + ["shell", "su", "-c", f"input tap {req.x} {req.y}"]
        if req.op == "swipe":
            duration = req.duration_ms or 300
            return prefix + [
                "shell",
                "su",
                "-c",
                f"input swipe {req.x1} {req.y1} {req.x2} {req.y2} {duration}",
            ]
        if req.op == "text":
            return prefix + ["shell", "su", "-c", f"input text {req.text or ''}"]
        if req.op == "keyevent":
            return prefix + ["shell", "su", "-c", f"input keyevent {req.keycode or 0}"]
        if req.op == "screencap":
            return prefix + ["exec-out", "screencap", "-p"]
        if req.op == "am_start":
            command = prefix + [
                "shell",
                "am",
                "start",
                "-a",
                req.action or "android.intent.action.INSERT",
                "-d",
                req.data or CALENDAR_URI,
            ]
            for key, value in (req.extras or {}).items():
                if isinstance(value, bool):
                    continue
                flag = "--el" if isinstance(value, int) else "--es"
                command += [flag, str(key), str(value)]
            return command
        if req.op == "content_query":
            return prefix + [
                "shell",
                "content",
                "query",
                "--uri",
                req.uri or CALENDAR_URI,
                "--projection",
                req.projection or "_id:title:dtstart:dtend:eventLocation",
            ]
        if req.op == "content_delete":
            where = f"title='{req.title}' AND dtstart={req.dtstart}"
            return prefix + [
                "shell",
                "content",
                "delete",
                "--uri",
                req.uri or CALENDAR_URI,
                "--where",
                where,
            ]
        if req.op == "wait":
            return prefix + ["shell", "sleep", str((req.wait_ms or 0) / 1000)]
        raise ValueError(f"cannot build adb command for {req.op}")

    def execute(self, request: ExecRequest | dict) -> ExecResult:
        if os.getenv("CALLPILOT_EXECUTOR") != "adb":
            raise AdbNotEnabled(
                "Refusing to touch a device. Set CALLPILOT_EXECUTOR=adb after the phone is plugged in. "
                "The default demo uses FakeExecutor."
            )
        req = request if isinstance(request, ExecRequest) else ExecRequest.model_validate(request)
        command = self.build(req)
        completed = subprocess.run(command, check=False, capture_output=True)
        stdout = completed.stdout.decode(errors="replace")
        ok = completed.returncode == 0
        return ExecResult(
            id=req.id,
            ok=ok,
            stdout=stdout,
            error=None if ok else completed.stderr.decode(errors="replace"),
            latency_ms=0,
        )
