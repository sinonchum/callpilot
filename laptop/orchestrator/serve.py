"""Replay the mock demo on ws://127.0.0.1:8765/events for the panel."""

from __future__ import annotations

import asyncio
import json

import websockets

from orchestrator.demo import run_demo


async def _main() -> None:
    result = run_demo()
    if not result.ok:
        raise SystemExit(result.reason)

    async def handler(websocket) -> None:
        for event in result.events:
            await websocket.send(json.dumps(event, ensure_ascii=False))
        await websocket.close()

    async with websockets.serve(handler, "127.0.0.1", 8765):
        print("ws://127.0.0.1:8765/events")
        await asyncio.Future()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
