from datetime import UTC, datetime, timedelta

import pytest

from cv.identity import (
    AnonymousIdentityMatcher,
    AppearanceSignature,
    CameraTopology,
    CameraTransition,
    GlobalAnonymousPersonId,
    MatcherConfig,
    appearance_histogram,
)
from cv.observation import BoundingBox

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
FULL = BoundingBox(0.0, 0.0, 1.0, 1.0)
BOX = BoundingBox(0.3, 0.2, 0.5, 0.9)

RED = (0, 0, 220)
BLUE = (220, 0, 0)
GREEN = (0, 200, 0)
GREY = (120, 120, 120)


def _at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


def _image(top: tuple[int, int, int], bottom: tuple[int, int, int], size: int = 40) -> list:
    return [[top if y < size // 2 else bottom for _x in range(size)] for y in range(size)]


def _signature(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> AppearanceSignature:
    signature = appearance_histogram(_image(top, bottom), FULL)
    assert signature is not None
    return signature


def _see(
    matcher: AnonymousIdentityMatcher,
    camera: str,
    track: str,
    start: float,
    appearance: AppearanceSignature | None,
    frames: int = 3,
    box: BoundingBox = BOX,
):
    assignment = None
    for i in range(frames):
        assignment = matcher.observe(
            camera, track, _at(start + i * 0.2), box, appearance=appearance, confirmed=i >= 1
        )
    return assignment


def test_global_ids_are_anonymous_and_validated() -> None:
    first = GlobalAnonymousPersonId.new()
    assert str(first).startswith("gp-")
    assert first != GlobalAnonymousPersonId.new()
    with pytest.raises(ValueError):
        GlobalAnonymousPersonId("employee-42")


def test_histogram_similarity_separates_clothing_colours() -> None:
    red_blue = _signature(RED, BLUE)
    assert red_blue.similarity(_signature(RED, BLUE)) == pytest.approx(1.0)
    assert red_blue.similarity(_signature(GREEN, GREY)) < 0.3


def test_histogram_returns_none_for_unusable_input() -> None:
    assert appearance_histogram(b"not-an-image", FULL) is None
    assert appearance_histogram(_image(RED, BLUE, size=4), FULL) is None
    assert appearance_histogram([[(300, 0, 0)] * 40] * 40, FULL) is None
    with pytest.raises(ValueError):
        appearance_histogram(_image(RED, BLUE), FULL, bins=7)


def test_pending_until_confirmed() -> None:
    matcher = AnonymousIdentityMatcher()
    assignment = matcher.observe("cam-a", "cam-a:t1", _at(0), BOX, confirmed=False)
    assert assignment.status == "pending"
    assert assignment.global_person_id is None


def test_same_camera_reentry_with_same_clothing_matches() -> None:
    matcher = AnonymousIdentityMatcher()
    appearance = _signature(RED, BLUE)
    first = _see(matcher, "cam-a", "cam-a:t1", 0, appearance)
    matcher.end_track("cam-a", "cam-a:t1")
    second = _see(matcher, "cam-a", "cam-a:t2", 3, appearance)
    assert first.status == "new"
    assert second.status == "matched"
    assert second.global_person_id == first.global_person_id
    assert second.similarity is not None and second.similarity >= 0.8


def test_different_clothing_gets_new_id() -> None:
    matcher = AnonymousIdentityMatcher()
    first = _see(matcher, "cam-a", "cam-a:t1", 0, _signature(RED, BLUE))
    matcher.end_track("cam-a", "cam-a:t1")
    second = _see(matcher, "cam-a", "cam-a:t2", 3, _signature(GREEN, GREY))
    assert second.status == "new"
    assert second.global_person_id != first.global_person_id


def test_no_appearance_never_merges() -> None:
    matcher = AnonymousIdentityMatcher()
    first = _see(matcher, "cam-a", "cam-a:t1", 0, None)
    matcher.end_track("cam-a", "cam-a:t1")
    second = _see(matcher, "cam-a", "cam-a:t2", 1, None)
    assert second.status == "new"
    assert second.global_person_id != first.global_person_id


def test_cross_camera_requires_known_topology() -> None:
    appearance = _signature(RED, BLUE)
    matcher = AnonymousIdentityMatcher()
    _see(matcher, "cam-a", "cam-a:t1", 0, appearance)
    matcher.end_track("cam-a", "cam-a:t1")
    unknown_pair = _see(matcher, "cam-b", "cam-b:t1", 5, appearance)
    assert unknown_pair.status == "new"

    topology = CameraTopology({("cam-a", "cam-b"): CameraTransition(min_s=2, max_s=20)})
    linked = AnonymousIdentityMatcher(topology=topology)
    first = _see(linked, "cam-a", "cam-a:t1", 0, appearance)
    linked.end_track("cam-a", "cam-a:t1")
    second = _see(linked, "cam-b", "cam-b:t1", 5, appearance)
    assert second.status == "matched"
    assert second.global_person_id == first.global_person_id


def test_cross_camera_outside_transit_window_is_new() -> None:
    appearance = _signature(RED, BLUE)
    topology = CameraTopology({("cam-a", "cam-b"): CameraTransition(min_s=2, max_s=20)})
    matcher = AnonymousIdentityMatcher(topology=topology)
    _see(matcher, "cam-a", "cam-a:t1", 0, appearance)
    matcher.end_track("cam-a", "cam-a:t1")
    too_fast = _see(matcher, "cam-b", "cam-b:t1", 0.6, appearance)
    assert too_fast.status == "new"


def test_person_still_visible_cannot_be_matched_elsewhere() -> None:
    appearance = _signature(RED, BLUE)
    topology = CameraTopology({("cam-a", "cam-b"): CameraTransition(min_s=0, max_s=20)})
    matcher = AnonymousIdentityMatcher(topology=topology)
    first = _see(matcher, "cam-a", "cam-a:t1", 0, appearance)
    other = _see(matcher, "cam-b", "cam-b:t1", 1, appearance)
    assert other.global_person_id != first.global_person_id


def test_ambiguous_candidates_are_not_merged() -> None:
    appearance = _signature(RED, BLUE)
    matcher = AnonymousIdentityMatcher()
    left = BoundingBox(0.3, 0.2, 0.5, 0.9)
    right = BoundingBox(0.35, 0.2, 0.55, 0.9)
    a = _see(matcher, "cam-a", "cam-a:t1", 0, appearance, box=left)
    b = _see(matcher, "cam-a", "cam-a:t2", 0, appearance, box=right)
    matcher.end_track("cam-a", "cam-a:t1")
    matcher.end_track("cam-a", "cam-a:t2")
    third = _see(matcher, "cam-a", "cam-a:t3", 2, appearance, box=BoundingBox(0.32, 0.2, 0.52, 0.9))
    assert third.status == "uncertain"
    assert third.global_person_id not in (a.global_person_id, b.global_person_id)
    assert third.candidate_id in (a.global_person_id, b.global_person_id)
    assert third.similarity is not None


def test_id_decided_once_per_local_track() -> None:
    matcher = AnonymousIdentityMatcher()
    first = _see(matcher, "cam-a", "cam-a:t1", 0, _signature(RED, BLUE), frames=2)
    later = _see(matcher, "cam-a", "cam-a:t1", 1, _signature(GREEN, GREY), frames=3)
    assert later.global_person_id == first.global_person_id


def test_retention_prunes_old_people() -> None:
    matcher = AnonymousIdentityMatcher(MatcherConfig(retention_s=10))
    _see(matcher, "cam-a", "cam-a:t1", 0, _signature(RED, BLUE))
    matcher.end_track("cam-a", "cam-a:t1")
    assert matcher.known_people() == 1
    matcher.observe("cam-a", "cam-a:t9", _at(60), BOX, confirmed=False)
    assert matcher.known_people() == 0


def test_config_forbids_timing_only_matches() -> None:
    with pytest.raises(ValueError, match="timing"):
        MatcherConfig(appearance_weight=0.5, uncertain_threshold=0.4, match_threshold=0.8)
    with pytest.raises(ValueError):
        MatcherConfig(uncertain_threshold=0.9, match_threshold=0.8)
