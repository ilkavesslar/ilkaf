from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cv import tracking as base_tracking
from cv.intelligence.tracker import CameraScopedTracker, TrackerConfig
from cv.observation import BoundingBox, Observation

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def _at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


def _person(box: tuple[float, float, float, float], camera_id: str | None = "cam-a") -> Observation:
    return Observation(
        observation_id=uuid4(),
        source_id="file:demo.mp4",
        object_class="person",
        confidence=0.9,
        bounding_box=BoundingBox(*box),
        model_id="stub",
        model_version="0",
        observed_at=START,
        camera_id=camera_id,
    )


LEFT = (0.1, 0.2, 0.3, 0.9)
RIGHT = (0.7, 0.2, 0.9, 0.9)


def test_defaults_match_base_tracker_geometry() -> None:
    config = TrackerConfig()
    assert config.center_distance_max == base_tracking.CENTER_DISTANCE_MAX
    assert config.overlap_iou_min == base_tracking.OVERLAP_IOU_MIN
    assert config.overlap_distance_max == base_tracking.OVERLAP_DISTANCE_MAX
    assert config.missed_limit == base_tracking.MISSED_INFERENCE_LIMIT


@pytest.mark.parametrize(
    "kwargs",
    [
        {"missed_limit": 0},
        {"min_hits": 0},
        {"center_distance_max": 0.0},
        {"overlap_iou_min": 1.5},
        {"max_lost_s": 0.0},
        {"history_limit": 1},
    ],
)
def test_invalid_config_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        TrackerConfig(**kwargs)


def test_track_ids_are_camera_scoped() -> None:
    update = CameraScopedTracker("cam-a").update([_person(LEFT)], _at(0))
    assert update.tracks[0].local_track_id == "cam-a:t1"


def test_tentative_until_min_hits_then_active() -> None:
    tracker = CameraScopedTracker("cam-a", TrackerConfig(min_hits=3))
    statuses = [tracker.update([_person(LEFT)], _at(i * 0.2)).tracks[0].status for i in range(3)]
    assert statuses == ["tentative", "tentative", "active"]


def test_tentative_track_dropped_on_first_miss() -> None:
    tracker = CameraScopedTracker("cam-a")
    tracker.update([_person(LEFT)], _at(0))
    update = tracker.update([], _at(0.2))
    assert update.tracks == []
    assert update.removed == ["cam-a:t1"]


def test_active_track_goes_lost_then_removed_after_missed_limit() -> None:
    tracker = CameraScopedTracker("cam-a", TrackerConfig(missed_limit=2, max_lost_s=10))
    tracker.update([_person(LEFT)], _at(0))
    tracker.update([_person(LEFT)], _at(0.2))
    lost = tracker.update([], _at(0.4))
    assert [t.status for t in lost.tracks] == ["lost"]
    assert lost.tracks[0].matched_this_update is False
    gone = tracker.update([], _at(0.6))
    assert gone.tracks == [] and gone.removed == ["cam-a:t1"]


def test_lost_track_reacquired_keeps_id() -> None:
    tracker = CameraScopedTracker("cam-a")
    tracker.update([_person(LEFT)], _at(0))
    tracker.update([_person(LEFT)], _at(0.2))
    tracker.update([], _at(0.4))
    update = tracker.update([_person(LEFT)], _at(0.6))
    assert [(t.local_track_id, t.status) for t in update.tracks] == [("cam-a:t1", "active")]


def test_time_gap_expires_tracks_even_without_missed_updates() -> None:
    tracker = CameraScopedTracker("cam-a", TrackerConfig(max_lost_s=1.0))
    tracker.update([_person(LEFT)], _at(0))
    tracker.update([_person(LEFT)], _at(0.2))
    update = tracker.update([_person(LEFT)], _at(5.0))
    assert update.removed == ["cam-a:t1"]
    assert [t.local_track_id for t in update.tracks] == ["cam-a:t2"]


def test_ids_are_never_reused() -> None:
    tracker = CameraScopedTracker("cam-a")
    seen: list[str] = []
    for step in range(4):
        update = tracker.update([_person(LEFT if step % 2 == 0 else RIGHT)], _at(step * 3.0))
        seen.extend(t.local_track_id for t in update.tracks)
    assert len(seen) == len(set(seen))


def test_distance_threshold_is_configurable() -> None:
    near = (0.25, 0.2, 0.45, 0.9)
    strict = CameraScopedTracker(
        "cam-a",
        TrackerConfig(center_distance_max=0.05, overlap_iou_min=0.9, overlap_distance_max=0.05),
    )
    strict.update([_person(LEFT)], _at(0))
    assert [t.number for t in strict.update([_person(near)], _at(0.2)).tracks] == [2]
    loose = CameraScopedTracker("cam-a")
    loose.update([_person(LEFT)], _at(0))
    assert [t.number for t in loose.update([_person(near)], _at(0.2)).tracks] == [1]


def test_two_people_keep_separate_tracks() -> None:
    tracker = CameraScopedTracker("cam-a")
    tracker.update([_person(LEFT), _person(RIGHT)], _at(0))
    update = tracker.update([_person(RIGHT), _person(LEFT)], _at(0.2))
    by_id = {t.local_track_id: t.bbox.x_min for t in update.tracks}
    assert by_id == {"cam-a:t1": pytest.approx(0.1), "cam-a:t2": pytest.approx(0.7)}


def test_rejects_backwards_and_naive_timestamps() -> None:
    tracker = CameraScopedTracker("cam-a")
    tracker.update([], _at(1))
    with pytest.raises(ValueError, match="backwards"):
        tracker.update([], _at(0))
    with pytest.raises(ValueError, match="timezone"):
        tracker.update([], datetime(2026, 11, 16, 12, 0))


def test_rejects_observations_from_another_camera() -> None:
    with pytest.raises(ValueError, match="camera_id"):
        CameraScopedTracker("cam-a").update([_person(LEFT, camera_id="cam-b")], _at(0))


def test_history_window_and_limit_are_bounded() -> None:
    tracker = CameraScopedTracker("cam-a", TrackerConfig(history_limit=4, history_window_s=100))
    for step in range(10):
        update = tracker.update([_person(LEFT)], _at(step * 0.1))
    assert len(update.tracks[0].center_history) == 4
    windowed = CameraScopedTracker("cam-a", TrackerConfig(history_window_s=1.0, max_lost_s=5))
    for step in range(10):
        update = windowed.update([_person(LEFT)], _at(step * 0.5))
    history = update.tracks[0].center_history
    assert (history[-1][0] - history[0][0]).total_seconds() <= 1.0
