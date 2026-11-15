"""Meaningful image motion from anonymous track centres. Not posture."""

from __future__ import annotations

from datetime import datetime
from math import hypot
from typing import Literal

Movement = Literal["unknown", "stationary", "moving"]

MIN_POINTS = 3
MIN_ELAPSED_S = 2.0
MOVE_SPEED = 0.18
MOVE_DISPLACEMENT = 0.25
SETTLE_SPEED = 0.08

CenterPoint = tuple[datetime, float, float]


def classify_movement(
    history: list[CenterPoint],
    previous: Movement | None = None,
) -> Movement:
    """Return whether the tracked centre moved across the recent window.

    ``unknown`` means the history is too short. ``stationary`` is not a posture.
    """

    window = _recent_window(history)
    if window is None:
        return "unknown"
    started, ended = window[0], window[-1]
    elapsed = (ended[0] - started[0]).total_seconds()
    if elapsed <= 0:
        return "unknown"
    net = hypot(ended[1] - started[1], ended[2] - started[2])
    speed = net / elapsed
    if speed >= MOVE_SPEED and net >= MOVE_DISPLACEMENT:
        return "moving"
    if speed <= SETTLE_SPEED:
        return "stationary"
    if previous in ("stationary", "moving"):
        return previous
    return "stationary"


def _recent_window(history: list[CenterPoint]) -> list[CenterPoint] | None:
    if len(history) < MIN_POINTS:
        return None
    last = history[-1][0]
    for index in range(len(history) - MIN_POINTS, -1, -1):
        window = history[index:]
        if (last - window[0][0]).total_seconds() >= MIN_ELAPSED_S:
            return window
    return None
