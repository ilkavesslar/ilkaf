from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.intelligence.contract import (
    KEYPOINT_COUNT,
    SCHEMA_VERSION,
    ActivityClass,
    Keypoint,
    KeypointName,
    PersonIntelligenceObservation,
    missing_keypoints,
)
from cv.observation import BoundingBox

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def _record(**overrides: object) -> PersonIntelligenceObservation:
    values: dict[str, object] = {
        "observation_id": uuid4(),
        "camera_id": "cam-a",
        "source_id": "file:demo.mp4",
        "timestamp": NOW,
        "local_track_id": "cam-a:t1",
        "bbox": BoundingBox(0.1, 0.2, 0.3, 0.9),
        "detection_confidence": 0.8,
        "keypoints": missing_keypoints(),
        "activity_class": ActivityClass.STANDING,
        "activity_confidence": 0.6,
        "activity_started_at": NOW - timedelta(seconds=2),
        "activity_duration_s": 2.0,
        "movement_state": "stationary",
        "tracking_status": "active",
        "model_versions": {"detector": "stub@0"},
    }
    values.update(overrides)
    return PersonIntelligenceObservation(**values)  # type: ignore[arg-type]


def test_schema_version_and_keypoint_order() -> None:
    assert SCHEMA_VERSION == "1.0.0"
    assert KEYPOINT_COUNT == 17
    assert KeypointName.NOSE == 0
    assert KeypointName.LEFT_SHOULDER == 5
    assert KeypointName.RIGHT_ANKLE == 16
    assert [member.value for member in KeypointName] == list(range(17))


def test_activity_classes_cover_required_set() -> None:
    assert {member.value for member in ActivityClass} == {
        "standing",
        "walking",
        "running",
        "sitting",
        "bending",
        "waving",
        "falling",
        "person_down",
        "unknown",
    }


def test_missing_keypoint_has_no_coordinates() -> None:
    point = Keypoint.missing()
    assert point.x is None and point.y is None
    assert point.visibility == 0.0
    assert not point.observed


def test_visible_keypoint_requires_coordinates() -> None:
    with pytest.raises(ValueError, match="visible keypoint"):
        Keypoint(x=None, y=None, confidence=0.9, visibility=0.9)


def test_keypoint_rejects_half_coordinates_and_out_of_range() -> None:
    with pytest.raises(ValueError, match="both"):
        Keypoint(x=0.5, y=None, confidence=0.0, visibility=0.0)
    with pytest.raises(ValueError):
        Keypoint(x=1.2, y=0.5, confidence=0.9, visibility=0.9)
    with pytest.raises(ValueError):
        Keypoint(x=0.5, y=0.5, confidence=1.5, visibility=0.9)


def test_round_trip_preserves_all_fields() -> None:
    keypoints = list(missing_keypoints())
    keypoints[KeypointName.NOSE] = Keypoint(x=0.2, y=0.25, confidence=0.9, visibility=0.95)
    record = _record(keypoints=tuple(keypoints), global_person_id="gp-abc", frame_id="12")
    restored = PersonIntelligenceObservation.from_dict(record.to_dict())
    assert restored == record
    assert restored.keypoints[KeypointName.NOSE].x == pytest.approx(0.2)
    assert restored.keypoints[KeypointName.LEFT_EYE].x is None


def test_to_dict_is_json_friendly() -> None:
    data = _record().to_dict()
    assert data["timestamp"] == NOW.isoformat()
    assert data["activity_class"] == "standing"
    assert isinstance(data["observation_id"], str)
    assert len(data["keypoints"]) == 17


def test_requires_exactly_seventeen_keypoints() -> None:
    with pytest.raises(ValueError, match="17"):
        _record(keypoints=missing_keypoints()[:16])


def test_unknown_activity_cannot_carry_confidence() -> None:
    with pytest.raises(ValueError, match="unknown"):
        _record(activity_class=ActivityClass.UNKNOWN, activity_confidence=0.4)


def test_activity_timing_must_be_paired_and_ordered() -> None:
    with pytest.raises(ValueError, match="together"):
        _record(activity_duration_s=None)
    with pytest.raises(ValueError, match="after"):
        _record(activity_started_at=NOW + timedelta(seconds=1))
    with pytest.raises(ValueError, match=">= 0"):
        _record(activity_duration_s=-1.0)


def test_rejects_naive_timestamp_and_bad_enums() -> None:
    with pytest.raises(ValueError, match="timezone"):
        _record(timestamp=datetime(2026, 11, 16, 12, 0))
    with pytest.raises(ValueError, match="tracking_status"):
        _record(tracking_status="gone")
    with pytest.raises(ValueError, match="movement_state"):
        _record(movement_state="sprinting")


def test_from_dict_rejects_missing_fields_instead_of_defaulting() -> None:
    data = _record().to_dict()
    del data["detection_confidence"]
    with pytest.raises(ValueError, match="detection_confidence"):
        PersonIntelligenceObservation.from_dict(data)


def test_from_dict_rejects_other_schema_versions() -> None:
    data = _record().to_dict()
    data["schema_version"] = "2.0.0"
    with pytest.raises(ValueError, match="schema_version"):
        PersonIntelligenceObservation.from_dict(data)


def test_synthetic_label_is_normalized() -> None:
    assert _record(is_synthetic=True, mock_label="").mock_label == MOCK_SYNTHETIC_LABEL
    assert _record(is_synthetic=False, mock_label=MOCK_SYNTHETIC_LABEL).mock_label == ""


def test_model_versions_are_copied_and_validated() -> None:
    versions = {"detector": "stub@0"}
    record = _record(model_versions=versions)
    versions["detector"] = "changed"
    assert record.model_versions == {"detector": "stub@0"}
    with pytest.raises(ValueError):
        _record(model_versions={"detector": " "})
