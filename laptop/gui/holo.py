"""Holo clients. Scripted playback is the default; the HTTP client needs HAI_API_KEY."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from contracts.models import Action, ExecResult
from gui.tools import HOLO_TOOLS, SYSTEM_PROMPT


@dataclass
class ToolCall:
    name: str
    arguments: dict
    model: str = "scripted"


class HoloClient(Protocol):
    def act(self, step_index: int, action: Action, shot: ExecResult) -> ToolCall: ...


class ScriptedHolo:
    def __init__(self, script: list[dict], model: str = "scripted") -> None:
        self.script = script
        self.model = model

    def act(self, step_index: int, action: Action, shot: ExecResult) -> ToolCall:
        del action, shot
        if step_index >= len(self.script):
            return ToolCall(name="answer", arguments={"content": "Step budget exhausted."}, model=self.model)
        item = self.script[step_index]
        return ToolCall(name=item["tool"], arguments=dict(item.get("args") or {}), model=self.model)


class MissingSaveHolo:
    """Clicks the corner, then answers. Used to exercise the calibrated-tap fallback."""

    def act(self, step_index: int, action: Action, shot: ExecResult) -> ToolCall:
        del action, shot
        if step_index == 0:
            return ToolCall(name="click", arguments={"element": "empty corner", "x": 0, "y": 0})
        return ToolCall(name="answer", arguments={"content": "I did not find Save."})


def default_save_script() -> list[dict]:
    return [
        {"tool": "click", "args": {"element": "the Save button", "x": 900, "y": 100}},
        {"tool": "answer", "args": {"content": "Saved."}},
    ]


def holo_from_env(script: list[dict] | None = None) -> HoloClient:
    if os.getenv("CALLPILOT_FORCE_MOCK") == "1" or not os.getenv("HAI_API_KEY"):
        return ScriptedHolo(script or default_save_script())
    return LiveHolo(
        api_key=os.environ["HAI_API_KEY"],
        base_url=os.getenv("CALLPILOT_HOLO_BASE_URL", "https://api.hcompany.ai/v1"),
        model=os.getenv("CALLPILOT_MODEL", "holo4-35b-a3b"),
    )


def trim_images(messages: list[dict], keep: int = 3) -> None:
    """Keep the newest screenshots. Older ones become a text placeholder."""
    seen = 0
    for message in reversed(messages):
        content = message.get("content")
        if message.get("role") != "user" or not isinstance(content, list):
            continue
        for chunk in content:
            if chunk.get("type") != "image_url":
                continue
            seen += 1
            if seen > keep:
                chunk.pop("image_url", None)
                chunk["type"] = "text"
                chunk["text"] = "[screenshot evicted]"


def build_holo_request(model: str, task: str, screenshot_b64: str, history: list[dict] | None = None) -> dict:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "<observation>\n"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
                },
                {"type": "text", "text": "\n</observation>"},
                {"type": "text", "text": task},
            ],
        }
    )
    return {
        "model": model,
        "messages": messages,
        "tools": HOLO_TOOLS,
        "tool_choice": "required",
        "temperature": 0.8,
        "chat_template_kwargs": {"enable_thinking": True},
    }


class LiveHolo:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.history: list[dict] = []

    def act(self, step_index: int, action: Action, shot: ExecResult) -> ToolCall:
        del step_index
        task = f"{action.kind}: {json.dumps(action.payload, ensure_ascii=False)}"
        self.history.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "<observation>\n"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{shot.screenshot_png_b64}"},
                    },
                    {"type": "text", "text": "\n</observation>"},
                    {"type": "text", "text": task},
                ],
            }
        )
        trim_images(self.history, 3)
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *self.history],
            "tools": HOLO_TOOLS,
            "tool_choice": "required",
            "temperature": 0.8,
            "chat_template_kwargs": {"enable_thinking": True},
        }
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode())
        message = body["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return ToolCall(name="answer", arguments={"content": message.get("content") or ""}, model=self.model)
        call = tool_calls[0]
        arguments = json.loads(call["function"]["arguments"])
        self.history.append(
            {
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": tool_calls,
            }
        )
        self.history.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": "ok",
            }
        )
        return ToolCall(name=call["function"]["name"], arguments=arguments, model=self.model)
