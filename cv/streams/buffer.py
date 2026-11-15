from __future__ import annotations

from collections import deque

from cv.frame import Frame


class BoundedFrameBuffer:
    """In-memory ring buffer. When full, the oldest frame is dropped."""

    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        self._maxsize = maxsize
        self._frames: deque[Frame] = deque(maxlen=maxsize)
        self._dropped = 0

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def dropped(self) -> int:
        return self._dropped

    def __len__(self) -> int:
        return len(self._frames)

    def push(self, frame: Frame) -> None:
        if len(self._frames) == self._maxsize:
            self._dropped += 1
        self._frames.append(frame)

    def pop(self) -> Frame | None:
        if not self._frames:
            return None
        return self._frames.popleft()

    def clear(self) -> None:
        self._frames.clear()
