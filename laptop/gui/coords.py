"""Scale Holo's normalized coordinates onto the screenshot's own pixels."""


def to_pixel(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ValueError("screenshot dimensions must be positive")
    return int(x / 1000 * width), int(y / 1000 * height)
