from datetime import UTC, datetime, timedelta

import pytest
from cv.detectors.mapping import (
    COCO_PERSON_LABEL,
    PERSON_CLASS,
    detections_to_observations,
    is_person_label,
    normalize_pixel_box,
)
from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
from cv.observation import BoundingBox


def _frame(*, width: int = 40, height: int = 20, **overrides: object) -> Frame:
    class _Shape:
        shape = (height, width, 3)

    now = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    values: dict[str, object] = {
        "data": _Shape(),
        "index": 0,
        "captured_at": now,
        "processed_at": now + timedelta(milliseconds=8),
        "source_id": "clip.avi",
    }
    values.update(overrides)
    return Frame(**values)  # type: ignore[arg-type]


def test_normalize_pixel_box_clips_and_scales() -> None:
    box = normalize_pixel_box(-4, -2, 44, 22, width=40, height=20)
    assert box == BoundingBox(x_min=0.0, y_min=0.0, x_max=1.0, y_max=1.0)


def test_normalize_pixel_box_skips_empty_after_clip() -> None:
    assert normalize_pixel_box(50, 1, 60, 2, width=40, height=20) is None
    assert normalize_pixel_box(1, 1, 1, 8, width=40, height=20) is None
    assert normalize_pixel_box(float("nan"), 0, 10, 10, width=40, height=20) is None
    assert normalize_pixel_box(0, 0, float("inf"), 10, width=40, height=20) is None


def test_person_label_accepts_only_integer_one_and_person_string() -> None:
    assert is_person_label(1) is True
    assert is_person_label("person") is True
    assert is_person_label(1.9) is False
    assert is_person_label(True) is False
    assert is_person_label(1.0) is False
    frame = _frame()
    rows = detections_to_observations(
        boxes=[(4, 2, 20, 18), (4, 2, 20, 18), (4, 2, 20, 18), (4, 2, 20, 18)],
        labels=[1.9, True, 1, "person"],
        scores=[0.9, 0.9, 0.8, 0.7],
        frame=frame,
        width=40,
        height=20,
        min_confidence=0.25,
        model_id="lab-ssdlite",
        model_version="test",
    )
    assert [item.confidence for item in rows] == [0.8, 0.7]
    assert all(item.object_class == PERSON_CLASS for item in rows)
    assert all(item.mock_label == MOCK_SYNTHETIC_LABEL for item in rows)


def test_detections_filter_class_and_threshold() -> None:
    frame = _frame()
    observed = datetime(2026, 9, 20, 12, 0, 1, tzinfo=UTC)
    rows = detections_to_observations(
        boxes=[
            (4, 2, 20, 18),
            (4, 2, 20, 18),
            (4, 2, 20, 18),
            (4, 2, 20, 18),
        ],
        labels=[COCO_PERSON_LABEL, 3, "person", 1],
        scores=[0.25, 0.99, 0.24, float("nan")],
        frame=frame,
        width=40,
        height=20,
        min_confidence=0.25,
        model_id="lab-ssdlite",
        model_version="test",
        camera_id="cam-a",
        observed_at=observed,
    )
    assert len(rows) == 1
    item = rows[0]
    assert item.object_class == PERSON_CLASS
    assert item.confidence == 0.25
    assert item.source_id == "clip.avi"
    assert item.camera_id == "cam-a"
    assert item.track_id is None
    assert item.media_timestamp == frame.captured_at
    assert item.observed_at == observed
    assert item.media_timestamp != item.observed_at
    assert item.is_synthetic is True
    assert item.mock_label == MOCK_SYNTHETIC_LABEL
    assert item.model_id == "lab-ssdlite"
    assert item.bounding_box == BoundingBox(x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.9)
    assert 0.0 <= item.bounding_box.x_min < item.bounding_box.x_max <= 1.0


def test_detections_preserve_nonsynthetic_frame_label() -> None:
    frame = _frame(is_synthetic=False, mock_label="unit-fixture")
    rows = detections_to_observations(
        boxes=[(0, 0, 10, 10)],
        labels=[1],
        scores=[0.9],
        frame=frame,
        width=40,
        height=20,
        min_confidence=0.25,
        model_id="lab-ssdlite",
        model_version="test",
    )
    assert rows[0].is_synthetic is False
    assert rows[0].mock_label == "unit-fixture"


def test_detections_reject_misaligned_outputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        detections_to_observations(
            boxes=[(0, 0, 1, 1)],
            labels=[1, 1],
            scores=[0.9],
            frame=_frame(),
            width=40,
            height=20,
            min_confidence=0.25,
            model_id="lab-ssdlite",
            model_version="test",
        )


def test_min_confidence_must_be_valid() -> None:
    with pytest.raises(ValueError, match="min_confidence"):
        detections_to_observations(
            boxes=[],
            labels=[],
            scores=[],
            frame=_frame(),
            width=40,
            height=20,
            min_confidence=1.5,
            model_id="lab-ssdlite",
            model_version="test",
        )
