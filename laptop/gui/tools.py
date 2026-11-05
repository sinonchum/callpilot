"""Tool schema registered with Holo. click and answer match the public examples."""

from __future__ import annotations

HOLO_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at normalized coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "element": {"type": "string"},
                    "x": {"type": "integer", "minimum": 0, "maximum": 1000},
                    "y": {"type": "integer", "minimum": 0, "maximum": 1000},
                },
                "required": ["element", "x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "swipe",
            "description": "Swipe between normalized coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "integer", "minimum": 0, "maximum": 1000},
                    "y1": {"type": "integer", "minimum": 0, "maximum": 1000},
                    "x2": {"type": "integer", "minimum": 0, "maximum": 1000},
                    "y2": {"type": "integer", "minimum": 0, "maximum": 1000},
                },
                "required": ["x1", "y1", "x2", "y2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type",
            "description": "Type ASCII text into the focused field",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer",
            "description": "Finish the task",
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You operate an Android phone by calling tools. "
    "Coordinates are integers from 0 to 1000 on the screenshot inside <observation>. "
    "Call answer when the task is done."
)
