"""Dev preview: laptop webcam, sampled CPU person detection, local window.

Observations only. Frames stay [MOCK / SYNTHETIC]. Does not open RTSP cameras,
download weights, or create incidents.

Usage (repo root, .venv-cv):

    $env:ILKA_CV_PERSON_WEIGHTS = "$(Get-Location)\\data\\models\\" + `
        "ssdlite320_mobilenet_v3_large_coco.pth"
    .\\.venv-cv\\Scripts\\python.exe scripts\\dev\\preview_webcam_person.py
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from math import isfinite
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cv.detectors.person_cpu import WEIGHTS_ENV, CpuPersonDetector
from cv.errors import (
    CvDependencyError,
    DetectorDependencyError,
    DetectorInferenceError,
    DetectorModelError,
    VideoSourceError,
)
from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.gestures import GestureTracker, PoseCue, associate_cues, relative_x
from cv.movement import Movement, classify_movement
from cv.observation import BoundingBox
from cv.opencv import load_cv2
from cv.pose_wrists import WristPoseReader
from cv.sampling import InferenceClock, sample_person
from cv.streams.webcam import WebcamSource
from cv.tracking import PersonTracker, Track

DEFAULT_WEIGHTS = ROOT / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"
DEFAULT_POSE = ROOT / "data" / "models" / "pose_landmarker_lite.task"
WINDOW_NAME = "ILKA - Webcam Person Detection"
BOX_COLOR = (40, 200, 80)
TEXT_COLOR = (255, 255, 255)
BANNER_COLOR = (30, 30, 30)


def _die(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def _pixel_xyxy(box: BoundingBox, width: int, height: int) -> tuple[int, int, int, int]:
    x1 = round(box.x_min * width)
    y1 = round(box.y_min * height)
    x2 = round(box.x_max * width)
    y2 = round(box.y_max * height)
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width - 1))
    y2 = max(0, min(y2, height - 1))
    return x1, y1, x2, y2


def _caption(track: Track, movement: str, waving: bool) -> str:
    confidence = round(track.latest_observation.confidence * 100)
    parts = [f"Person #{track.track_id:02d}"]
    if movement == "moving":
        parts.append("Moving")
    if waving:
        parts.append("Waving")
    parts.append(f"{confidence}%")
    return " · ".join(parts)


def _annotate(
    image: object,
    tracks: list[Track],
    movements: dict[int, str],
    gestures: GestureTracker,
    when: datetime | None,
) -> object:
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 2:
        raise VideoSourceError("webcam frame has no spatial shape")
    height, width = int(shape[0]), int(shape[1])
    canvas = image.copy()
    cv2 = load_cv2()
    for track in tracks:
        item = track.latest_observation
        x1, y1, x2, y2 = _pixel_xyxy(item.bounding_box, width, height)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), BOX_COLOR, 2)
        waving = when is not None and gestures.waving(track.track_id, when)
        caption = _caption(track, movements.get(track.track_id, "unknown"), waving)
        cv2.putText(
            canvas,
            caption,
            (x1, max(16, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )
    cv2.rectangle(canvas, (0, 0), (width, 28), BANNER_COLOR, thickness=-1)
    cv2.putText(
        canvas,
        f"{MOCK_SYNTHETIC_LABEL}  {len(tracks)} person",
        (8, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )
    return canvas


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show sampled CPU person boxes on the laptop webcam (dev only)."
    )
    parser.add_argument("--index", type=int, default=0, help="Webcam device index")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS, help="Local .pth weights")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between inferences. Preview frames stay continuous.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.25,
        help="Same default as CpuPersonDetector (0.25 inclusive)",
    )
    return parser.parse_args(argv)


def _confidence_message(value: float) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        return "min-confidence must be a finite number in [0.0, 1.0]"
    if float(value) < 0.0 or float(value) > 1.0:
        return "min-confidence must be in [0.0, 1.0]"
    return None


def _interval_message(value: float) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        return "interval must be a finite number of seconds greater than 0"
    if float(value) <= 0.0:
        return "interval must be greater than 0"
    return None


def _record_waves(
    gestures: GestureTracker,
    tracks: list[Track],
    cues: list[PoseCue],
    when: datetime,
) -> None:
    pairs = [(track.track_id, track.latest_observation.bounding_box) for track in tracks]
    assigned = associate_cues(pairs, cues)
    for track in tracks:
        cue = assigned.get(track.track_id)
        box = track.latest_observation.bounding_box
        left = relative_x(cue.left_wrist[0], box) if cue and cue.left_wrist else None
        right = relative_x(cue.right_wrist[0], box) if cue and cue.right_wrist else None
        gestures.update(track.track_id, when, left, right)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    confidence_error = _confidence_message(args.min_confidence)
    if confidence_error:
        return _die(confidence_error)
    interval_error = _interval_message(args.interval)
    if interval_error:
        return _die(interval_error)
    weights = args.weights if args.weights.is_absolute() else ROOT / args.weights
    if not weights.is_file():
        return _die(
            f"Person detector weights are missing: {weights}. "
            f"Set {WEIGHTS_ENV} by placing the local .pth file. "
            "This script does not download weights."
        )

    try:
        cv2 = load_cv2()
    except CvDependencyError as exc:
        return _die(str(exc))

    source: WebcamSource | None = None
    pose: WristPoseReader | None = None
    window_open = False
    try:
        try:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            window_open = True
        except cv2.error:
            return _die(
                "OpenCV display is unavailable. The installed OpenCV build cannot "
                "open a preview window."
            )
        except Exception as exc:  # noqa: BLE001
            return _die(f"OpenCV display is unavailable: {exc}")

        try:
            detector = CpuPersonDetector(
                weights_path=weights,
                min_confidence=args.min_confidence,
            )
        except (DetectorDependencyError, DetectorModelError, ValueError) as exc:
            return _die(str(exc))

        try:
            source = WebcamSource(args.index)
            source.open()
        except (VideoSourceError, ValueError) as exc:
            return _die(f"Could not open webcam: {exc}")

        clock = InferenceClock(args.interval)
        tracker = PersonTracker()
        gestures = GestureTracker()
        pose = WristPoseReader(DEFAULT_POSE)
        if not pose.open():
            print(
                "Pose landmarks are unavailable. Movement labels still run. Waving stays off.",
                file=sys.stderr,
            )
        tracks: list[Track] = []
        movements: dict[int, Movement] = {}
        observed_at: datetime | None = None
        print(
            f"Webcam preview started. Inference every {clock.interval_s:.1f}s. "
            "Press q to quit. Frames are [MOCK / SYNTHETIC]."
        )
        while True:
            try:
                frame = source.read()
            except VideoSourceError as exc:
                return _die(f"Webcam read failed: {exc}")
            try:
                found = sample_person(
                    detector,
                    frame,
                    source.source_id,
                    clock,
                    time.monotonic(),
                )
            except DetectorInferenceError as exc:
                return _die(f"Person detector inference failed: {exc}")
            if found is not None:
                observed_at = frame.processed_at
                tracks = tracker.update(found, observed_at)
                active = {track.track_id for track in tracks}
                movements = {
                    track.track_id: classify_movement(
                        track.center_history,
                        movements.get(track.track_id),
                    )
                    for track in tracks
                }
                _record_waves(gestures, tracks, pose.read(frame.data), observed_at)
                gestures.retain(active)
            annotated = _annotate(frame.data, tracks, movements, gestures, observed_at)
            try:
                cv2.imshow(WINDOW_NAME, annotated)
                key = cv2.waitKey(1) & 0xFF
            except cv2.error:
                return _die("OpenCV window failed while showing frames.")
            if key in (ord("q"), ord("Q")):
                print("Preview closed by user.")
                return 0
    except KeyboardInterrupt:
        print("Preview closed.")
        return 0
    finally:
        if pose is not None:
            pose.close()
        if source is not None:
            source.close()
        if window_open:
            try:
                cv2.destroyAllWindows()
            except Exception:  # noqa: BLE001, S110
                pass


if __name__ == "__main__":
    raise SystemExit(main())
