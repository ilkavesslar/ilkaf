from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cv.intelligence.contract import (
    ActivityClass,
    PersonIntelligenceObservation,
    missing_keypoints,
)
from cv.observation import BoundingBox

from app.services.detection_state import intelligence_to_live_observation


def test_intelligence_to_live_observation_maps_public_fields() -> None:
    item = PersonIntelligenceObservation(
        observation_id=uuid4(),
        camera_id="cam-a",
        source_id="cam-a",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        local_track_id="cam-a:t3",
        bbox=BoundingBox(0.1, 0.2, 0.4, 0.8),
        detection_confidence=0.91,
        keypoints=missing_keypoints(),
        activity_class=ActivityClass.WALKING,
        activity_confidence=0.7,
        movement_state="moving",
        tracking_status="active",
        model_versions={"detector": "ssdlite"},
        global_person_id="anon-12345678",
        is_synthetic=True,
    )
    live = intelligence_to_live_observation(item, "cam-a")
    assert live.track_id == 3
    assert live.local_track_id == "cam-a:t3"
    assert live.activity_class == "walking"
    assert live.moving is True
    assert live.global_person_id == "anon-12345678"
    assert live.schema_version == "1.0.0"
    assert len(live.keypoints) == 17
