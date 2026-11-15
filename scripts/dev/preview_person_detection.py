"""Lab preview: FileSource + CpuPersonDetector with drawn person boxes.

Person observations only — not incidents, alerts, PPE, or events (ADR 0003).
File frames stay labeled [MOCK / SYNTHETIC]. Does not download weights.

Usage (repo root, .venv-cv):

    $env:ILKA_CV_PERSON_WEIGHTS = "$(Get-Location)\\data\\models\\" + `
        "ssdlite320_mobilenet_v3_large_coco.pth"
    python scripts/dev/preview_person_detection.py
    python scripts/dev/preview_person_detection.py `
        --no-display --output data/videos/people-detection-annotated.mp4
"""

from __future__ import annotations

import argparse
import os
import sys
from math import isfinite
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_cv() -> tuple[object, ...]:
    """Import the lab pipeline after the repository root is on sys.path."""
    from cv.detectors.person_cpu import WEIGHTS_ENV, CpuPersonDetector
    from cv.errors import (
        CvDependencyError,
        DetectorDependencyError,
        DetectorInferenceError,
        DetectorModelError,
        VideoSourceError,
    )
    from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
    from cv.observation import BoundingBox, Observation
    from cv.opencv import load_cv2
    from cv.streams.file import FileSource

    return (
        WEIGHTS_ENV,
        CpuPersonDetector,
        CvDependencyError,
        DetectorDependencyError,
        DetectorInferenceError,
        DetectorModelError,
        VideoSourceError,
        MOCK_SYNTHETIC_LABEL,
        Frame,
        BoundingBox,
        Observation,
        load_cv2,
        FileSource,
    )


(
    WEIGHTS_ENV,
    CpuPersonDetector,
    CvDependencyError,
    DetectorDependencyError,
    DetectorInferenceError,
    DetectorModelError,
    VideoSourceError,
    MOCK_SYNTHETIC_LABEL,
    Frame,
    BoundingBox,
    Observation,
    load_cv2,
    FileSource,
) = _load_cv()

DEFAULT_VIDEO = ROOT / "data" / "videos" / "people-detection (1).mp4"
DEFAULT_WEIGHTS = ROOT / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"
DEFAULT_OUTPUT = ROOT / "data" / "videos" / "people-detection-annotated.mp4"
WINDOW_NAME = "ILKA - Person Detection"
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


def _annotate(image, observations: list[Observation], *, frame_index: int, total_observations: int):
    height, width = int(image.shape[0]), int(image.shape[1])
    canvas = image.copy()
    for item in observations:
        x1, y1, x2, y2 = _pixel_xyxy(item.bounding_box, width, height)
        cv2 = load_cv2()
        cv2.rectangle(canvas, (x1, y1), (x2, y2), BOX_COLOR, 2)
        caption = f"{item.object_class} {item.confidence:.2f}"
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
    cv2 = load_cv2()
    cv2.rectangle(canvas, (0, 0), (width, 56), BANNER_COLOR, thickness=-1)
    cv2.putText(
        canvas,
        WINDOW_NAME,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )
    status = (
        f"frame {frame_index + 1}  detections {len(observations)}  "
        f"total {total_observations}  {MOCK_SYNTHETIC_LABEL}"
    )
    cv2.putText(
        canvas,
        status,
        (8, 46),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )
    return canvas


def _probe_fps(path: Path) -> float:
    cv2 = load_cv2()
    capture = cv2.VideoCapture(str(path))
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    finally:
        capture.release()
    if fps <= 0.0 or fps > 120.0:
        return 25.0
    return fps


def _open_writer(path: Path, width: int, height: int, fps: float):
    cv2 = load_cv2()
    path.parent.mkdir(parents=True, exist_ok=True)
    for fourcc_name in ("mp4v", "avc1", "XVID"):
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*fourcc_name),
            fps,
            (width, height),
        )
        if writer.isOpened():
            return writer
        writer.release()
    return None


