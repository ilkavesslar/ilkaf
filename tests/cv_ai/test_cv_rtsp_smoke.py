"""Opt-in local RTSP smoke. The publisher content is ``[MOCK / SYNTHETIC]``.

``RtspSource`` marks RTSP frames non-synthetic because the transport is a
live stream, not a file fixture. That flag does not mean the pixels came
from a factory camera. This test does not start a publisher and does not
accept a URL with userinfo, so a failure cannot echo camera credentials.
"""

from __future__ import annotations

import os

import pytest

from cv.streams.base import VideoSource
from cv.streams.rtsp import RtspSource


def _smoke_url() -> str:
    url = os.environ.get("ILKA_RTSP_SMOKE_URL", "").strip()
    if not url:
        pytest.skip("ILKA_RTSP_SMOKE_URL is not set; local RTSP publisher smoke is opt-in")
    if "@" in url or not url.lower().startswith(("rtsp://", "rtsps://")):
        pytest.fail("ILKA_RTSP_SMOKE_URL must be a credential-free rtsp or rtsps URL")
    return url


def test_local_rtsp_publisher_smoke() -> None:
    url = _smoke_url()
    np = pytest.importorskip("numpy")
    source = RtspSource(
        url,
        source_id="rtsp-smoke-local",
        open_timeout_ms=5_000,
        read_timeout_ms=5_000,
        max_reconnect_attempts=2,
        retry_delay_s=0.5,
    )
    assert isinstance(source, VideoSource)
    frames = []
    try:
        source.open()
        for _ in range(2):
            frame = source.read()
            assert frame is not None
            frames.append(frame)
        assert len(frames) == 2
        assert frames[0].data is not frames[1].data
        held = frames[0].data.copy()
        for frame, index in zip(frames, (0, 1), strict=True):
            assert frame.index == index
            assert frame.source_id == "rtsp-smoke-local"
            assert frame.source_kind == "rtsp"
            assert frame.is_synthetic is False
            assert frame.mock_label == ""
            assert frame.captured_at.tzinfo is not None
            assert frame.processed_at.tzinfo is not None
            image = np.asarray(frame.data)
            assert image.ndim == 3
            assert image.shape[0] > 0
            assert image.shape[1] > 0
            assert image.shape[2] >= 3
            assert image.dtype == np.uint8
            assert int(image.size) > 0
        assert np.array_equal(frames[0].data, held)
    finally:
        source.close()
        source.close()

    follow_up = RtspSource(
        url,
        source_id="rtsp-smoke-local-reopen",
        open_timeout_ms=5_000,
        read_timeout_ms=5_000,
        max_reconnect_attempts=1,
        retry_delay_s=0.25,
    )
    try:
        follow_up.open()
        again = follow_up.read()
        assert again is not None
        assert int(np.asarray(again.data).shape[2]) >= 3
    finally:
        follow_up.close()
        follow_up.close()
