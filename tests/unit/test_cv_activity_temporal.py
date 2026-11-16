from datetime import UTC, datetime, timedelta

import pytest

from cv.activity import ActivityConfig, ActivityState, TemporalActivityRecognizer
from cv.intelligence.contract import ActivityClass, Keypoint, KeypointName, missing_keypoints
from cv.observation import BoundingBox

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
STEP = 0.2
TRACK = "cam-a:t1"

STANDING_BOX = BoundingBox(0.4, 0.2, 0.6, 0.95)
LYING_BOX = BoundingBox(0.2, 0.78, 0.7, 0.95)


def _at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


def _keypoints(points: dict[KeypointName, tuple[float, float]]) -> tuple[Keypoint, ...]:
    keypoints = list(missing_keypoints())
    for name, (x_pos, y_pos) in points.items():
        keypoints[name] = Keypoint(x=x_pos, y=y_pos, confidence=0.9, visibility=0.9)
    return tuple(keypoints)


UPRIGHT = _keypoints(
    {
        KeypointName.LEFT_SHOULDER: (0.45, 0.3),
        KeypointName.RIGHT_SHOULDER: (0.55, 0.3),
        KeypointName.LEFT_HIP: (0.46, 0.55),
        KeypointName.RIGHT_HIP: (0.54, 0.55),
        KeypointName.LEFT_KNEE: (0.46, 0.75),
        KeypointName.RIGHT_KNEE: (0.54, 0.75),
    }
)
SITTING = _keypoints(
    {
        KeypointName.LEFT_SHOULDER: (0.45, 0.3),
        KeypointName.RIGHT_SHOULDER: (0.55, 0.3),
        KeypointName.LEFT_HIP: (0.46, 0.55),
        KeypointName.RIGHT_HIP: (0.54, 0.55),
        KeypointName.LEFT_KNEE: (0.66, 0.57),
        KeypointName.RIGHT_KNEE: (0.72, 0.57),
    }
)
BENT = _keypoints(
    {
        KeypointName.LEFT_SHOULDER: (0.62, 0.45),
        KeypointName.RIGHT_SHOULDER: (0.64, 0.45),
        KeypointName.LEFT_HIP: (0.5, 0.55),
        KeypointName.RIGHT_HIP: (0.52, 0.55),
    }
)
LYING = _keypoints(
    {
        KeypointName.LEFT_SHOULDER: (0.3, 0.85),
        KeypointName.RIGHT_SHOULDER: (0.3, 0.87),
        KeypointName.LEFT_HIP: (0.55, 0.86),
        KeypointName.RIGHT_HIP: (0.55, 0.88),
    }
)


def _feed(
    recognizer: TemporalActivityRecognizer,
    frames: int,
    *,
    start: float = 0.0,
    box: BoundingBox = STANDING_BOX,
    keypoints: tuple[Keypoint, ...] | None = UPRIGHT,
    aspect: float | None = 1.0,
    waving: bool = False,
) -> list[ActivityState]:
    return [
        recognizer.update(
            TRACK,
            _at(start + i * STEP),
            box,
            keypoints=keypoints,
            waving=waving,
            image_aspect=aspect,
        )
        for i in range(frames)
    ]


def _classes(states: list[ActivityState]) -> list[ActivityClass]:
    return [state.activity_class for state in states]


def test_standing_needs_several_frames() -> None:
    states = _feed(TemporalActivityRecognizer(), 8)
    assert states[0].activity_class is ActivityClass.UNKNOWN
    assert states[0].confidence == 0.0
    assert states[-1].activity_class is ActivityClass.STANDING
    first_standing = _classes(states).index(ActivityClass.STANDING)
    assert first_standing >= 3
    assert states[-1].started_at is not None and states[-1].started_at < _at(7 * STEP)
    assert states[-1].duration_s is not None and states[-1].duration_s > 0
    assert 0.0 < states[-1].confidence <= 1.0


def test_sitting_from_thigh_geometry() -> None:
    states = _feed(TemporalActivityRecognizer(), 8, keypoints=SITTING)
    assert states[-1].activity_class is ActivityClass.SITTING


def test_bending_from_torso_angle() -> None:
    states = _feed(TemporalActivityRecognizer(), 8, keypoints=BENT)
    assert states[-1].activity_class is ActivityClass.BENDING


def _moving(
    recognizer: TemporalActivityRecognizer, per_step: float, height: float
) -> list[ActivityState]:
    states = []
    for i in range(10):
        x_min = 0.05 + i * per_step
        box = BoundingBox(x_min, 0.5, x_min + 0.1, 0.5 + height)
        states.append(
            recognizer.update(TRACK, _at(i * STEP), box, keypoints=None, image_aspect=1.0)
        )
    return states


def test_walking_and_running_from_body_height_speed() -> None:
    walking = _moving(TemporalActivityRecognizer(), per_step=0.03, height=0.4)
    assert walking[-1].activity_class is ActivityClass.WALKING
    running = _moving(TemporalActivityRecognizer(), per_step=0.08, height=0.2)
    assert running[-1].activity_class is ActivityClass.RUNNING


