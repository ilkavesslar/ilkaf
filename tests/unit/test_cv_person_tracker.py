from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cv.observation import BoundingBox, Observation
from cv.tracking import CENTER_HISTORY_LIMIT, MISSED_INFERENCE_LIMIT, PersonTracker


def _person(
    box: tuple[float, float, float, float],
    *,
    when: datetime,
    confidence: float = 0.9,
) -> Observation:
    x_min, y_min, x_max, y_max = box
    return Observation(
        observation_id=uuid4(),
        source_id="webcam:0",
        object_class="person",
        confidence=confidence,
        bounding_box=BoundingBox(x_min, y_min, x_max, y_max),
        model_id="test-detector",
        model_version="0",
        observed_at=when,
        track_id=None,
        is_synthetic=True,
    )


def _when(step: int) -> datetime:
    return datetime(2026, 11, 12, 12, 0, tzinfo=UTC) + timedelta(seconds=step)


def test_first_person_creates_track_one() -> None:
    moment = _when(0)
    tracks = PersonTracker().update([_person((0.2, 0.2, 0.4, 0.8), when=moment)], moment)
    assert [track.track_id for track in tracks] == [1]
    assert tracks[0].missed_inferences == 0
    assert tracks[0].last_center[0] == pytest.approx(0.3)
    assert tracks[0].last_center[1] == pytest.approx(0.5)
    assert tracks[0].center_history[0][0] == moment
    assert tracks[0].center_history[0][1] == pytest.approx(0.3)
    assert tracks[0].center_history[0][2] == pytest.approx(0.5)
    assert tracks[0].latest_observation.track_id is None


def test_nearby_detection_keeps_the_same_track() -> None:
    tracker = PersonTracker()
    first = _when(0)
    second = _when(1)
    tracker.update([_person((0.20, 0.20, 0.40, 0.80), when=first)], first)
    tracks = tracker.update([_person((0.24, 0.22, 0.44, 0.82), when=second)], second)
    assert [track.track_id for track in tracks] == [1]
    assert tracks[0].missed_inferences == 0
    assert len(tracks[0].center_history) == 2
    assert tracks[0].center_history[-1][0] == second


def test_two_people_keep_separate_ids() -> None:
    tracker = PersonTracker()
    first = _when(0)
    tracker.update(
        [
            _person((0.05, 0.20, 0.25, 0.80), when=first, confidence=0.94),
            _person((0.70, 0.20, 0.90, 0.80), when=first, confidence=0.88),
        ],
        first,
    )
    second = _when(1)
    tracks = tracker.update(
        [
            _person((0.72, 0.22, 0.92, 0.82), when=second, confidence=0.80),
            _person((0.08, 0.22, 0.28, 0.82), when=second, confidence=0.91),
        ],
        second,
    )
    assert [track.track_id for track in tracks] == [1, 2]
    by_id = {track.track_id: track for track in tracks}
    assert by_id[1].last_center[0] < 0.3
    assert by_id[2].last_center[0] > 0.7
    assert by_id[1].latest_observation.confidence == 0.91
    assert by_id[2].latest_observation.confidence == 0.80


def test_one_missed_inference_keeps_the_track() -> None:
    tracker = PersonTracker()
    moment = _when(0)
    tracker.update([_person((0.2, 0.2, 0.4, 0.8), when=moment)], moment)
    tracks = tracker.update([], _when(1))
    assert [track.track_id for track in tracks] == [1]
    assert tracks[0].missed_inferences == 1


def test_track_expires_after_three_missed_inferences() -> None:
    tracker = PersonTracker()
    moment = _when(0)
    tracker.update([_person((0.2, 0.2, 0.4, 0.8), when=moment)], moment)
    alive = tracker.update([], _when(1))
    assert alive[0].missed_inferences == 1
    still = tracker.update([], _when(2))
    assert still[0].missed_inferences == 2
    expired = tracker.update([], _when(3))
    assert expired == []
    assert MISSED_INFERENCE_LIMIT == 3


def test_expired_id_is_not_reused() -> None:
    tracker = PersonTracker()
    moment = _when(0)
    tracker.update([_person((0.2, 0.2, 0.4, 0.8), when=moment)], moment)
    for step in range(1, 4):
        tracker.update([], _when(step))
    tracks = tracker.update([_person((0.2, 0.2, 0.4, 0.8), when=_when(4))], _when(4))
    assert [track.track_id for track in tracks] == [2]


def test_empty_inference_creates_no_tracks() -> None:
    assert PersonTracker().update([], _when(0)) == []


def test_two_detections_cannot_share_one_track() -> None:
    tracker = PersonTracker()
    moment = _when(0)
    tracker.update([_person((0.40, 0.20, 0.60, 0.80), when=moment)], moment)
    tracks = tracker.update(
        [
            _person((0.42, 0.20, 0.62, 0.80), when=_when(1)),
            _person((0.55, 0.20, 0.75, 0.80), when=_when(1)),
        ],
        _when(1),
    )
    assert sorted(track.track_id for track in tracks) == [1, 2]
    holders = [track.track_id for track in tracks if abs(track.last_center[0] - 0.52) < 0.02]
    assert holders == [1]


def test_far_detection_opens_a_new_track() -> None:
    tracker = PersonTracker()
    moment = _when(0)
    tracker.update([_person((0.00, 0.20, 0.20, 0.80), when=moment)], moment)
    tracks = tracker.update([_person((0.80, 0.20, 1.00, 0.80), when=_when(1))], _when(1))
    by_id = {track.track_id: track for track in tracks}
    assert sorted(by_id) == [1, 2]
    assert by_id[1].missed_inferences == 1
    assert by_id[1].last_center[0] == pytest.approx(0.1)
    assert by_id[2].last_center[0] == pytest.approx(0.9)
    assert by_id[2].missed_inferences == 0


def test_center_history_keeps_the_latest_eight_points() -> None:
    tracker = PersonTracker()
    for step in range(CENTER_HISTORY_LIMIT + 1):
        shift = step * 0.01
        moment = _when(step)
        tracks = tracker.update(
            [_person((0.10 + shift, 0.20, 0.30 + shift, 0.80), when=moment)],
            moment,
        )
    history = tracks[0].center_history
    assert len(history) == CENTER_HISTORY_LIMIT
    assert history[0][0] == _when(1)
    assert history[-1][0] == _when(CENTER_HISTORY_LIMIT)
