"""Draw Human Intelligence observations on BGR frames. Lab visualization only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from cv.intelligence.contract import KEYPOINT_COUNT, PersonIntelligenceObservation
from cv.intelligence.tracker import TrackState
from cv.observation import BoundingBox

# COCO-17 bones (pairs of joint indices).
SKELETON_EDGES: tuple[tuple[int, int], ...] = (
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
)

BOX_COLOR = (40, 200, 80)
BONE_COLOR = (59, 130, 246)
JOINT_COLOR = (255, 200, 40)
TRAIL_COLOR = (180, 180, 40)
TEXT_COLOR = (255, 255, 255)
BANNER_COLOR = (30, 30, 30)
PANEL_COLOR = (20, 20, 20)


@dataclass(frozen=True, slots=True)
class PipelineDiagnostics:
    detector_loaded: bool
    tracker_active: bool
    pose_model_loaded: bool
    pose_inference_ok: bool
    activity_engine_active: bool
    camera_fps: float
    inference_latency_ms: float
    people_detected: int
    people_tracked: int
    valid_poses: int
    pose_error: str = ""
    detector_id: str = ""


def pixel_xyxy(box: BoundingBox, width: int, height: int) -> tuple[int, int, int, int]:
    x1 = max(0, min(width - 1, round(box.x_min * width)))
    y1 = max(0, min(height - 1, round(box.y_min * height)))
    x2 = max(0, min(width - 1, round(box.x_max * width)))
    y2 = max(0, min(height - 1, round(box.y_max * height)))
    return x1, y1, x2, y2


def pixel_xy(x: float, y: float, width: int, height: int) -> tuple[int, int]:
    return (
        max(0, min(width - 1, round(x * width))),
        max(0, min(height - 1, round(y * height))),
    )


def count_valid_poses(items: Sequence[PersonIntelligenceObservation]) -> int:
    total = 0
    for item in items:
        if sum(1 for joint in item.keypoints if joint.observed) >= 3:
            total += 1
    return total


def draw_skeleton(
    canvas: Any,
    item: PersonIntelligenceObservation,
    width: int,
    height: int,
    cv2: Any,
) -> int:
    """Draw COCO-17 bones/joints. Returns observed joint count. Never invents joints."""

    observed = 0
    points: list[tuple[int, int] | None] = [None] * KEYPOINT_COUNT
    for index, joint in enumerate(item.keypoints):
        if not joint.observed or joint.x is None or joint.y is None:
            continue
        points[index] = pixel_xy(joint.x, joint.y, width, height)
        observed += 1
    for left, right in SKELETON_EDGES:
        a = points[left]
        b = points[right]
        if a is None or b is None:
            continue
        cv2.line(canvas, a, b, BONE_COLOR, 2, cv2.LINE_AA)
    for point in points:
        if point is None:
            continue
        cv2.circle(canvas, point, 3, JOINT_COLOR, -1, cv2.LINE_AA)
    return observed


def draw_trail(
    canvas: Any,
    track: TrackState,
    width: int,
    height: int,
    cv2: Any,
    *,
    max_points: int = 24,
) -> None:
    history = track.center_history[-max_points:]
    if len(history) < 2:
        return
    pts = [pixel_xy(x, y, width, height) for _when, x, y in history]
    for index in range(1, len(pts)):
        cv2.line(canvas, pts[index - 1], pts[index], TRAIL_COLOR, 2, cv2.LINE_AA)


def person_caption(item: PersonIntelligenceObservation) -> str:
    short_id = item.local_track_id.rsplit(":", 1)[-1]
    activity = item.activity_class.value
    if activity == "unknown":
        activity_part = "activity unknown"
    else:
        conf = round(item.activity_confidence * 100)
        activity_part = f"{activity} {conf}%"
    det = round(item.detection_confidence * 100)
    return f"{short_id} · det {det}% · {activity_part} · {item.tracking_status}"


def annotate_hie_frame(
    image: Any,
    items: Sequence[PersonIntelligenceObservation],
    tracks: Sequence[TrackState],
    diagnostics: PipelineDiagnostics,
    cv2: Any,
) -> Any:
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 2:
        raise ValueError("frame has no spatial shape")
    height, width = int(shape[0]), int(shape[1])
    canvas = image.copy()
    by_id = {track.local_track_id: track for track in tracks}

    for item in items:
        x1, y1, x2, y2 = pixel_xyxy(item.bbox, width, height)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), BOX_COLOR, 2)
        track = by_id.get(item.local_track_id)
        if track is not None:
            draw_trail(canvas, track, width, height, cv2)
        draw_skeleton(canvas, item, width, height, cv2)
        caption = person_caption(item)
        cv2.putText(
            canvas,
            caption,
            (x1, max(16, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )

    banner = (
        f"HIE live  people={diagnostics.people_tracked}  "
        f"poses={diagnostics.valid_poses}  "
        f"FPS={diagnostics.camera_fps:.1f}  "
        f"infer={diagnostics.inference_latency_ms:.0f}ms"
    )
    cv2.rectangle(canvas, (0, 0), (width, 28), BANNER_COLOR, thickness=-1)
    cv2.putText(
        canvas,
        banner,
        (8, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )

    panel_lines = [
        f"detector: {'OK' if diagnostics.detector_loaded else 'MISSING'} {diagnostics.detector_id}",
        f"tracker: {'OK' if diagnostics.tracker_active else 'OFF'}",
        f"pose model: {'OK' if diagnostics.pose_model_loaded else 'MISSING'}",
        f"pose infer: {'OK' if diagnostics.pose_inference_ok else 'FAIL/EMPTY'}",
        f"activity: {'OK' if diagnostics.activity_engine_active else 'OFF'}",
        f"detected={diagnostics.people_detected} tracked={diagnostics.people_tracked}",
    ]
    if diagnostics.pose_error:
        panel_lines.append(f"pose err: {diagnostics.pose_error[:60]}")
    panel_h = 18 + 16 * len(panel_lines)
    cv2.rectangle(canvas, (0, height - panel_h), (min(width, 520), height), PANEL_COLOR, -1)
    for index, line in enumerate(panel_lines):
        cv2.putText(
            canvas,
            line,
            (8, height - panel_h + 16 + index * 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )
    return canvas
