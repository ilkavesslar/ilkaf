"""Camera-scoped anonymous tracking with configurable thresholds and track status.

Uses the geometry and default thresholds of ``cv.tracking.PersonTracker``.
``PersonTracker`` reads module-level constants, so the association loop is
repeated here with a ``TrackerConfig`` instead of patching those globals.
Track ids are never reused for the life of one tracker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from cv import tracking as base_tracking
from cv.intelligence.contract import TrackingStatus
from cv.observation import BoundingBox, Observation

CenterPoint = tuple[datetime, float, float]


@dataclass(frozen=True, slots=True)
class TrackerConfig:
    center_distance_max: float = base_tracking.CENTER_DISTANCE_MAX
    overlap_iou_min: float = base_tracking.OVERLAP_IOU_MIN
    overlap_distance_max: float = base_tracking.OVERLAP_DISTANCE_MAX
    missed_limit: int = base_tracking.MISSED_INFERENCE_LIMIT
    min_hits: int = 2
    max_lost_s: float = 2.0
    history_limit: int = 64
    history_window_s: float = 6.0

    def __post_init__(self) -> None:
        for name in ("center_distance_max", "overlap_distance_max"):
            if not 0.0 < getattr(self, name) <= 2.0:
                raise ValueError(f"{name} must be in (0, 2]")
        if not 0.0 <= self.overlap_iou_min <= 1.0:
            raise ValueError("overlap_iou_min must be in [0, 1]")
        if self.missed_limit < 1:
            raise ValueError("missed_limit must be >= 1")
        if self.min_hits < 1:
            raise ValueError("min_hits must be >= 1")
        if self.max_lost_s <= 0.0:
            raise ValueError("max_lost_s must be > 0")
        if self.history_limit < 2:
            raise ValueError("history_limit must be >= 2")
        if self.history_window_s <= 0.0:
            raise ValueError("history_window_s must be > 0")


@dataclass
class TrackState:
    """One anonymous person within one camera. Not identity."""

    local_track_id: str
    number: int
    observation: Observation
    first_seen: datetime
    last_seen: datetime
    status: TrackingStatus
    hits: int = 1
    missed: int = 0
    matched_this_update: bool = True
    center_history: list[CenterPoint] = field(default_factory=list)

    @property
    def bbox(self) -> BoundingBox:
        return self.observation.bounding_box


@dataclass(frozen=True, slots=True)
class TrackerUpdate:
    tracks: list[TrackState]
    removed: list[str]


class CameraScopedTracker:
    """Associate person observations into ``{camera_id}:t{n}`` tracks."""

    def __init__(self, camera_id: str, config: TrackerConfig | None = None) -> None:
        stripped = camera_id.strip()
        if not stripped:
            raise ValueError("camera_id is required")
        self.camera_id = stripped
        self.config = config or TrackerConfig()
        self._tracks: list[TrackState] = []
        self._next_number = 1
        self._last_update: datetime | None = None

    @property
    def tracks(self) -> list[TrackState]:
        return list(self._tracks)

    def update(self, observations: list[Observation], when: datetime) -> TrackerUpdate:
        """Apply one inference result at ``when``. ``[]`` ages tracks.

        Timestamps must not go backwards. Tracks unseen for longer than
        ``max_lost_s`` are dropped even if fewer than ``missed_limit`` updates ran.
        """

        if when.tzinfo is None:
            raise ValueError("when must be timezone-aware (UTC)")
        if self._last_update is not None and when < self._last_update:
            raise ValueError("tracker timestamps must not go backwards")
        self._last_update = when
        for observation in observations:
            if observation.camera_id is not None and observation.camera_id != self.camera_id:
                raise ValueError("observation camera_id does not match tracker camera_id")

        removed: list[str] = []
        fresh: list[TrackState] = []
        for track in self._tracks:
            if (when - track.last_seen).total_seconds() > self.config.max_lost_s:
                removed.append(track.local_track_id)
            else:
                fresh.append(track)
        self._tracks = fresh

        pairs = self._match(observations)
        matched_tracks = {track_index for track_index, _ in pairs}
        matched_observations = {observation_index for _, observation_index in pairs}
        for track_index, observation_index in pairs:
            self._apply(self._tracks[track_index], observations[observation_index], when)

        surviving: list[TrackState] = []
        for index, track in enumerate(self._tracks):
            if index in matched_tracks:
                surviving.append(track)
                continue
            track.matched_this_update = False
            track.missed += 1
            if track.status == "tentative" or track.missed >= self.config.missed_limit:
                removed.append(track.local_track_id)
                continue
            track.status = "lost"
            surviving.append(track)
        self._tracks = surviving

        for index, observation in enumerate(observations):
            if index not in matched_observations:
                self._tracks.append(self._create(observation, when))
        ordered = sorted(self._tracks, key=lambda item: item.number)
        return TrackerUpdate(tracks=ordered, removed=removed)

    def _create(self, observation: Observation, when: datetime) -> TrackState:
        number = self._next_number
        self._next_number += 1
        center = base_tracking._center(observation.bounding_box)
        return TrackState(
            local_track_id=f"{self.camera_id}:t{number}",
            number=number,
            observation=observation,
            first_seen=when,
            last_seen=when,
            status="active" if self.config.min_hits <= 1 else "tentative",
            center_history=[(when, center[0], center[1])],
        )

    def _apply(self, track: TrackState, observation: Observation, when: datetime) -> None:
        center = base_tracking._center(observation.bounding_box)
        track.observation = observation
        track.last_seen = when
        track.missed = 0
        track.hits += 1
        track.matched_this_update = True
        if track.status == "lost" or track.hits >= self.config.min_hits:
            track.status = "active"
        history = track.center_history
        history.append((when, center[0], center[1]))
        cutoff = self.config.history_window_s
        while len(history) > 2 and (when - history[0][0]).total_seconds() > cutoff:
            history.pop(0)
        del history[: -self.config.history_limit]

    def _can_match(self, distance: float, iou: float) -> bool:
        config = self.config
        if distance <= config.center_distance_max:
            return True
        return iou >= config.overlap_iou_min and distance <= config.overlap_distance_max

    def _match(self, observations: list[Observation]) -> list[tuple[int, int]]:
        candidates: list[tuple[float, int, int]] = []
        for observation_index, observation in enumerate(observations):
            center = base_tracking._center(observation.bounding_box)
            for track_index, track in enumerate(self._tracks):
                last = track.center_history[-1]
                distance = base_tracking._distance(center, (last[1], last[2]))
                overlap = base_tracking._iou(observation.bounding_box, track.bbox)
                if self._can_match(distance, overlap):
                    candidates.append((distance, observation_index, track_index))
        candidates.sort()
        used_observations: set[int] = set()
        used_tracks: set[int] = set()
        pairs: list[tuple[int, int]] = []
        for _distance, observation_index, track_index in candidates:
            if observation_index in used_observations or track_index in used_tracks:
                continue
            used_observations.add(observation_index)
            used_tracks.add(track_index)
            pairs.append((track_index, observation_index))
        return pairs
