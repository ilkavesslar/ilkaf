from datetime import UTC, datetime, timedelta

from cv.movement import classify_movement


def _at(seconds: float) -> datetime:
    return datetime(2026, 11, 13, 12, 0, tzinfo=UTC) + timedelta(seconds=seconds)


def _history(points: list[tuple[float, float, float]]) -> list[tuple[datetime, float, float]]:
    return [(_at(moment), x_pos, y_pos) for moment, x_pos, y_pos in points]


def test_empty_history_is_not_moving() -> None:
    assert classify_movement([]) == "unknown"


def test_insufficient_history_is_not_moving() -> None:
    short = _history([(0, 0.2, 0.5), (1.5, 0.8, 0.5)])
    assert classify_movement(short) == "unknown"


def test_jitter_is_not_moving() -> None:
    history = _history(
        [(0, 0.50, 0.50), (1, 0.53, 0.50), (2, 0.50, 0.50), (3, 0.53, 0.50)]
    )
    assert classify_movement(history) == "stationary"


def test_minor_shift_is_not_moving() -> None:
    history = _history([(0, 0.40, 0.50), (1, 0.43, 0.51), (2, 0.46, 0.50)])
    assert classify_movement(history) == "stationary"


def test_sustained_movement_is_moving() -> None:
    history = _history([(0, 0.10, 0.50), (1, 0.35, 0.50), (2, 0.60, 0.50)])
    assert classify_movement(history) == "moving"


def test_timestamps_change_the_classification() -> None:
    fast = _history([(0, 0.10, 0.50), (1, 0.35, 0.50), (2, 0.60, 0.50)])
    slow = _history([(0, 0.10, 0.50), (4, 0.35, 0.50), (8, 0.60, 0.50)])
    assert classify_movement(fast) == "moving"
    assert classify_movement(slow) == "stationary"


def test_dead_band_keeps_the_previous_state() -> None:
    history = _history([(0, 0.10, 0.50), (1, 0.25, 0.50), (2, 0.40, 0.50)])
    assert classify_movement(history, previous="moving") == "moving"
    assert classify_movement(history, previous="stationary") == "stationary"
    assert classify_movement(history) == "stationary"


def test_moving_clears_after_the_person_stops() -> None:
    moving = _history([(0, 0.10, 0.50), (1, 0.35, 0.50), (2, 0.60, 0.50)])
    assert classify_movement(moving) == "moving"
    stopped = _history(
        [
            (0, 0.10, 0.50),
            (1, 0.35, 0.50),
            (2, 0.60, 0.50),
            (3, 0.61, 0.50),
            (4, 0.60, 0.51),
        ]
    )
    assert classify_movement(stopped, previous="moving") == "stationary"


def test_results_do_not_name_a_posture() -> None:
    samples = [
        [],
        _history([(0, 0.40, 0.50), (1, 0.41, 0.50), (2, 0.42, 0.50)]),
        _history([(0, 0.10, 0.50), (1, 0.35, 0.50), (2, 0.60, 0.50)]),
    ]
    for history in samples:
        assert classify_movement(history) in {"unknown", "stationary", "moving"}


def test_zero_elapsed_time_is_unknown() -> None:
    moment = _at(0)
    history = [(moment, 0.1, 0.5), (moment, 0.4, 0.5), (moment, 0.7, 0.5)]
    assert classify_movement(history) == "unknown"
