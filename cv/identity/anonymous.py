"""Anonymous cross-camera person continuity. Not face recognition, biometrics, or identity.

A ``GlobalAnonymousPersonId`` is an in-memory hypothesis that two local tracks
are the same unnamed person. It is built only from coarse clothing colour
histograms and camera timing/geometry; no face, gait, or biometric template is
computed or stored. When evidence is weak or ambiguous the matcher issues a
new id (``uncertain`` keeps the best candidate for review instead of merging).
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from math import hypot, sqrt
from typing import Any, Literal
from uuid import uuid4

from cv.observation import BoundingBox

MATCHER_VERSION = "ilka-anon-matcher-0.1.0"

IdentityStatus = Literal["pending", "new", "matched", "uncertain"]


@dataclass(frozen=True, slots=True)
class GlobalAnonymousPersonId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith("gp-") or len(self.value) <= 3:
            raise ValueError("global anonymous person ids start with 'gp-'")

    @classmethod
    def new(cls) -> GlobalAnonymousPersonId:
        return cls(f"gp-{uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AppearanceSignature:
    """L1-normalised per-channel colour histograms for upper and lower body halves."""

    upper: tuple[float, ...]
    lower: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.upper) != len(self.lower) or not self.upper:
            raise ValueError("upper and lower histograms must be the same non-zero length")

    def similarity(self, other: AppearanceSignature) -> float:
        """Mean Bhattacharyya coefficient of both halves, in ``[0, 1]``."""

        if len(self.upper) != len(other.upper):
            raise ValueError("appearance signatures use different bin counts")
        return (
            _bhattacharyya(self.upper, other.upper) + _bhattacharyya(self.lower, other.lower)
        ) / 2

    def blend(self, other: AppearanceSignature, weight: float) -> AppearanceSignature:
        return AppearanceSignature(
            upper=_normalize(
                [
                    (1 - weight) * a + weight * b
                    for a, b in zip(self.upper, other.upper, strict=True)
                ]
            ),
            lower=_normalize(
                [
                    (1 - weight) * a + weight * b
                    for a, b in zip(self.lower, other.lower, strict=True)
                ]
            ),
        )


def _bhattacharyya(left: Sequence[float], right: Sequence[float]) -> float:
    channels = 3
    per = len(left) // channels
    total = 0.0
    for channel in range(channels):
        start = channel * per
        total += sum(
            sqrt(a * b)
            for a, b in zip(left[start : start + per], right[start : start + per], strict=True)
        )
    return min(max(total / channels, 0.0), 1.0)


def _normalize(values: Sequence[float]) -> tuple[float, ...]:
    channels = 3
    per = len(values) // channels
    out: list[float] = []
    for channel in range(channels):
        chunk = values[channel * per : (channel + 1) * per]
        total = sum(chunk)
        out.extend(value / total if total > 0 else 0.0 for value in chunk)
    return tuple(out)


def _image_size(image: Any) -> tuple[int, int] | None:
    shape = getattr(image, "shape", None)
    if shape is not None and len(shape) >= 2:
        return int(shape[0]), int(shape[1])
    if isinstance(image, Sequence) and image and isinstance(image[0], Sequence):
        return len(image), len(image[0])
    return None


def appearance_histogram(
    image: Any,
    bbox: BoundingBox,
    *,
    bins: int = 8,
    max_samples: int = 1024,
    min_samples_per_half: int = 16,
) -> AppearanceSignature | None:
    """Colour histogram of a person box from a BGR HWC image, or ``None``.

    Samples at most ``max_samples`` pixels on a grid so cost stays bounded on
    CPU. Works on NumPy arrays or nested lists; no NumPy import is required.
    """

    if bins < 2 or 256 % bins:
        raise ValueError("bins must divide 256 and be >= 2")
    size = _image_size(image)
    if size is None:
        return None
    height, width = size
    x0, x1 = int(bbox.x_min * width), min(int(bbox.x_max * width), width)
    y0, y1 = int(bbox.y_min * height), min(int(bbox.y_max * height), height)
    if x1 - x0 < 2 or y1 - y0 < 4:
        return None
    area = (x1 - x0) * (y1 - y0)
    step = max(1, int(sqrt(area / max_samples)))
    middle = (y0 + y1) // 2
    width_per_bin = 256 // bins
    halves = ([0.0] * (3 * bins), [0.0] * (3 * bins))
    counts = [0, 0]
    try:
        for y_pos in range(y0, y1, step):
            row = image[y_pos]
            half = 0 if y_pos < middle else 1
            for x_pos in range(x0, x1, step):
                pixel = row[x_pos]
                for channel in range(3):
                    value = int(pixel[channel])
                    if not 0 <= value <= 255:
                        return None
                    halves[half][channel * bins + value // width_per_bin] += 1.0
                counts[half] += 1
    except (IndexError, TypeError, ValueError):
        return None
    if min(counts) < min_samples_per_half:
        return None
    return AppearanceSignature(upper=_normalize(halves[0]), lower=_normalize(halves[1]))


@dataclass(frozen=True, slots=True)
class CameraTransition:
    min_s: float
    max_s: float

    def __post_init__(self) -> None:
        if self.min_s < 0 or self.max_s <= self.min_s:
            raise ValueError("require 0 <= min_s < max_s")


class CameraTopology:
    """Known walkable transitions between cameras. Unknown pairs are implausible."""

    def __init__(
        self,
        transitions: Mapping[tuple[str, str], CameraTransition] | None = None,
        *,
        symmetric: bool = True,
    ) -> None:
        self._transitions: dict[tuple[str, str], CameraTransition] = {}
        for (source, target), transition in (transitions or {}).items():
            self._transitions[(source, target)] = transition
            if symmetric:
                self._transitions.setdefault((target, source), transition)

    def plausibility(self, source: str, target: str, gap_s: float) -> float:
        transition = self._transitions.get((source, target))
        if transition is None or gap_s < transition.min_s or gap_s > transition.max_s:
            return 0.0
        span = transition.max_s - transition.min_s
        return 1.0 - 0.5 * ((gap_s - transition.min_s) / span)


@dataclass(frozen=True, slots=True)
class MatcherConfig:
    match_threshold: float = 0.80
    uncertain_threshold: float = 0.60
    min_margin: float = 0.08
    appearance_weight: float = 0.75
    min_appearance_samples: int = 2
    appearance_ema: float = 0.3
    same_camera_reentry_s: float = 10.0
    same_camera_max_distance: float = 0.35
    retention_s: float = 300.0

    def __post_init__(self) -> None:
        if not 0.0 < self.uncertain_threshold < self.match_threshold <= 1.0:
            raise ValueError("require 0 < uncertain_threshold < match_threshold <= 1")
        if not 0.5 <= self.appearance_weight <= 1.0:
            raise ValueError("appearance_weight must be in [0.5, 1.0]")
        if (1.0 - self.appearance_weight) >= self.uncertain_threshold:
            raise ValueError("timing alone must never reach uncertain_threshold")
        if not 0.0 < self.appearance_ema <= 1.0:
            raise ValueError("appearance_ema must be in (0, 1]")
        if self.min_appearance_samples < 1:
            raise ValueError("min_appearance_samples must be >= 1")


@dataclass(frozen=True, slots=True)
class IdentityAssignment:
    global_person_id: GlobalAnonymousPersonId | None
    status: IdentityStatus
    similarity: float | None = None
    candidate_id: GlobalAnonymousPersonId | None = None


@dataclass
class _LocalTrack:
    camera_id: str
    local_track_id: str
    first_seen: datetime
    last_seen: datetime
    last_center: tuple[float, float]
    first_center: tuple[float, float]
    appearance: AppearanceSignature | None = None
    appearance_samples: int = 0
    assignment: IdentityAssignment | None = None


@dataclass
class _GlobalPerson:
    person_id: GlobalAnonymousPersonId
    last_camera: str
    last_seen: datetime
    last_center: tuple[float, float]
    appearance: AppearanceSignature | None
    active_track: tuple[str, str] | None = None
    history: list[tuple[str, str]] = field(default_factory=list)


def _center(box: BoundingBox) -> tuple[float, float]:
    return ((box.x_min + box.x_max) / 2, (box.y_min + box.y_max) / 2)


class AnonymousIdentityMatcher:
    """Share one instance across camera engines. In-memory only; thread-safe."""

    def __init__(
        self,
        config: MatcherConfig | None = None,
        topology: CameraTopology | None = None,
    ) -> None:
        self.config = config or MatcherConfig()
        self.topology = topology or CameraTopology()
        self._locals: dict[tuple[str, str], _LocalTrack] = {}
        self._people: dict[str, _GlobalPerson] = {}
        self._lock = threading.Lock()

    def observe(
        self,
        camera_id: str,
        local_track_id: str,
        when: datetime,
        bbox: BoundingBox,
        *,
        appearance: AppearanceSignature | None = None,
        confirmed: bool = True,
    ) -> IdentityAssignment:
        """Record one sighting. A global id is decided once, at first confirmed sighting."""

        key = (camera_id, local_track_id)
        center = _center(bbox)
        with self._lock:
            self._prune(when)
            track = self._locals.get(key)
            if track is None:
                track = _LocalTrack(camera_id, local_track_id, when, when, center, center)
                self._locals[key] = track
            track.last_seen = when
            track.last_center = center
            if appearance is not None:
                track.appearance = (
                    appearance
                    if track.appearance is None
                    else track.appearance.blend(appearance, self.config.appearance_ema)
                )
                track.appearance_samples += 1
            if track.assignment is None:
                if not confirmed:
                    return IdentityAssignment(None, "pending")
                track.assignment = self._decide(track, when)
            assignment = track.assignment
            person_id = assignment.global_person_id
            if person_id is not None:
                person = self._people[person_id.value]
                person.last_camera = camera_id
                person.last_seen = when
                person.last_center = center
                if track.appearance is not None:
                    person.appearance = track.appearance
            return assignment

    def end_track(self, camera_id: str, local_track_id: str) -> None:
        """The local tracker dropped this track; its person becomes matchable elsewhere."""

        with self._lock:
            track = self._locals.pop((camera_id, local_track_id), None)
            if track is None or track.assignment is None:
                return
            person_id = track.assignment.global_person_id
            person = self._people.get(person_id.value) if person_id else None
            if person is not None and person.active_track == (camera_id, local_track_id):
                person.active_track = None

    def known_people(self) -> int:
        with self._lock:
            return len(self._people)

    def _prune(self, when: datetime) -> None:
        retention = self.config.retention_s
        stale = [
            key
            for key, person in self._people.items()
            if person.active_track is None and (when - person.last_seen).total_seconds() > retention
        ]
        for key in stale:
            del self._people[key]

    def _plausibility(self, person: _GlobalPerson, track: _LocalTrack, when: datetime) -> float:
        gap = (track.first_seen - person.last_seen).total_seconds()
        if gap < 0:
            return 0.0
        if person.last_camera == track.camera_id:
            reentry = self.config.same_camera_reentry_s
            distance = hypot(
                track.first_center[0] - person.last_center[0],
                track.first_center[1] - person.last_center[1],
            )
            max_distance = self.config.same_camera_max_distance
            if gap > reentry or distance > max_distance:
                return 0.0
            return (1.0 - 0.5 * gap / reentry) * (1.0 - 0.5 * distance / max_distance)
        return self.topology.plausibility(person.last_camera, track.camera_id, gap)

    def _decide(self, track: _LocalTrack, when: datetime) -> IdentityAssignment:
        config = self.config
        scored: list[tuple[float, float | None, _GlobalPerson]] = []
        for person in self._people.values():
            if person.active_track is not None:
                continue
            plausibility = self._plausibility(person, track, when)
            if plausibility <= 0.0:
                continue
            appearance: float | None = None
            if (
                track.appearance is not None
                and person.appearance is not None
                and track.appearance_samples >= config.min_appearance_samples
            ):
                appearance = track.appearance.similarity(person.appearance)
            score = (1.0 - config.appearance_weight) * plausibility
            if appearance is not None:
                score += config.appearance_weight * appearance
            scored.append((score, appearance, person))
        scored.sort(key=lambda item: item[0], reverse=True)

        status: IdentityStatus = "new"
        similarity: float | None = None
        candidate: GlobalAnonymousPersonId | None = None
        chosen: _GlobalPerson | None = None
        if scored:
            best_score, best_appearance, best = scored[0]
            runner_up = scored[1][0] if len(scored) > 1 else 0.0
            similarity = round(best_score, 4)
            confident = (
                best_appearance is not None
                and best_score >= config.match_threshold
                and best_score - runner_up >= config.min_margin
            )
            if confident:
                status, chosen = "matched", best
            elif best_score >= config.uncertain_threshold:
                status, candidate = "uncertain", best.person_id
            else:
                similarity = None

        key = (track.camera_id, track.local_track_id)
        if chosen is None:
            chosen = _GlobalPerson(
                person_id=GlobalAnonymousPersonId.new(),
                last_camera=track.camera_id,
                last_seen=when,
                last_center=track.last_center,
                appearance=track.appearance,
            )
            self._people[chosen.person_id.value] = chosen
        chosen.active_track = key
        chosen.history.append(key)
        return IdentityAssignment(chosen.person_id, status, similarity, candidate)
