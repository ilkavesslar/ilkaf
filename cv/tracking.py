"""Anonymous in-memory person tracking. Not identity, biometrics, or incidents.

The detector stays stateless. This module associates its observations across
inference results for one stream session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import hypot

from cv.observation import BoundingBox, Observation

CENTER_DISTANCE_MAX = 0.35
OVERLAP_IOU_MIN = 0.20
OVERLAP_DISTANCE_MAX = 0.50
MISSED_INFERENCE_LIMIT = 3
CENTER_HISTORY_LIMIT = 8


def _center(box: BoundingBox) -> tuple[float, float]:
    return ((box.x_min + box.x_max) / 2, (box.y_min + box.y_max) / 2)


def _distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return hypot(left[0] - right[0], left[1] - right[1])


def _iou(left: BoundingBox, right: BoundingBox) -> float:
    overlap_w = min(left.x_max, right.x_max) - max(left.x_min, right.x_min)
    overlap_h = min(left.y_max, right.y_max) - max(left.y_min, right.y_min)
    if overlap_w <= 0 or overlap_h <= 0:
        return 0.0
    intersection = overlap_w * overlap_h
    area_left = (left.x_max - left.x_min) * (left.y_max - left.y_min)
    area_right = (right.x_max - right.x_min) * (right.y_max - right.y_min)
    union = area_left + area_right - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def _can_match(distance: float, iou: float) -> bool:
    if distance <= CENTER_DISTANCE_MAX:
        return True
    return iou >= OVERLAP_IOU_MIN and distance <= OVERLAP_DISTANCE_MAX


@dataclass
class Track:
    """One anonymous person for the life of a single tracker."""

    track_id: int
    latest_observation: Observation
    last_center: tuple[float, float]
    missed_inferences: int = 0
    center_history: list[tuple[datetime, float, float]] = field(default_factory=list)


class PersonTracker:
    """Match person observations to temporary tracks. IDs are never reused."""

    def __init__(self) -> None:
        self._tracks: list[Track] = []
        self._next_id = 1

    def update(self, observations: list[Observation], observed_at: datetime) -> list[Track]:
        """Apply one inference result. ``[]`` ages tracks. Skipped frames must not call this."""

        pairs = self._match(observations)
        matched_tracks: set[int] = set()
        matched_observations: set[int] = set()
        for track_index, observation_index in pairs:
            observation = observations[observation_index]
            center = _center(observation.bounding_box)
            track = self._tracks[track_index]
            track.latest_observation = observation
            track.last_center = center
            track.missed_inferences = 0
            track.center_history.append((observed_at, center[0], center[1]))
            del track.center_history[:-CENTER_HISTORY_LIMIT]
            matched_tracks.add(track_index)
            matched_observations.add(observation_index)

        surviving: list[Track] = []
        for index, track in enumerate(self._tracks):
            if index in matched_tracks:
                surviving.append(track)
                continue
            track.missed_inferences += 1
            if track.missed_inferences < MISSED_INFERENCE_LIMIT:
                surviving.append(track)
        self._tracks = surviving

        for index, observation in enumerate(observations):
            if index in matched_observations:
                continue
            center = _center(observation.bounding_box)
            track = Track(
                track_id=self._next_id,
                latest_observation=observation,
                last_center=center,
                missed_inferences=0,
                center_history=[(observed_at, center[0], center[1])],
            )
            self._next_id += 1
            self._tracks.append(track)
        return sorted(self._tracks, key=lambda item: item.track_id)

    def _match(self, observations: list[Observation]) -> list[tuple[int, int]]:
        candidates: list[tuple[float, int, int]] = []
        for observation_index, observation in enumerate(observations):
            center = _center(observation.bounding_box)
            for track_index, track in enumerate(self._tracks):
                distance = _distance(center, track.last_center)
                overlap = _iou(observation.bounding_box, track.latest_observation.bounding_box)
                if _can_match(distance, overlap):
                    candidates.append((distance, observation_index, track_index))
        candidates.sort()
        used_observations: set[int] = set()
        used_tracks: set[int] = set()
        pairs: list[tuple[int, int]] = []
        for _pair_distance, observation_index, track_index in candidates:
            if observation_index in used_observations or track_index in used_tracks:
                continue
            used_observations.add(observation_index)
            used_tracks.add(track_index)
            pairs.append((track_index, observation_index))
        return pairs
