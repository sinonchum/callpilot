"""Length-prefixed PCM frames from the phone stub."""

from __future__ import annotations

import json
import struct


def encode_frame(header: dict, pcm: bytes) -> bytes:
    encoded = json.dumps(header, separators=(",", ":")).encode()
    return struct.pack(">I", len(encoded)) + encoded + struct.pack(">I", len(pcm)) + pcm


def decode_frame(blob: bytes) -> tuple[dict, bytes]:
    if len(blob) < 8:
        raise ValueError("pcm frame is too short")
    header_len = struct.unpack(">I", blob[:4])[0]
    start = 4
    header = json.loads(blob[start : start + header_len])
    pcm_len_at = start + header_len
    pcm_len = struct.unpack(">I", blob[pcm_len_at : pcm_len_at + 4])[0]
    pcm_start = pcm_len_at + 4
    pcm = blob[pcm_start : pcm_start + pcm_len]
    if len(pcm) != pcm_len:
        raise ValueError("pcm frame truncated")
    return header, pcm
