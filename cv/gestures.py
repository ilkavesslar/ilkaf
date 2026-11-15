"""Anonymous wave detection from wrist positions. Not identity or biometrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise

from cv.observation import BoundingBox

WAVE_MIN_POINTS = 4
WAVE_MIN_STEP = 0.08
WAVE_MIN_SPAN = 0.18
WAVE_MIN_REVERSALS = 2
WAVE_WINDOW_S = 2.5
WAVE_HOLD_S = 1.5

Wrist = tuple[float, float]


@dataclass(frozen=True, slots=True)
class PoseCue:
    """One posed person in normalized image coordinates."""

    anchor: Wrist
    left_wrist: Wrist | None
    right_wrist: Wrist | None


def relative_x(wrist_x: float, box: BoundingBox) -> float | None:
    """Horizontal wrist position inside a person box. Walking shifts the box, not this value."""

    width = box.x_max - box.x_min
    if width <= 0.01:
        return None
    return (wrist_x - box.x_min) / width


def detect_wave(samples: list[tuple[datetime, float]], now: datetime) -> bool:
    """True when recent relative wrist positions reverse direction twice."""

    window_start = now - timedelta(seconds=WAVE_WINDOW_S)
    values = [position for moment, position in samples if moment >= window_start]
    if len(values) < WAVE_MIN_POINTS:
        return False
    if max(values) - min(values) < WAVE_MIN_SPAN:
        return False
    deltas = [right - left for left, right in pairwise(values) if abs(right - left) >= WAVE_MIN_STEP]
    if len(deltas) < 3:
        return False
    reversals = sum(1 for left, right in pairwise(deltas) if left * right < 0)
    return reversals >= WAVE_MIN_REVERSALS


def associate_cues(
    tracks: list[tuple[int, BoundingBox]],
    cues: list[PoseCue],
) -> dict[int, PoseCue]:
    """Give each pose to the tightest track box that contains its torso anchor."""

    assigned: dict[int, PoseCue] = {}
    used: set[int] = set()
    for cue in cues:
        candidates: list[tuple[float, int]] = []
        for track_id, box in tracks:
            if track_id in used or not _contains(cue.anchor, box):
                continue
            area = (box.x_max - box.x_min) * (box.y_max - box.y_min)
            candidates.append((area, track_id))
        if not candidates:
            continue
        candidates.sort()
        track_id = candidates[0][1]
        used.add(track_id)
        assigned[track_id] = cue
    return assigned


def _contains(point: Wrist, box: BoundingBox) -> bool:
    x_pos, y_pos = point
    return box.x_min <= x_pos <= box.x_max and box.y_min <= y_pos <= box.y_max


class GestureTracker:
    """Per-track wrist history. Waving clears shortly after the motion stops."""

    def __init__(self) -> None:
        self._left: dict[int, list[tuple[datetime, float]]] = {}
        self._right: dict[int, list[tuple[datetime, float]]] = {}
        self._until: dict[int, datetime] = {}

    def update(
        self,
        track_id: int,
        when: datetime,
        left_relative: float | None,
        right_relative: float | None,
    ) -> None:
        self._append(self._left, track_id, when, left_relative)
        self._append(self._right, track_id, when, right_relative)
        if detect_wave(self._left.get(track_id, []), when) or detect_wave(
            self._right.get(track_id, []), when
        ):
            self._until[track_id] = when + timedelta(seconds=WAVE_HOLD_S)

    def waving(self, track_id: int, when: datetime) -> bool:
        until = self._until.get(track_id)
        return until is not None and when <= until

    def retain(self, active_ids: set[int]) -> None:
        for store in (self._left, self._right, self._until):
            stale = [track_id for track_id in store if track_id not in active_ids]
            for track_id in stale:
                del store[track_id]

    def _append(
        self,
        store: dict[int, list[tuple[datetime, float]]],
        track_id: int,
        when: datetime,
        value: float | None,
    ) -> None:
        if value is None:
            return
        series = store.setdefault(track_id, [])
        series.append((when, value))
        cutoff = when - timedelta(seconds=WAVE_WINDOW_S)
        store[track_id] = [item for item in series if item[0] >= cutoff]
