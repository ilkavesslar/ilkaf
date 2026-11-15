from datetime import UTC, datetime

import pytest

from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
from cv.streams.buffer import BoundedFrameBuffer


def _frame(index: int, **overrides: object) -> Frame:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "data": b"synthetic",
        "index": index,
        "captured_at": now,
        "processed_at": now,
        "source_id": "test-file",
    }
    values.update(overrides)
    return Frame(**values)  # type: ignore[arg-type]


def test_buffer_rejects_non_positive_maxsize() -> None:
    with pytest.raises(ValueError, match="maxsize"):
        BoundedFrameBuffer(0)
    with pytest.raises(ValueError, match="maxsize"):
        BoundedFrameBuffer(-1)


def test_buffer_maxsize_one_drops_oldest() -> None:
    buffer = BoundedFrameBuffer(1)
    buffer.push(_frame(0))
    buffer.push(_frame(1))
    assert len(buffer) == 1
    assert buffer.dropped == 1
    held = buffer.pop()
    assert held is not None and held.index == 1


def test_buffer_clear_keeps_drop_counter() -> None:
    buffer = BoundedFrameBuffer(1)
    buffer.push(_frame(0))
    buffer.push(_frame(1))
    buffer.clear()
    assert len(buffer) == 0
    assert buffer.dropped == 1
    assert buffer.pop() is None


def test_buffer_drop_oldest() -> None:
    buffer = BoundedFrameBuffer(2)
    buffer.push(_frame(0))
    buffer.push(_frame(1))
    buffer.push(_frame(2))
    assert len(buffer) == 2
    assert buffer.dropped == 1
    first = buffer.pop()
    second = buffer.pop()
    assert first is not None and first.index == 1
    assert second is not None and second.index == 2
    assert buffer.pop() is None


def test_frame_is_labeled_synthetic() -> None:
    frame = _frame(0)
    assert frame.is_synthetic is True
    assert frame.mock_label == MOCK_SYNTHETIC_LABEL
    assert frame.source_kind == "file"
    assert frame.captured_at.tzinfo is not None
    assert frame.processed_at.tzinfo is not None


def test_nonsynthetic_frame_does_not_keep_synthetic_label() -> None:
    defaulted = _frame(0, is_synthetic=False)
    assert defaulted.is_synthetic is False
    assert defaulted.mock_label == ""

    tagged = _frame(0, is_synthetic=False, mock_label="unit-fixture")
    assert tagged.mock_label == "unit-fixture"

    forced = _frame(0, is_synthetic=True, mock_label="other")
    assert forced.mock_label == MOCK_SYNTHETIC_LABEL
