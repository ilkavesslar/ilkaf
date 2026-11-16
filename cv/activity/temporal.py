"""Rule-based temporal activity hypotheses per anonymous track. PROVISIONAL heuristics.

Outputs are probabilistic observations, not incidents or safety conclusions.
No class is committed from a single frame: every change needs a consistent
candidate over ``min_frames`` and ``min_duration_s``. ``FALLING`` needs an
observed upright-to-down transition; ``PERSON_DOWN`` needs the down posture
sustained for ``person_down_s``. Thresholds are uncalibrated lab defaults.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from math import atan2, degrees, hypot
from typing import Literal

from cv.intelligence.contract import (
    KEYPOINT_COUNT,
    ActivityClass,
    Keypoint,
    KeypointName,
    MovementState,
)
from cv.observation import BoundingBox

RULES_VERSION = "ilka-temporal-rules-0.1.0"

Posture = Literal["upright", "bent", "sitting", "down"]
_DOWN_CLASSES = (ActivityClass.FALLING, ActivityClass.PERSON_DOWN)


@dataclass(frozen=True, slots=True)
class ActivityConfig:
    walk_speed_bh: float = 0.25
    run_speed_bh: float = 1.5
    speed_window_s: float = 1.0
    min_speed_span_s: float = 0.4
    upright_torso_deg: float = 30.0
    bending_torso_deg: float = 45.0
    lying_torso_deg: float = 65.0
    sitting_thigh_deg: float = 55.0
    upright_box_aspect: float = 0.75
    lying_box_aspect: float = 1.3
    min_keypoint_confidence: float = 0.3
    min_duration_s: float = 0.5
    min_frames: int = 3
    exit_down_s: float = 1.5
    fall_window_s: float = 1.5
    fall_min_drop_bh: float = 0.2
    fall_confirm_s: float = 0.3
    fall_confirm_frames: int = 2
    person_down_s: float = 3.0
    unknown_after_s: float = 2.0
    history_s: float = 8.0

    def __post_init__(self) -> None:
        if not 0.0 < self.walk_speed_bh < self.run_speed_bh:
            raise ValueError("require 0 < walk_speed_bh < run_speed_bh")
        if not self.upright_torso_deg <= self.bending_torso_deg < self.lying_torso_deg <= 90.0:
            raise ValueError("require upright <= bending < lying <= 90 degrees")
        if self.upright_box_aspect >= self.lying_box_aspect:
            raise ValueError("upright_box_aspect must be below lying_box_aspect")
        if self.min_frames < 2 or self.fall_confirm_frames < 2:
            raise ValueError("activity changes need at least two frames")
        for name in (
            "speed_window_s",
            "min_speed_span_s",
            "min_duration_s",
            "exit_down_s",
            "fall_window_s",
            "fall_confirm_s",
            "person_down_s",
            "unknown_after_s",
            "history_s",
        ):
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be > 0")
        if self.history_s < max(self.fall_window_s + self.person_down_s, self.speed_window_s):
            raise ValueError("history_s is too short for fall and speed windows")


@dataclass(frozen=True, slots=True)
class ActivityState:
    activity_class: ActivityClass
    confidence: float
    started_at: datetime | None
    duration_s: float | None

    @classmethod
    def unknown(cls) -> ActivityState:
        return cls(ActivityClass.UNKNOWN, 0.0, None, None)


@dataclass(frozen=True, slots=True)
class _Sample:
    when: datetime
    center: tuple[float, float]
    foot: tuple[float, float]
    height: float
    posture: Posture | None
    candidate: ActivityClass
    quality: float


@dataclass
class _TrackActivity:
    samples: list[_Sample] = field(default_factory=list)
    committed: ActivityClass = ActivityClass.UNKNOWN
    committed_since: datetime | None = None
    pending: ActivityClass | None = None
    pending_since: datetime | None = None
    pending_frames: int = 0
    down_since: datetime | None = None
    down_frames: int = 0


def _point(
    keypoints: Sequence[Keypoint], name: KeypointName, floor: float
) -> tuple[float, float] | None:
    keypoint = keypoints[name]
    if not keypoint.observed or keypoint.confidence < floor:
        return None
    if keypoint.x is None or keypoint.y is None:
        return None
    return (keypoint.x, keypoint.y)


def _mid(
    left: tuple[float, float] | None, right: tuple[float, float] | None
) -> tuple[float, float] | None:
    if left is not None and right is not None:
        return ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
    return left or right


def _angle_from_vertical(
    top: tuple[float, float], bottom: tuple[float, float], image_aspect: float
) -> float:
    dx = (top[0] - bottom[0]) * image_aspect
    dy = top[1] - bottom[1]
    return degrees(atan2(abs(dx), abs(dy)))


def _pixel_aspect(box: BoundingBox, image_aspect: float) -> float:
    return ((box.x_max - box.x_min) * image_aspect) / (box.y_max - box.y_min)


class TemporalActivityRecognizer:
    """Per-track activity with hysteresis. Call once per inference per visible track."""

    def __init__(self, config: ActivityConfig | None = None) -> None:
        self.config = config or ActivityConfig()
        self._tracks: dict[str, _TrackActivity] = {}

    def update(
        self,
        track_id: str,
        when: datetime,
        bbox: BoundingBox,
        *,
        keypoints: Sequence[Keypoint] | None = None,
        movement_state: MovementState = "unknown",
        waving: bool = False,
        image_aspect: float | None = None,
    ) -> ActivityState:
        """Add one observation and return the current committed activity.

        ``image_aspect`` is frame width / height. Without it, geometry rules are
        skipped (normalized coordinates are not square), leaving motion only.
        """

        if keypoints is not None and len(keypoints) != KEYPOINT_COUNT:
            raise ValueError(f"keypoints must contain {KEYPOINT_COUNT} entries")
        if image_aspect is not None and image_aspect <= 0.0:
            raise ValueError("image_aspect must be > 0")
        state = self._tracks.setdefault(track_id, _TrackActivity())
        if state.samples and when < state.samples[-1].when:
            raise ValueError("activity timestamps must not go backwards")

        center = ((bbox.x_min + bbox.x_max) / 2, (bbox.y_min + bbox.y_max) / 2)
        foot = (center[0], bbox.y_max)
        height = bbox.y_max - bbox.y_min
        posture, posture_quality = self._posture(keypoints, bbox, image_aspect)
        speed = self._speed(state.samples, when, foot, height, image_aspect)
        candidate, quality = self._candidate(
            posture, posture_quality, speed, movement_state, waving
        )
        state.samples.append(_Sample(when, center, foot, height, posture, candidate, quality))
        cutoff = self.config.history_s
        state.samples = [s for s in state.samples if (when - s.when).total_seconds() <= cutoff]

        self._advance(state, candidate, when)
        return self._state(state, when)

    def retain(self, active_ids: set[str]) -> None:
        for track_id in [key for key in self._tracks if key not in active_ids]:
            del self._tracks[track_id]

    def forget(self, track_id: str) -> None:
        self._tracks.pop(track_id, None)

    def _posture(
        self,
        keypoints: Sequence[Keypoint] | None,
        bbox: BoundingBox,
        image_aspect: float | None,
    ) -> tuple[Posture | None, float]:
        config = self.config
        if image_aspect is None:
            return None, 0.0
        if keypoints is not None:
            floor = config.min_keypoint_confidence
            shoulders = _mid(
                _point(keypoints, KeypointName.LEFT_SHOULDER, floor),
                _point(keypoints, KeypointName.RIGHT_SHOULDER, floor),
            )
            hips = _mid(
                _point(keypoints, KeypointName.LEFT_HIP, floor),
                _point(keypoints, KeypointName.RIGHT_HIP, floor),
            )
            if shoulders is not None and hips is not None and shoulders != hips:
                used = [kp.confidence for kp in keypoints if kp.observed and kp.confidence >= floor]
                quality = 0.5 + 0.5 * (sum(used) / len(used))
                torso = _angle_from_vertical(shoulders, hips, image_aspect)
                if torso >= config.lying_torso_deg:
                    return "down", quality
                if torso >= config.bending_torso_deg:
                    return "bent", quality
                if torso > config.upright_torso_deg:
                    return None, 0.0
                thighs = [
                    _angle_from_vertical(hip, knee, image_aspect)
                    for hip, knee in (
                        (
                            _point(keypoints, KeypointName.LEFT_HIP, floor),
                            _point(keypoints, KeypointName.LEFT_KNEE, floor),
                        ),
                        (
                            _point(keypoints, KeypointName.RIGHT_HIP, floor),
                            _point(keypoints, KeypointName.RIGHT_KNEE, floor),
                        ),
                    )
                    if hip is not None and knee is not None and hip != knee
                ]
                if thighs and sum(thighs) / len(thighs) >= config.sitting_thigh_deg:
                    return "sitting", quality
                return "upright", quality
        aspect = _pixel_aspect(bbox, image_aspect)
        if aspect >= config.lying_box_aspect:
            return "down", 0.55
        if aspect <= config.upright_box_aspect:
            return "upright", 0.55
        return None, 0.0

    def _speed(
        self,
        samples: list[_Sample],
        when: datetime,
        foot: tuple[float, float],
        height: float,
        image_aspect: float | None,
    ) -> float | None:
        """Ground-point speed in body heights per second over the recent window.

        The box bottom-centre is used so posture changes (sitting, lying down)
        are not read as locomotion. The tallest box in the window is the scale,
        so a short lying box cannot inflate speed.
        """

        if image_aspect is None:
            return None
        window = [
            s for s in samples if (when - s.when).total_seconds() <= self.config.speed_window_s
        ]
        if not window:
            return None
        start = window[0]
        span = (when - start.when).total_seconds()
        if span < self.config.min_speed_span_s:
            return None
        dx = (foot[0] - start.foot[0]) * image_aspect
        dy = foot[1] - start.foot[1]
        scale = max([s.height for s in window] + [height])
        return hypot(dx, dy) / scale / span

    def _candidate(
        self,
        posture: Posture | None,
        posture_quality: float,
        speed: float | None,
        movement_state: MovementState,
        waving: bool,
    ) -> tuple[ActivityClass, float]:
        config = self.config
        if posture == "down":
            return ActivityClass.PERSON_DOWN, posture_quality
        slow = speed is None or speed < config.walk_speed_bh
        if waving and slow:
            return ActivityClass.WAVING, 0.7
        if speed is not None and posture != "sitting":
            if speed >= config.run_speed_bh:
                return ActivityClass.RUNNING, 0.65
            if speed >= config.walk_speed_bh:
                return ActivityClass.WALKING, 0.65
        if speed is None and movement_state == "moving":
            return ActivityClass.WALKING, 0.5
        if posture == "sitting":
            return ActivityClass.SITTING, posture_quality
        if posture == "bent":
            return ActivityClass.BENDING, posture_quality
        if posture == "upright" and (speed is not None or movement_state == "stationary"):
            return ActivityClass.STANDING, posture_quality
        return ActivityClass.UNKNOWN, 0.0

    def _advance(self, state: _TrackActivity, candidate: ActivityClass, when: datetime) -> None:
        config = self.config
        is_down = candidate is ActivityClass.PERSON_DOWN
        if is_down:
            if state.down_since is None:
                state.down_since = when
                state.down_frames = 0
            state.down_frames += 1
        elif candidate is not ActivityClass.UNKNOWN and state.committed not in _DOWN_CLASSES:
            state.down_since = None
            state.down_frames = 0

        if state.committed in _DOWN_CLASSES and is_down:
            state.pending = None
            self._down_progress(state, when)
            return
        if is_down and self._fall_observed(state, when):
            self._commit(state, ActivityClass.FALLING, state.down_since or when)
            self._down_progress(state, when)
            return

        if candidate is state.committed:
            state.pending = None
            return
        if candidate is not state.pending:
            state.pending = candidate
            state.pending_since = when
            state.pending_frames = 0
        state.pending_frames += 1
        since = state.pending_since or when
        held = (when - since).total_seconds()

        if is_down:
            self._down_progress(state, when)
            return
        if candidate is ActivityClass.UNKNOWN:
            if held >= config.unknown_after_s:
                state.down_since = None
                state.down_frames = 0
                self._commit(state, ActivityClass.UNKNOWN, since)
            return
        needed = config.exit_down_s if state.committed in _DOWN_CLASSES else config.min_duration_s
        if held >= needed and state.pending_frames >= config.min_frames:
            if state.committed in _DOWN_CLASSES:
                state.down_since = None
                state.down_frames = 0
            self._commit(state, candidate, since)

    def _down_progress(self, state: _TrackActivity, when: datetime) -> None:
        since = state.down_since
        if since is None or state.committed is ActivityClass.PERSON_DOWN:
            return
        held = (when - since).total_seconds()
        if held >= self.config.person_down_s and state.down_frames >= self.config.min_frames:
            self._commit(state, ActivityClass.PERSON_DOWN, since)

    def _fall_observed(self, state: _TrackActivity, when: datetime) -> bool:
        """Upright shortly before the down run began, a real drop, and >= 2 down frames."""

        config = self.config
        since = state.down_since
        if since is None or state.committed in _DOWN_CLASSES:
            return False
        if state.down_frames < config.fall_confirm_frames:
            return False
        if (when - since).total_seconds() < config.fall_confirm_s:
            return False
        latest = state.samples[-1]
        for sample in state.samples:
            gap = (since - sample.when).total_seconds()
            if sample.posture != "upright" or gap <= 0.0 or gap > config.fall_window_s:
                continue
            drop = latest.center[1] - sample.center[1]
            if drop >= config.fall_min_drop_bh * sample.height:
                return True
        return False

    def _commit(self, state: _TrackActivity, activity: ActivityClass, since: datetime) -> None:
        state.committed = activity
        state.committed_since = since
        state.pending = None
        state.pending_since = None
        state.pending_frames = 0

    def _state(self, state: _TrackActivity, when: datetime) -> ActivityState:
        activity = state.committed
        since = state.committed_since
        if activity is ActivityClass.UNKNOWN or since is None:
            return ActivityState.unknown()
        accepted = (ActivityClass.PERSON_DOWN,) if activity in _DOWN_CLASSES else (activity,)
        window = [s for s in state.samples if s.when >= since]
        agreeing = [s for s in window if s.candidate in accepted]
        if not window or not agreeing:
            return ActivityState(activity, 0.0, since, (when - since).total_seconds())
        agreement = len(agreeing) / len(window)
        quality = sum(s.quality for s in agreeing) / len(agreeing)
        confidence = round(min(max(agreement * quality, 0.0), 1.0), 4)
        return ActivityState(activity, confidence, since, (when - since).total_seconds())
