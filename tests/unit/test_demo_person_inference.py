"""Real 30-frame MP4 check. Skips only when the local video or weights file is absent."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.services.demo_observations import demo_video_path, demo_weights_path, execute_demo_run


def test_local_mp4_person_observations_match_the_contract(tmp_path: Path) -> None:
    video = demo_video_path()
    weights = demo_weights_path()
    if not video.is_file() or not weights.is_file():
        pytest.skip("local demo video or weights file is missing")
    snapshot = execute_demo_run(
        tmp_path / "demo.json",
        max_frames=30,
        video_path=video,
        weights_path=weights,
    )
    assert snapshot.demo_status == "ready"
    assert snapshot.source_status == "local_mp4_demo"
    assert snapshot.source_kind == "file"
    assert snapshot.source_id == video.name
    assert snapshot.is_synthetic is True
    assert snapshot.mock_label == "[MOCK / SYNTHETIC]"
    assert snapshot.frames_processed == 30
    assert snapshot.model_id == "torchvision-ssdlite320-mobilenet-v3-large"
    assert snapshot.model_version
    assert snapshot.observations
    confidences = [item.confidence for item in snapshot.observations]
    assert min(confidences) >= 0.0
    assert max(confidences) <= 1.0
    for item in snapshot.observations:
        assert item.object_class == "person"
        assert item.is_synthetic is True
        assert item.mock_label == "[MOCK / SYNTHETIC]"
        assert item.source_id == video.name
        assert item.model_id == snapshot.model_id
        assert item.model_version == snapshot.model_version
        box = item.bounding_box
        assert 0.0 <= box.x_min < box.x_max <= 1.0
        assert 0.0 <= box.y_min < box.y_max <= 1.0
        assert item.media_timestamp is not None
        assert item.observed_at.tzinfo is not None
