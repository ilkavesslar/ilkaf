from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.observation import BoundingBox, Observation


def _box() -> BoundingBox:
    return BoundingBox(x_min=0.1, y_min=0.2, x_max=0.4, y_max=0.8)


def _observation(**overrides: object) -> Observation:
    values: dict[str, object] = {
        "observation_id": uuid4(),
        "source_id": "test-file.avi",
        "object_class": "person",
        "confidence": 0.91,
        "bounding_box": _box(),
        "model_id": "ilka-placeholder-detector",
        "model_version": "0.0.0-test",
        "observed_at": datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return Observation(**values)  # type: ignore[arg-type]


def test_valid_observation_with_optional_fields() -> None:
    media = datetime(2026, 9, 20, 11, 59, 50, tzinfo=UTC)
    observed = datetime(2026, 9, 20, 12, 0, 1, tzinfo=UTC)
    box = _box()
    observation_id = uuid4()
    observation = Observation(
        observation_id=observation_id,
        source_id="clip.avi",
        object_class="hard_hat",
        confidence=0.0,
        bounding_box=box,
        model_id="ilka-placeholder-detector",
        model_version="0.0.0-test",
        observed_at=observed,
        camera_id="cam-line-04",
        track_id="trk-1",
        media_timestamp=media,
    )
    assert observation.observation_id == observation_id
    assert observation.source_id == "clip.avi"
    assert observation.camera_id == "cam-line-04"
    assert observation.object_class == "hard_hat"
    assert observation.confidence == 0.0
    assert observation.bounding_box is box
    assert observation.model_id == "ilka-placeholder-detector"
    assert observation.model_version == "0.0.0-test"
    assert observation.track_id == "trk-1"
    assert observation.media_timestamp == media
    assert observation.observed_at == observed
    assert observation.media_timestamp != observation.observed_at
    assert observation.is_synthetic is True
    assert observation.mock_label == MOCK_SYNTHETIC_LABEL
    assert Observation.__doc__ is not None
    assert "not" in Observation.__doc__.lower()
    assert "incident" in Observation.__doc__.lower()


def test_missing_optional_fields_default_none() -> None:
    observation = _observation()
    assert observation.camera_id is None
    assert observation.track_id is None
    assert observation.media_timestamp is None
    assert observation.observed_at.tzinfo is not None
    assert observation.is_synthetic is True
    assert observation.mock_label == MOCK_SYNTHETIC_LABEL


def test_confidence_endpoints_are_valid() -> None:
    low = _observation(confidence=0.0)
    high = _observation(confidence=1.0)
    assert low.confidence == 0.0
    assert high.confidence == 1.0


@pytest.mark.parametrize(
    "confidence",
    [-0.01, 1.01, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_confidence_rejected(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        _observation(confidence=confidence)


def test_confidence_rejects_bool() -> None:
    with pytest.raises(TypeError, match="confidence"):
        _observation(confidence=True)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"x_min": -0.1, "y_min": 0.0, "x_max": 0.5, "y_max": 0.5}, "x_min"),
        ({"x_min": 0.0, "y_min": 1.1, "x_max": 0.5, "y_max": 0.5}, "y_min"),
        ({"x_min": 0.2, "y_min": 0.0, "x_max": 0.2, "y_max": 0.5}, "x_max"),
        ({"x_min": 0.0, "y_min": 0.4, "x_max": 0.5, "y_max": 0.1}, "y_max"),
        ({"x_min": 0.0, "y_min": 0.0, "x_max": 1.01, "y_max": 0.5}, "x_max"),
        ({"x_min": 0.0, "y_min": 0.0, "x_max": 0.5, "y_max": float("nan")}, "y_max"),
        ({"x_min": float("inf"), "y_min": 0.0, "x_max": 0.5, "y_max": 0.5}, "x_min"),
        ({"x_min": 0.0, "y_min": float("-inf"), "x_max": 0.5, "y_max": 0.5}, "y_min"),
    ],
)
def test_invalid_bounding_box_rejected(kwargs: dict[str, float], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        BoundingBox(**kwargs)


def test_bounding_box_unit_square_is_valid() -> None:
    box = BoundingBox(x_min=0.0, y_min=0.0, x_max=1.0, y_max=1.0)
    assert box.x_min == 0.0
    assert box.y_max == 1.0


def test_observation_rejects_invalid_id_and_box_types() -> None:
    with pytest.raises(TypeError, match="observation_id"):
        _observation(observation_id="not-a-uuid")
    with pytest.raises(TypeError, match="bounding_box"):
        _observation(bounding_box=(0.1, 0.2, 0.3, 0.4))


def test_empty_optional_identifiers_rejected() -> None:
    with pytest.raises(ValueError, match="camera_id"):
        _observation(camera_id="  ")
    with pytest.raises(ValueError, match="track_id"):
        _observation(track_id="")


def test_synthetic_and_nonsynthetic_labels_cannot_contradict() -> None:
    synthetic = _observation()
    assert synthetic.is_synthetic is True
    assert synthetic.mock_label == MOCK_SYNTHETIC_LABEL

    forced = _observation(is_synthetic=True, mock_label="other")
    assert forced.mock_label == MOCK_SYNTHETIC_LABEL

    cleared = _observation(is_synthetic=False)
    assert cleared.is_synthetic is False
    assert cleared.mock_label == ""

    tagged = _observation(is_synthetic=False, mock_label="unit-fixture")
    assert tagged.mock_label == "unit-fixture"


def test_media_timestamp_is_optional_and_distinct_from_observed_at() -> None:
    observed = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    without_media = _observation(observed_at=observed)
    assert without_media.media_timestamp is None
    assert without_media.observed_at == observed

    media = observed - timedelta(milliseconds=250)
    with_media = _observation(observed_at=observed, media_timestamp=media)
    assert with_media.media_timestamp == media
    assert with_media.observed_at == observed
    assert with_media.media_timestamp < with_media.observed_at


def test_naive_timestamps_rejected() -> None:
    naive = datetime(2026, 9, 20, 12, 0)  # noqa: DTZ001
    with pytest.raises(ValueError, match="observed_at"):
        _observation(observed_at=naive)
    with pytest.raises(ValueError, match="media_timestamp"):
        _observation(media_timestamp=naive)


def test_non_utc_aware_timestamps_are_normalized() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    observed = datetime(2026, 9, 20, 17, 30, tzinfo=offset)
    media = datetime(2026, 9, 20, 17, 29, tzinfo=offset)
    observation = _observation(observed_at=observed, media_timestamp=media)
    assert observation.observed_at == datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    assert observation.media_timestamp == datetime(2026, 9, 20, 11, 59, tzinfo=UTC)
    assert observation.observed_at.tzinfo == UTC
    assert observation.media_timestamp is not None
    assert observation.media_timestamp.tzinfo == UTC


def test_empty_required_strings_rejected() -> None:
    with pytest.raises(ValueError, match="source_id"):
        _observation(source_id="  ")
    with pytest.raises(ValueError, match="object_class"):
        _observation(object_class="")
    with pytest.raises(ValueError, match="model_id"):
        _observation(model_id=" ")
    with pytest.raises(ValueError, match="model_version"):
        _observation(model_version="")