def _try_open_window() -> bool:
    cv2 = load_cv2()
    try:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        return True
    except cv2.error:
        return False
    except Exception:  # noqa: BLE001
        return False


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draw CpuPersonDetector boxes on a FileSource video (lab demo)."
    )
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO, help="Input video path")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS, help="Local .pth weights")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Annotated MP4 path (used when saving)",
    )
    parser.add_argument("--no-display", action="store_true", help="Do not open an OpenCV window")
    parser.add_argument("--no-save", action="store_true", help="Do not write an annotated video")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = all)")
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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    confidence_error = _confidence_message(args.min_confidence)
    if confidence_error:
        return _die(confidence_error)
    video = args.video if args.video.is_absolute() else ROOT / args.video
    weights = args.weights if args.weights.is_absolute() else ROOT / args.weights
    output = args.output if args.output.is_absolute() else ROOT / args.output

    if not video.is_file():
        return _die(f"Video file is missing: {video}")
    if not weights.is_file():
        return _die(
            f"Person detector weights are missing: {weights}. "
            "Do not download from this script. Place the local .pth file or run "
            "scripts/dev/fetch_person_detector_weights.py separately."
        )

    try:
        cv2 = load_cv2()
    except CvDependencyError as exc:
        return _die(str(exc))

    os.environ[WEIGHTS_ENV] = str(weights)

    display = not args.no_display
    save = not args.no_save
    window_ok = False
    writer = None
    source: FileSource | None = None
    frame_count = 0
    total_observations = 0

    try:
        try:
            detector = CpuPersonDetector(weights_path=weights, min_confidence=args.min_confidence)
        except (DetectorDependencyError, DetectorModelError, ValueError) as exc:
            return _die(str(exc))

        try:
            source = FileSource(video, source_id=video.name)
            source.open()
        except VideoSourceError as exc:
            return _die(f"Could not open video: {exc}")

        if display:
            window_ok = _try_open_window()
            if not window_ok:
                print(
                    "OpenCV display is unavailable (headless build or no GUI). "
                    f"Annotated video will be written to {output}",
                    file=sys.stderr,
                )
                save = True

        fps = _probe_fps(video)

        while True:
            if args.max_frames and frame_count >= args.max_frames:
                break
            frame: Frame | None = source.read()
            if frame is None:
                break
            try:
                observations = detector.detect(frame)
            except DetectorInferenceError as exc:
                return _die(f"Person detector inference failed: {exc}")
            frame_count += 1
            total_observations += len(observations)
            image = frame.data
            shape = getattr(image, "shape", None)
            if shape is None or len(shape) < 2:
                return _die("Decoded frame has no spatial shape")
            annotated = _annotate(
                image,
                observations,
                frame_index=frame.index,
                total_observations=total_observations,
            )
            height, width = int(annotated.shape[0]), int(annotated.shape[1])
            if save and writer is None:
                writer = _open_writer(output, width, height, fps)
                if writer is None:
                    return _die(f"Could not open annotated video writer: {output}")
            if writer is not None:
                writer.write(annotated)
            if window_ok:
                try:
                    cv2.imshow(WINDOW_NAME, annotated)
                    key = cv2.waitKey(1) & 0xFF
                except cv2.error:
                    print(
                        "OpenCV window failed while showing frames. "
                        "Continuing with annotated file output only.",
                        file=sys.stderr,
                    )
                    window_ok = False
                    save = True
                    if writer is None:
                        writer = _open_writer(output, width, height, fps)
                        if writer is None:
                            return _die(f"Could not open annotated video writer: {output}")
                        writer.write(annotated)
                    key = 0xFF
                if key in (27, ord("q"), ord("Q")):
                    print("Preview closed by user.")
                    break

        if frame_count == 0:
            return _die("Video opened but produced no frames")
        print(
            f"frames={frame_count} person_observations={total_observations} "
            f"model_id={detector.model_id} model_version={detector.model_version}"
        )
        if writer is not None:
            print(f"wrote {output}")
            if not window_ok:
                print(f"Open the annotated file to view boxes: {output}")
        return 0
    finally:
        if source is not None:
            source.close()
        if writer is not None:
            writer.release()
        try:
            cv2.destroyAllWindows()
        except Exception:  # noqa: BLE001, S110
            pass


if __name__ == "__main__":
    raise SystemExit(main())
