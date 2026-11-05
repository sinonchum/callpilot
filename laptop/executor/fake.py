"""In-memory phone: a calendar provider and a save button on a fake screen."""

from __future__ import annotations

import base64

from contracts.models import CALENDAR_URI, CalendarRow, ExecRequest, ExecResult
from executor.png import png_bytes
from verify.calendar import format_rows

SCREEN_W = 100
SCREEN_H = 200
SAVE_X = 90
SAVE_Y = 20


class FakeExecutor:
    def __init__(self, save_xy: tuple[int, int] = (SAVE_X, SAVE_Y), hit_radius: int = 12) -> None:
        self.rows: list[CalendarRow] = []
        self.pending: CalendarRow | None = None
        self.save_xy = save_xy
        self.hit_radius = hit_radius
        self.calls: list[str] = []
        self._png = base64.b64encode(png_bytes(SCREEN_W, SCREEN_H)).decode()

    def execute(self, request: ExecRequest | dict) -> ExecResult:
        req = request if isinstance(request, ExecRequest) else ExecRequest.model_validate(request)
        self.calls.append(req.op)
        if req.op == "screencap":
            return self._shot(req.id, ok=True)
        if req.op == "am_start":
            self.pending = _row_from_extras(req.extras or {})
            return self._shot(req.id, ok=self.pending is not None, error=None if self.pending else "missing extras")
        if req.op == "tap":
            if req.x is None or req.y is None:
                return self._shot(req.id, ok=False, error="tap needs x,y")
            self._tap(req.x, req.y)
            return self._shot(req.id, ok=True)
        if req.op == "content_query":
            return ExecResult(id=req.id, ok=True, stdout=format_rows(self.rows), latency_ms=1)
        if req.op == "content_delete":
            title = req.title or ""
            begin = req.dtstart
            self.rows = [row for row in self.rows if not (row.title == title and row.dtstart == begin)]
            return ExecResult(id=req.id, ok=True, stdout=format_rows(self.rows), latency_ms=1)
        if req.op == "wait":
            return ExecResult(id=req.id, ok=True, latency_ms=req.wait_ms or 0)
        if req.op in {"swipe", "text", "keyevent"}:
            return self._shot(req.id, ok=True)
        return ExecResult(id=req.id, ok=False, error=f"unsupported op {req.op}")

    def _tap(self, x: int, y: int) -> None:
        if self.pending is None:
            return
        if abs(x - self.save_xy[0]) <= self.hit_radius and abs(y - self.save_xy[1]) <= self.hit_radius:
            self.rows = [row for row in self.rows if row.title != self.pending.title]
            self.rows.append(self.pending)
            self.pending = None

    def _shot(self, request_id: str, ok: bool, error: str | None = None) -> ExecResult:
        return ExecResult(
            id=request_id,
            ok=ok,
            width=SCREEN_W,
            height=SCREEN_H,
            screenshot_png_b64=self._png,
            latency_ms=1,
            error=error,
        )


def _row_from_extras(extras: dict) -> CalendarRow | None:
    title = extras.get("title")
    begin = extras.get("beginTime")
    end = extras.get("endTime")
    if title is None or begin is None:
        return None
    return CalendarRow(
        title=str(title),
        dtstart=int(begin),
        dtend=int(end) if end is not None else int(begin),
        eventLocation=str(extras.get("eventLocation") or ""),
    )


def query_request(request_id: str = "query") -> ExecRequest:
    return ExecRequest(
        id=request_id,
        op="content_query",
        uri=CALENDAR_URI,
        projection="_id:title:dtstart:dtend:eventLocation",
    )
