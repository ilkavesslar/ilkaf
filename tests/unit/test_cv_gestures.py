from datetime import UTC, datetime, timedelta

from cv.gestures import GestureTracker, PoseCue, associate_cues, detect_wave, relative_x
from cv.observation import BoundingBox


def _at(seconds: float) -> datetime:
    return datetime(2026, 11, 13, 12, 0, tzinfo=UTC) + timedelta(seconds=seconds)


def _samples(values: list[tuple[float, float]]) -> list[tuple[datetime, float]]:
    return [(_at(moment), position) for moment, position in values]


def test_no_samples_is_not_a_wave() -> None:
    assert detect_wave([], _at(0)) is False


def test_one_hand_movement_is_not_a_wave() -> None:
    samples = _samples([(0, 0.20), (0.4, 0.55)])
    assert detect_wave(samples, _at(0.4)) is False


def test_repeated_side_to_side_motion_is_a_wave() -> None:
    samples = _samples([(0, 0.20), (0.4, 0.55), (0.8, 0.20), (1.2, 0.55)])
    assert detect_wave(samples, _at(1.2)) is True


def test_steady_drift_is_not_a_wave() -> None:
    samples = _samples([(0, 0.40), (0.4, 0.43), (0.8, 0.46), (1.2, 0.49)])
    assert detect_wave(samples, _at(1.2)) is False


def test_old_wave_clears() -> None:
    tracker = GestureTracker()
    values = [0.20, 0.55, 0.20, 0.55]
    for index, position in enumerate(values):
        moment = _at(index * 0.4)
        tracker.update(1, moment, position, None)
    assert tracker.waving(1, _at(1.2)) is True
    assert tracker.waving(1, _at(1.2 + 1.5)) is True
    assert tracker.waving(1, _at(1.2 + 1.6)) is False


def test_pose_stays_with_the_track_that_contains_it() -> None:
    left = BoundingBox(0.05, 0.10, 0.40, 0.90)
    right = BoundingBox(0.60, 0.10, 0.95, 0.90)
    cue = PoseCue(anchor=(0.22, 0.40), left_wrist=(0.10, 0.50), right_wrist=(0.30, 0.50))
    other = PoseCue(anchor=(0.75, 0.40), left_wrist=(0.70, 0.50), right_wrist=None)
    assigned = associate_cues([(1, left), (2, right)], [other, cue])
    assert assigned[1] is cue
    assert assigned[2] is other
    assert relative_x(0.30, left) is not None
    assert 0.0 < relative_x(0.30, left) < 1.0
