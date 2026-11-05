"""Screenshot, tool call, pixel tap. Stops on answer or the step budget."""

from __future__ import annotations

from contracts.dump import dump
from contracts.models import Action, ActionFinished, AgentStep, ExecRequest, ExecResult
from executor.fake import SCREEN_H, SCREEN_W, FakeExecutor
from gui.coords import to_pixel
from gui.holo import HoloClient, ToolCall


def run_gui(
    action: Action,
    executor: FakeExecutor,
    holo: HoloClient,
    *,
    ts: str,
    call_id: str,
    max_steps: int = 8,
) -> tuple[list[dict], ActionFinished]:
    steps: list[dict] = []
    for index in range(max_steps):
        shot = executor.execute(ExecRequest(id=f"{action.action_id}-shot-{index}", op="screencap"))
        if not shot.ok:
            finished = _finish(action, ts, call_id, ok=False, stop="executor_error", count=len(steps))
            return steps, finished
        call = holo.act(index, action, shot)
        step, follow = _dispatch(action, executor, call, shot, index, ts, call_id)
        steps.append(step)
        if follow is not None and not follow.ok:
            finished = _finish(action, ts, call_id, ok=False, stop="executor_error", count=len(steps))
            return steps, finished
        if call.name == "answer":
            content = str(call.arguments.get("content") or "")
            finished = _finish(
                action,
                ts,
                call_id,
                ok=True,
                stop="answer",
                count=len(steps),
                answer=content,
            )
            return steps, finished
    finished = _finish(action, ts, call_id, ok=False, stop="step_budget", count=len(steps))
    return steps, finished


def _dispatch(
    action: Action,
    executor: FakeExecutor,
    call: ToolCall,
    shot: ExecResult,
    index: int,
    ts: str,
    call_id: str,
) -> tuple[dict, ExecResult | None]:
    pixel = None
    follow: ExecResult | None = None
    error = None
    ok = True
    try:
        if call.name == "click":
            x = int(call.arguments["x"])
            y = int(call.arguments["y"])
            px, py = to_pixel(x, y, shot.width or SCREEN_W, shot.height or SCREEN_H)
            pixel = {"x": px, "y": py}
            follow = executor.execute(ExecRequest(id=f"{action.action_id}-tap-{index}", op="tap", x=px, y=py))
            ok = follow.ok
        elif call.name == "swipe":
            x1, y1 = to_pixel(int(call.arguments["x1"]), int(call.arguments["y1"]), shot.width, shot.height)
            x2, y2 = to_pixel(int(call.arguments["x2"]), int(call.arguments["y2"]), shot.width, shot.height)
            follow = executor.execute(
                ExecRequest(
                    id=f"{action.action_id}-swipe-{index}",
                    op="swipe",
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    duration_ms=300,
                )
            )
            ok = follow.ok
        elif call.name == "type":
            follow = executor.execute(
                ExecRequest(id=f"{action.action_id}-type-{index}", op="text", text=str(call.arguments.get("text") or ""))
            )
            ok = follow.ok
        elif call.name != "answer":
            ok = False
            error = f"unknown tool {call.name}"
    except (KeyError, TypeError, ValueError) as exc:
        ok = False
        error = str(exc)
    event = AgentStep(
        ts=ts,
        call_id=call_id,
        action_id=action.action_id,
        step_index=index,
        model=call.model,
        tool=call.name,
        args=call.arguments,
        pixel=pixel,
        screenshot_width=shot.width,
        screenshot_height=shot.height,
        ok=ok,
        latency_ms=shot.latency_ms,
        error=error,
    )
    return dump(event), follow


def _finish(
    action: Action,
    ts: str,
    call_id: str,
    *,
    ok: bool,
    stop: str,
    count: int,
    answer: str = "",
) -> ActionFinished:
    return ActionFinished(
        ts=ts,
        call_id=call_id,
        action_id=action.action_id,
        ok=ok,
        stop=stop,  # type: ignore[arg-type]
        steps=count,
        answer=answer,
    )
