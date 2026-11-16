"""TorchVision Keypoint R-CNN pose (COCO-17). CPU lab adapter for Intel Mac.

Weights are never downloaded by this constructor. Provide a local ``.pth`` that
matches the pinned digest, or set ``ILKA_CV_POSE_WEIGHTS``.
"""

from __future__ import annotations

import hashlib
import logging
import os
from math import isfinite
from pathlib import Path
from typing import Any

from cv.frame import Frame
from cv.intelligence.contract import KEYPOINT_COUNT, Keypoint
from cv.pose.coco17 import PoseEstimate

LOGGER = logging.getLogger(__name__)
MODEL_ID = "torchvision-keypointrcnn-resnet50-fpn"
WEIGHTS_ENV = "ILKA_CV_POSE_WEIGHTS"
WEIGHTS_FILE = "keypointrcnn_resnet50_fpn_coco-fc266e95.pth"
WEIGHTS_URL = "https://download.pytorch.org/models/" + WEIGHTS_FILE
# Official TorchVision COCO_V1 artifact (filename SHA-256 prefix fc266e95).
WEIGHTS_SHA256_PREFIX = "fc266e95"
WEIGHTS_SHA256 = "fc266e953d2b302cdcbb9ae66f71f6b0d4649928bf02dc573961e361e4918926"
WEIGHTS_BYTES = 237_034_793
WEIGHTS_BYTES_MIN = 200_000_000  # catalog ~226 MiB
DEFAULT_MIN_SCORE = 0.5
DEFAULT_MIN_KEYPOINT_SCORE = 0.2
# Full-res Keypoint R-CNN is too slow for live Intel Mac CPU (~3–4s/frame).
DEFAULT_MAX_INFERENCE_SIDE = 480
_CPU = "cpu"
_PERSON_LABEL = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_pose_weights(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit
    env = os.environ.get(WEIGHTS_ENV, "").strip()
    if env:
        return Path(env)
    default = Path(__file__).resolve().parents[2] / "data" / "models" / WEIGHTS_FILE
    if default.is_file():
        return default
    # Also accept short alias name used in docs.
    alias = Path(__file__).resolve().parents[2] / "data" / "models" / "keypointrcnn_resnet50_fpn_coco.pth"
    if alias.is_file():
        return alias
    return None


def _to_keypoint(x: float, y: float, score: float, width: int, height: int, floor: float) -> Keypoint:
    if width < 1 or height < 1 or not (isfinite(x) and isfinite(y) and isfinite(score)):
        return Keypoint.missing()
    if score < floor:
        return Keypoint.missing()
    nx = x / float(width)
    ny = y / float(height)
    if not (0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0):
        return Keypoint.missing()
    conf = min(max(float(score), 0.0), 1.0)
    return Keypoint(x=nx, y=ny, confidence=conf, visibility=conf)


class TorchvisionKeypointPoseEstimator:
    """Full-frame Keypoint R-CNN → COCO-17. Associate to tracks with ``associate_poses``."""

    model_id = MODEL_ID

    def __init__(
        self,
        weights_path: Path | None = None,
        *,
        min_score: float = DEFAULT_MIN_SCORE,
        min_keypoint_score: float = DEFAULT_MIN_KEYPOINT_SCORE,
        max_inference_side: int = DEFAULT_MAX_INFERENCE_SIDE,
        expected_sha256: str | None = None,
    ) -> None:
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be in [0, 1]")
        if not 0.0 <= min_keypoint_score <= 1.0:
            raise ValueError("min_keypoint_score must be in [0, 1]")
        if max_inference_side < 64:
            raise ValueError("max_inference_side must be >= 64")
        path = resolve_pose_weights(weights_path)
        self._path = path
        self._min_score = min_score
        self._min_keypoint_score = min_keypoint_score
        self._max_inference_side = max_inference_side
        self._expected_sha256 = expected_sha256  # optional full digest; prefix always checked
        self._model: Any | None = None
        self._torch: Any | None = None
        self.model_version = "unloaded"

    @property
    def available(self) -> bool:
        return self._model is not None

    def open(self) -> bool:
        if self._model is not None:
            return True
        if self._path is None or not self._path.is_file():
            LOGGER.info(
                "keypoint pose weights missing; pose disabled",
                extra={"component": "cv.pose", "env": WEIGHTS_ENV},
            )
            return False
        try:
            import torch
            from torchvision.models.detection import keypointrcnn_resnet50_fpn
        except ImportError:
            LOGGER.warning(
                "torch/torchvision unavailable for keypoint pose",
                exc_info=True,
                extra={"component": "cv.pose"},
            )
            return False

        if self._path.stat().st_size < WEIGHTS_BYTES_MIN:
            LOGGER.warning(
                "pose weights file too small; pose disabled",
                extra={"component": "cv.pose", "path": self._path.name},
            )
            return False
        digest = sha256_file(self._path)
        expected = self._expected_sha256 or WEIGHTS_SHA256
        if digest != expected or not digest.startswith(WEIGHTS_SHA256_PREFIX):
            LOGGER.warning(
                "pose weights digest mismatch; pose disabled",
                extra={"component": "cv.pose", "path": self._path.name},
            )
            return False

        try:
            # weights_backbone=None avoids a silent ImageNet ResNet download.
            model = keypointrcnn_resnet50_fpn(weights=None, weights_backbone=None)
            state = torch.load(self._path, map_location=_CPU, weights_only=True)
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]
            model.load_state_dict(state)
            model.to(_CPU)
            model.eval()
        except Exception:
            LOGGER.warning(
                "keypoint pose model could not be opened",
                exc_info=True,
                extra={"component": "cv.pose"},
            )
            return False

        self._torch = torch
        self._model = model
        self.model_version = f"local:{self._path.name}"
        return True

    def estimate(self, frame: Frame) -> list[PoseEstimate]:
        if self._model is None or self._torch is None:
            return []
        image = frame.data
        shape = getattr(image, "shape", None)
        if shape is None or len(shape) < 3:
            return []
        orig_h, orig_w = int(shape[0]), int(shape[1])
        try:
            import numpy as np

            array = np.asarray(image)
            if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] < 3:
                return []
            scale = 1.0
            work = array
            longest = max(orig_h, orig_w)
            if longest > self._max_inference_side:
                scale = self._max_inference_side / float(longest)
                new_w = max(1, int(round(orig_w * scale)))
                new_h = max(1, int(round(orig_h * scale)))
                # Local import keeps OpenCV optional for unit tests that only
                # exercise keypoint normalization helpers.
                import cv2

                work = cv2.resize(array, (new_w, new_h), interpolation=cv2.INTER_AREA)
            infer_h, infer_w = int(work.shape[0]), int(work.shape[1])
            # BGR -> RGB float tensor CHW [0,1]
            rgb = work[:, :, :3][:, :, ::-1].copy()
            tensor = self._torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
            with self._torch.inference_mode():
                outputs = self._model([tensor])[0]
        except Exception:
            LOGGER.warning(
                "keypoint pose inference failed",
                exc_info=True,
                extra={"component": "cv.pose", "frame_index": frame.index},
            )
            return []

        scores = outputs.get("scores")
        labels = outputs.get("labels")
        keypoints = outputs.get("keypoints")
        keypoint_scores = outputs.get("keypoints_scores")
        if keypoints is None or scores is None or labels is None:
            return []

        poses: list[PoseEstimate] = []
        count = int(keypoints.shape[0])
        for index in range(count):
            if int(labels[index].item()) != _PERSON_LABEL:
                continue
            if float(scores[index].item()) < self._min_score:
                continue
            person_kps = keypoints[index]
            if person_kps.shape[0] < KEYPOINT_COUNT:
                continue
            scores_row = None
            if keypoint_scores is not None:
                scores_row = keypoint_scores[index]
            joints: list[Keypoint] = []
            for joint_i in range(KEYPOINT_COUNT):
                x = float(person_kps[joint_i, 0].item())
                y = float(person_kps[joint_i, 1].item())
                if scores_row is not None:
                    score = float(scores_row[joint_i].item())
                else:
                    score = float(person_kps[joint_i, 2].item()) if person_kps.shape[1] > 2 else 0.0
                # Normalize in inference space (scale cancels for normalized coords).
                joints.append(
                    _to_keypoint(x, y, score, infer_w, infer_h, self._min_keypoint_score)
                )
            poses.append(PoseEstimate(keypoints=tuple(joints)))
        return poses

    def close(self) -> None:
        self._model = None
        self._torch = None
