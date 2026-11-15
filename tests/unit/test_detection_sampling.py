from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.services.detection_state import (
    get_detection_state,
    record_person_sample,
    to_live_observation,
)

from cv.frame import Frame
from cv.observation import BoundingBox, Observation
from cv.sampling import InferenceClock


def _frame() -> Frame:
    now = datetime(2026, 11, 8, tzinfo=UTC)
    return Frame(
        data=b"frame",
        index=0,
        captured_at=now,
        processed_at=now,
        source_id="camera-1",
    )


def _observation() -> Observation:
    return Observation(
        observation_id=uuid4(),
        source_id="camera-1",
        object_class="person",
        confidence=0.5,
        bounding_box=BoundingBox(0.1, 0.2, 0.4, 0.8),
        model_id="torchvision-ssdlite320-mobilenet-v3-large",
        model_version="local",
        observed_at=datetime(2026, 11, 8, tzinfo=UTC),
    )


def test_public_observation_omits_model_and_stream_details() -> None:
    item = to_live_observation(_observation(), "camera-1")
    payload = item.model_dump()
    assert set(payload) == {
        "observation_id",
        "camera_id",
        "object_class",
        "confidence",
        "bounding_box",
        "observed_at",
        "track_id",
        "moving",
        "waving",
    }
    assert payload["track_id"] is None
    assert payload["moving"] is False
    assert payload["waving"] is False
    assert payload["bounding_box"] == {"x_min": 0.1, "y_min": 0.2, "x_max": 0.4, "y_max": 0.8}
    assert "model" not in payload


class _Detector:
    model_id = "stub"
    model_version = "0"
    calls = 0

    def detect(self, frame: Frame) -> list[Observation]:
        del frame
        self.calls += 1
        return [_observation()]


def test_sampler_skips_frames_inside_the_interval() -> None:
    get_detection_state().clear()
    detector = _Detector()
    clock = InferenceClock(10)
    assert record_person_sample(detector, _frame(), "camera-1", clock, 100) is True
    assert record_person_sample(detector, _frame(), "camera-1", clock, 105) is False
    assert detector.calls == 1
    stored = get_detection_state().read("camera-1")
    assert stored is not None
    assert stored.status == "ready"
    assert len(stored.items) == 1
    assert stored.items[0].object_class == "person"
    assert record_person_sample(detector, _frame(), "camera-1", clock, 110) is True
    assert detector.calls == 2
    get_detection_state().clear()
