"""Live webcam Human Intelligence Engine preview (Intel Mac / CPU).

Runs: WebcamSource -> SSDLite -> HumanIntelligenceEngine (track, COCO-17 pose,
temporal activity) -> OpenCV overlay with boxes, IDs, skeleton, activity, trails.

Does not download weights. Does not invent keypoints or activities.
Frames stay [MOCK / SYNTHETIC]. Press q to quit.

Usage (repo root, .venv-cv):

    export ILKA_CV_PERSON_WEIGHTS="$(pwd)/data/models/ssdlite320_mobilenet_v3_large_coco.pth"
    .venv-cv/bin/python scripts/dev/preview_webcam_hie.py --index 0
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
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
from cv.intelligence.contract import PersonIntelligenceObservation
from cv.intelligence.engine import HumanIntelligenceEngine
from cv.intelligence.overlay import PipelineDiagnostics, annotate_hie_frame, count_valid_poses
from cv.opencv import load_cv2
from cv.frame import Frame
from cv.pose.coco17 import NullPoseEstimator
from cv.pose.mediapipe_adapter import MediaPipePoseEstimator
from cv.pose.torchvision_keypoint import (
    WEIGHTS_ENV as POSE_WEIGHTS_ENV,
    WEIGHTS_FILE as KEYPOINT_WEIGHTS_FILE,
    TorchvisionKeypointPoseEstimator,
)
from cv.sampling import InferenceClock, sample_person
from cv.streams.webcam import WebcamSource

DEFAULT_WEIGHTS = ROOT / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"
DEFAULT_KEYPOINT_WEIGHTS = ROOT / "data" / "models" / KEYPOINT_WEIGHTS_FILE
DEFAULT_MEDIAPIPE_TASK = ROOT / "data" / "models" / "pose_landmarker_lite.task"
WINDOW_NAME = "ILKA - Human Intelligence Engine"


def _die(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live HIE webcam: detection, tracking, COCO-17 pose, activity."
    )
    parser.add_argument("--index", type=int, default=0, help="Webcam device index")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument(
        "--pose-weights",
        type=Path,
        default=DEFAULT_KEYPOINT_WEIGHTS,
        help=f"Local Keypoint R-CNN .pth (or set {POSE_WEIGHTS_ENV})",
    )
    parser.add_argument(
        "--mediapipe-task",
        type=Path,
        default=DEFAULT_MEDIAPIPE_TASK,
        help="Optional MediaPipe .task (used only if Keypoint R-CNN unavailable)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Seconds between detector+tracker+activity updates.",
    )
    parser.add_argument(
        "--pose-interval",
        type=float,
        default=2.0,
        help="Seconds between heavy Keypoint R-CNN pose runs (skeleton cached between).",
    )
    parser.add_argument("--min-confidence", type=float, default=0.25)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="Optional path to rewrite an annotated JPEG each second",
    )
    return parser.parse_args(argv)


def _finite_positive(value: float, name: str) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        return f"{name} must be a finite number"
    if float(value) <= 0.0:
        return f"{name} must be > 0"
    return None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    for err in (
        _finite_positive(args.interval, "interval"),
        _finite_positive(args.pose_interval, "pose-interval"),
        None
        if 0.0 <= float(args.min_confidence) <= 1.0
        else "min-confidence must be in [0, 1]",
    ):
        if err:
            return _die(err)

    weights = args.weights if args.weights.is_absolute() else ROOT / args.weights
    if not weights.is_file():
        return _die(
            f"Person detector weights missing: {weights}. Set {WEIGHTS_ENV}. No download."
        )

    try:
        cv2 = load_cv2()
    except CvDependencyError as exc:
        return _die(str(exc))

    source: WebcamSource | None = None
    pose: object | None = None
    window_open = False
    try:
        try:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 960, 720)
            cv2.moveWindow(WINDOW_NAME, 80, 80)
            window_open = True
        except Exception as exc:  # noqa: BLE001
            return _die(
                "OpenCV display unavailable. On Intel Mac install opencv-python "
                f"(same version) after removing opencv-python-headless. Detail: {exc}"
            )

        try:
            detector = CpuPersonDetector(
                weights_path=weights,
                min_confidence=args.min_confidence,
            )
        except (DetectorDependencyError, DetectorModelError, ValueError) as exc:
            return _die(str(exc))

        pose_weights = (
            args.pose_weights if args.pose_weights.is_absolute() else ROOT / args.pose_weights
        )
        mediapipe_task = (
            args.mediapipe_task if args.mediapipe_task.is_absolute() else ROOT / args.mediapipe_task
        )
        pose_error = ""
        pose_ok = False
        keypoint_pose = TorchvisionKeypointPoseEstimator(pose_weights)
        if keypoint_pose.open():
            pose = keypoint_pose
            pose_ok = True
        else:
            mp_pose = MediaPipePoseEstimator(mediapipe_task, num_poses=4)
            if mp_pose.open():
                pose = mp_pose
                pose_ok = True
            else:
                pose_error = (
                    f"pose unavailable: need {pose_weights.name} "
                    f"(run scripts/dev/fetch_pose_keypoint_rcnn.py) "
                    f"or MediaPipe + {mediapipe_task.name}"
                )
                print(pose_error, file=sys.stderr)
                pose = None

        try:
            source = WebcamSource(args.index)
            source.open()
        except (VideoSourceError, ValueError) as exc:
            return _die(f"Could not open webcam: {exc}")

        camera_id = source.source_id
        # SSDLite + tracker on the UI thread. Keypoint R-CNN is async; adapter
        # exposes cached poses to the engine for association + activity.
        pose_lock = threading.Lock()
        pose_busy = False
        latest_poses: list = []
        pose_model_lock = threading.Lock()

        class _LatestPoseAdapter:
            model_id = "async-pose-cache"
            model_version = "1"

            @property
            def available(self) -> bool:
                return pose_ok

            def estimate(self, frame: Frame) -> list:
                with pose_lock:
                    return list(latest_poses)

        engine = HumanIntelligenceEngine(
            camera_id,
            pose_estimator=_LatestPoseAdapter() if pose_ok else NullPoseEstimator(),
        )
        clock = InferenceClock(args.interval)
        items: list[PersonIntelligenceObservation] = []
        last_detect_count = 0
        last_detect_ms = 0.0
        last_pose_ms = 0.0
        pose_infer_ok = False
        last_pose_at = 0.0
        frame_count = 0
        t0 = time.monotonic()
        last_snap = 0.0

        def _pose_worker(pose_frame: Frame) -> None:
            nonlocal pose_busy, latest_poses, last_pose_ms, pose_infer_ok, last_pose_at
            started = time.perf_counter()
            try:
                assert pose is not None
                with pose_model_lock:
                    estimated = pose.estimate(pose_frame)
                with pose_lock:
                    latest_poses = list(estimated)
                    pose_infer_ok = any(est.observed_count >= 3 for est in estimated)
                    last_pose_ms = (time.perf_counter() - started) * 1000.0
                    last_pose_at = time.monotonic()
            except Exception as exc:  # noqa: BLE001
                print(f"pose worker failed: {exc}", file=sys.stderr)
                with pose_lock:
                    pose_infer_ok = False
            finally:
                with pose_lock:
                    pose_busy = False

        print(
            f"HIE webcam started ({camera_id}). detect every {clock.interval_s:.2f}s, "
            f"pose every {args.pose_interval:.1f}s (async). pose_loaded={pose_ok}. Press q to quit.",
            flush=True,
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
                return _die(f"Person detector failed: {exc}")

            if found is not None:
                last_detect_count = len(found)
                t_infer = time.perf_counter()
                items = engine.process_frame(frame, found)
                last_detect_ms = (time.perf_counter() - t_infer) * 1000.0

                now_m = time.monotonic()
                with pose_lock:
                    busy = pose_busy
                if (
                    pose_ok
                    and pose is not None
                    and not busy
                    and now_m - last_pose_at >= float(args.pose_interval)
                ):
                    with pose_lock:
                        pose_busy = True
                    # Copy pixels so the capture thread can overwrite the next frame.
                    pose_frame = Frame(
                        data=frame.data.copy(),
                        index=frame.index,
                        captured_at=frame.captured_at,
                        processed_at=frame.processed_at,
                        source_id=frame.source_id,
                        is_synthetic=frame.is_synthetic,
                        source_kind=frame.source_kind,
                        mock_label=frame.mock_label,
                    )
                    worker = threading.Thread(
                        target=_pose_worker,
                        args=(pose_frame,),
                        daemon=True,
                        name="ilka-pose-worker",
                    )
                    worker.start()

            frame_count += 1
            fps = frame_count / max(time.monotonic() - t0, 1e-6)
            diagnostics = PipelineDiagnostics(
                detector_loaded=True,
                tracker_active=True,
                pose_model_loaded=pose_ok,
                pose_inference_ok=pose_infer_ok,
                activity_engine_active=True,
                camera_fps=fps,
                inference_latency_ms=last_pose_ms or last_detect_ms,
                people_detected=last_detect_count,
                people_tracked=len(items),
                valid_poses=count_valid_poses(items),
                pose_error=pose_error,
                detector_id=f"{detector.model_id}@{detector.model_version}",
            )
            annotated = annotate_hie_frame(
                frame.data,
                items,
                engine.tracker.tracks,
                diagnostics,
                cv2,
            )
            try:
                cv2.imshow(WINDOW_NAME, annotated)
                key = cv2.waitKey(1) & 0xFF
            except cv2.error:
                return _die("OpenCV window failed while showing frames.")

            if args.snapshot is not None:
                now = time.monotonic()
                if now - last_snap >= 1.0:
                    path = args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot
                    path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(path), annotated)
                    last_snap = now
                    acts = ",".join(
                        f"{i.local_track_id}:{i.activity_class.value}" for i in items
                    ) or "-"
                    print(
                        f"snap tracked={len(items)} poses={diagnostics.valid_poses} "
                        f"fps={fps:.1f} detect_ms={last_detect_ms:.0f} "
                        f"pose_ms={last_pose_ms:.0f} acts={acts}",
                        flush=True,
                    )

            if key in (ord("q"), ord("Q")):
                print("Preview closed by user.", flush=True)
                return 0
    except KeyboardInterrupt:
        print("Preview closed.", flush=True)
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
