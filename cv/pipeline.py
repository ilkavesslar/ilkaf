"""Sampled detection adapter. Observations only. Does not open cameras or create incidents."""

from __future__ import annotations

from dataclasses import dataclass

from cv.detectors.base import PersonDetector
from cv.errors import DetectorError, DetectorInferenceError
from cv.observation import Observation
from cv.streams.base import VideoSource


@dataclass(frozen=True, slots=True)
class SampledRun:
    frames_read: int
    frames_inferred: int
    observations: list[Observation]


def run_sampled_detection(
    source: VideoSource,
    detector: PersonDetector,
    *,
    max_frames: int,
    sample_every: int = 1,
) -> SampledRun:
    """Read at most ``max_frames`` frames and run ``detector`` every ``sample_every`` frame.

    The caller opens and closes ``source``. Stream rate and inference rate stay separate.
    """

    if isinstance(max_frames, bool) or not isinstance(max_frames, int) or max_frames < 1:
        raise ValueError("max_frames must be an integer of at least 1")
    if isinstance(sample_every, bool) or not isinstance(sample_every, int) or sample_every < 1:
        raise ValueError("sample_every must be an integer of at least 1")
    frames_read = 0
    frames_inferred = 0
    observations: list[Observation] = []
    while frames_read < max_frames:
        frame = source.read()
        if frame is None:
            break
        frames_read += 1
        if (frames_read - 1) % sample_every != 0:
            continue
        try:
            found = detector.detect(frame)
        except DetectorError:
            raise
        except Exception as exc:
            raise DetectorInferenceError("detection failed") from exc
        frames_inferred += 1
        observations.extend(found)
    return SampledRun(
        frames_read=frames_read,
        frames_inferred=frames_inferred,
        observations=observations,
    )
