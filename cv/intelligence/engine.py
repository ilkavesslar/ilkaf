"""Per-camera human intelligence pipeline. CPU-only; emits observations, not incidents.

Stages: person observations (from any ``PersonDetector``) -> camera tracker ->
optional pose -> movement -> temporal activity -> anonymous identity.
A failing optional stage (pose, appearance) is logged and degrades to honest
"unobserved" values instead of failing the frame.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from cv.activity.temporal import (
    RULES_VERSION,
    ActivityConfig,
    ActivityState,
    TemporalActivityRecognizer,
)
from cv.frame import Frame
from cv.gestures import GestureTracker, relative_x
from cv.identity.anonymous import (
    MATCHER_VERSION,
    AnonymousIdentityMatcher,
    AppearanceSignature,
    appearance_histogram,
)
from cv.intelligence.contract import (
    ActivityClass,
    KeypointName,
    MovementState,
    PersonIntelligenceObservation,
    missing_keypoints,
)
from cv.intelligence.tracker import CameraScopedTracker, TrackerConfig, TrackState
from cv.movement import classify_movement
from cv.observation import Observation
from cv.pose.coco17 import NullPoseEstimator, PoseEstimate, PoseEstimator, associate_poses

LOGGER = logging.getLogger(__name__)
TRACKER_VERSION = "ilka-camera-tracker-1.0.0"
PERSON_CLASS = "person"


@dataclass(frozen=True, slots=True)
class EngineConfig:
    emit_lost_tracks: bool = False
    compute_appearance: bool = True
    image_aspect: float | None = None

    def __post_init__(self) -> None:
        if self.image_aspect is not None and self.image_aspect <= 0.0:
            raise ValueError("image_aspect must be > 0")


def _frame_aspect(data: Any) -> float | None:
    shape = getattr(data, "shape", None)
    if shape is not None and len(shape) >= 2:
        height, width = int(shape[0]), int(shape[1])
    elif isinstance(data, Sequence) and data and isinstance(data[0], Sequence):
        height, width = len(data), len(data[0])
    else:
        return None
    if height < 1 or width < 1:
        return None
    return width / height


class HumanIntelligenceEngine:
    """One engine per camera. Share an ``AnonymousIdentityMatcher`` across cameras."""

    def __init__(
        self,
        camera_id: str,
        *,
        tracker_config: TrackerConfig | None = None,
        activity_config: ActivityConfig | None = None,
        pose_estimator: PoseEstimator | None = None,
        identity_matcher: AnonymousIdentityMatcher | None = None,
        config: EngineConfig | None = None,
    ) -> None:
        self.tracker = CameraScopedTracker(camera_id, tracker_config)
        self.camera_id = self.tracker.camera_id
        self.activity = TemporalActivityRecognizer(activity_config)
        self.pose: PoseEstimator = pose_estimator or NullPoseEstimator()
        self.identity = identity_matcher or AnonymousIdentityMatcher()
        self.config = config or EngineConfig()
        self._gestures = GestureTracker()
        self._movement: dict[str, MovementState] = {}
        self._global_ids: dict[str, str] = {}

    def process_frame(
        self, frame: Frame, observations: list[Observation]
    ) -> list[PersonIntelligenceObservation]:
        """Run every stage for one inference result. ``[]`` still ages tracks."""

        when = frame.captured_at
        people = [obs for obs in observations if self._accept(obs)]
        update = self.tracker.update(people, when)
        for local_track_id in update.removed:
            self._drop(local_track_id)

        visible = [track for track in update.tracks if track.matched_this_update]
        poses = self._estimate_poses(frame)
        assigned = associate_poses([(t.local_track_id, t.bbox) for t in visible], poses)
        image_aspect = self.config.image_aspect or _frame_aspect(frame.data)
        pose_version = f"{self.pose.model_id}@{self.pose.model_version}"

        results: list[PersonIntelligenceObservation] = []
        for track in update.tracks:
            if track.matched_this_update:
                results.append(
                    self._visible(
                        frame, track, assigned.get(track.local_track_id), image_aspect, pose_version
                    )
                )
            elif self.config.emit_lost_tracks:
                results.append(self._lost(frame, track, pose_version))
        active_numbers = {track.number for track in update.tracks}
        self._gestures.retain(active_numbers)
        return results

    def _accept(self, observation: Observation) -> bool:
        if observation.object_class != PERSON_CLASS:
            return False
        if observation.camera_id is not None and observation.camera_id != self.camera_id:
            LOGGER.warning(
                "dropping observation from another camera",
                extra={
                    "component": "cv.intelligence",
                    "camera_id": self.camera_id,
                    "observation_camera_id": observation.camera_id,
                    "observation_id": str(observation.observation_id),
                },
            )
            return False
        return True

    def _estimate_poses(self, frame: Frame) -> list[PoseEstimate]:
        if not self.pose.available:
            return []
        try:
            return list(self.pose.estimate(frame))
        except Exception:
            LOGGER.warning(
                "pose stage failed; keypoints reported as unobserved",
                exc_info=True,
                extra={"component": "cv.intelligence", "camera_id": self.camera_id},
            )
            return []

    def _appearance(self, frame: Frame, track: TrackState) -> AppearanceSignature | None:
        if not self.config.compute_appearance:
            return None
        try:
            return appearance_histogram(frame.data, track.bbox)
        except Exception:
            LOGGER.warning(
                "appearance stage failed; identity falls back to new ids",
                exc_info=True,
                extra={"component": "cv.intelligence", "camera_id": self.camera_id},
            )
            return None

    def _visible(
        self,
        frame: Frame,
        track: TrackState,
        pose: PoseEstimate | None,
        image_aspect: float | None,
        pose_version: str,
    ) -> PersonIntelligenceObservation:
        when = frame.captured_at
        track_id = track.local_track_id
        movement = classify_movement(track.center_history, self._movement.get(track_id))
        self._movement[track_id] = movement

        keypoints = pose.keypoints if pose is not None else missing_keypoints()
        if pose is not None:
            left = pose.point(KeypointName.LEFT_WRIST)
            right = pose.point(KeypointName.RIGHT_WRIST)
            self._gestures.update(
                track.number,
                when,
                relative_x(left[0], track.bbox) if left else None,
                relative_x(right[0], track.bbox) if right else None,
            )
        waving = self._gestures.waving(track.number, when)

        activity = self.activity.update(
            track_id,
            when,
            track.bbox,
            keypoints=keypoints if pose is not None else None,
            movement_state=movement,
            waving=waving,
            image_aspect=image_aspect,
        )

        assignment = self.identity.observe(
            self.camera_id,
            track_id,
            when,
            track.bbox,
            appearance=self._appearance(frame, track),
            confirmed=track.status == "active",
        )
        global_id = assignment.global_person_id
        if global_id is not None:
            self._global_ids[track_id] = global_id.value
        return self._build(frame, track, keypoints, activity, movement, pose_version)

    def _lost(
        self, frame: Frame, track: TrackState, pose_version: str
    ) -> PersonIntelligenceObservation:
        return self._build(
            frame,
            track,
            missing_keypoints(),
            ActivityState.unknown(),
            "unknown",
            pose_version,
        )

    def _build(
        self,
        frame: Frame,
        track: TrackState,
        keypoints: tuple[Any, ...],
        activity: ActivityState,
        movement: MovementState,
        pose_version: str,
    ) -> PersonIntelligenceObservation:
        observation = track.observation
        synthetic = frame.is_synthetic or observation.is_synthetic
        return PersonIntelligenceObservation(
            observation_id=uuid4(),
            camera_id=self.camera_id,
            source_id=frame.source_id,
            frame_id=str(frame.index),
            timestamp=frame.captured_at,
            local_track_id=track.local_track_id,
            global_person_id=self._global_ids.get(track.local_track_id),
            bbox=track.bbox,
            detection_confidence=observation.confidence,
            keypoints=keypoints,
            activity_class=activity.activity_class,
            activity_confidence=(
                0.0 if activity.activity_class is ActivityClass.UNKNOWN else activity.confidence
            ),
            activity_started_at=activity.started_at,
            activity_duration_s=activity.duration_s,
            movement_state=movement,
            tracking_status=track.status,
            model_versions={
                "detector": f"{observation.model_id}@{observation.model_version}",
                "tracker": TRACKER_VERSION,
                "pose": pose_version,
                "activity": RULES_VERSION,
                "identity": MATCHER_VERSION,
            },
            is_synthetic=synthetic,
            mock_label=frame.mock_label if frame.is_synthetic else observation.mock_label,
        )

    def _drop(self, local_track_id: str) -> None:
        self.activity.forget(local_track_id)
        self._movement.pop(local_track_id, None)
        self._global_ids.pop(local_track_id, None)
        self.identity.end_track(self.camera_id, local_track_id)