def test_waving_cue_becomes_waving() -> None:
    states = _feed(TemporalActivityRecognizer(), 8, waving=True)
    assert states[-1].activity_class is ActivityClass.WAVING


def test_fall_is_a_temporal_transition_then_person_down() -> None:
    recognizer = TemporalActivityRecognizer()
    standing = _feed(recognizer, 8)
    assert standing[-1].activity_class is ActivityClass.STANDING
    down = _feed(recognizer, 20, start=8 * STEP, box=LYING_BOX, keypoints=LYING)
    classes = _classes(down)
    assert classes[0] is ActivityClass.STANDING
    assert classes[1] is ActivityClass.STANDING
    assert ActivityClass.FALLING in classes
    falling_at = classes.index(ActivityClass.FALLING)
    assert falling_at >= 2
    assert classes[-1] is ActivityClass.PERSON_DOWN
    down_at = classes.index(ActivityClass.PERSON_DOWN)
    assert down_at > falling_at
    assert down[down_at].started_at == _at(8 * STEP)
    assert (down[down_at].duration_s or 0) >= ActivityConfig().person_down_s


def test_single_down_frame_never_alarms() -> None:
    recognizer = TemporalActivityRecognizer()
    _feed(recognizer, 8)
    glitch = recognizer.update(TRACK, _at(8 * STEP), LYING_BOX, keypoints=LYING, image_aspect=1.0)
    after = _feed(recognizer, 10, start=9 * STEP)
    seen = {glitch.activity_class, *_classes(after)}
    assert ActivityClass.FALLING not in seen
    assert ActivityClass.PERSON_DOWN not in seen


def test_already_down_is_person_down_without_falling() -> None:
    recognizer = TemporalActivityRecognizer()
    states = _feed(recognizer, 20, box=LYING_BOX, keypoints=LYING)
    classes = _classes(states)
    assert ActivityClass.FALLING not in classes
    assert classes[-1] is ActivityClass.PERSON_DOWN
    first = classes.index(ActivityClass.PERSON_DOWN)
    assert first * STEP >= ActivityConfig().person_down_s


def test_bbox_aspect_fallback_without_keypoints() -> None:
    states = _feed(TemporalActivityRecognizer(), 20, box=LYING_BOX, keypoints=None)
    assert states[-1].activity_class is ActivityClass.PERSON_DOWN
    assert states[-1].confidence < 0.6


def test_exit_from_person_down_is_sticky() -> None:
    recognizer = TemporalActivityRecognizer()
    _feed(recognizer, 20, box=LYING_BOX, keypoints=LYING)
    up = _feed(recognizer, 12, start=20 * STEP)
    classes = _classes(up)
    exit_frames = int(ActivityConfig().exit_down_s / STEP)
    assert all(c is ActivityClass.PERSON_DOWN for c in classes[:exit_frames])
    assert classes[-1] is ActivityClass.STANDING


def test_without_geometry_or_motion_stays_unknown() -> None:
    states = _feed(TemporalActivityRecognizer(), 10, aspect=None)
    assert all(state.activity_class is ActivityClass.UNKNOWN for state in states)
    assert all(state.started_at is None for state in states)


def test_noisy_alternation_does_not_flip_class() -> None:
    recognizer = TemporalActivityRecognizer()
    _feed(recognizer, 8)
    classes = []
    for i in range(10):
        keypoints = BENT if i % 2 == 0 else UPRIGHT
        state = recognizer.update(
            TRACK, _at((8 + i) * STEP), STANDING_BOX, keypoints=keypoints, image_aspect=1.0
        )
        classes.append(state.activity_class)
    assert set(classes) == {ActivityClass.STANDING}


def test_tracks_are_independent_and_forgettable() -> None:
    recognizer = TemporalActivityRecognizer()
    _feed(recognizer, 8)
    other = recognizer.update(
        "cam-a:t2", _at(2.0), STANDING_BOX, keypoints=UPRIGHT, image_aspect=1.0
    )
    assert other.activity_class is ActivityClass.UNKNOWN
    recognizer.retain({"cam-a:t2"})
    fresh = recognizer.update(TRACK, _at(3.0), STANDING_BOX, keypoints=UPRIGHT, image_aspect=1.0)
    assert fresh.activity_class is ActivityClass.UNKNOWN


def test_rejects_backwards_time_and_bad_inputs() -> None:
    recognizer = TemporalActivityRecognizer()
    recognizer.update(TRACK, _at(1), STANDING_BOX, image_aspect=1.0)
    with pytest.raises(ValueError, match="backwards"):
        recognizer.update(TRACK, _at(0), STANDING_BOX, image_aspect=1.0)
    with pytest.raises(ValueError, match="17"):
        recognizer.update(TRACK, _at(2), STANDING_BOX, keypoints=UPRIGHT[:5])
    with pytest.raises(ValueError, match="image_aspect"):
        recognizer.update(TRACK, _at(2), STANDING_BOX, image_aspect=0.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"walk_speed_bh": 2.0, "run_speed_bh": 1.0},
        {"min_frames": 1},
        {"fall_confirm_frames": 1},
        {"person_down_s": 0.0},
        {"history_s": 1.0},
    ],
)
def test_invalid_config_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        ActivityConfig(**kwargs)
