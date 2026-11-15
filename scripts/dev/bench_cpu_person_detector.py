"""Measure CPU person-detector latency. Does not download weights.

Requires ``ILKA_CV_PERSON_WEIGHTS`` to already point at the pinned local file.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from datetime import UTC, datetime

from cv.detectors.person_cpu import WEIGHTS_ENV, CpuPersonDetector
from cv.errors import DetectorDependencyError, DetectorModelError
from cv.frame import Frame


def main() -> int:
    configured = os.environ.get(WEIGHTS_ENV, "").strip()
    if not configured:
        print(
            f"{WEIGHTS_ENV} is not set. This benchmark does not download weights.",
            file=sys.stderr,
        )
        return 1
    try:
        import numpy as np
    except ImportError:
        print("NumPy is required for the benchmark.", file=sys.stderr)
        return 1
    try:
        detector = CpuPersonDetector(weights_path=configured)
    except (DetectorDependencyError, DetectorModelError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    image = np.zeros((320, 320, 3), dtype=np.uint8)
    now = datetime.now(UTC)
    frame = Frame(
        data=image,
        index=0,
        captured_at=now,
        processed_at=now,
        source_id="bench-synthetic",
    )
    warmup = detector.detect(frame)
    samples: list[float] = []
    for index in range(8):
        frame = Frame(
            data=image,
            index=index,
            captured_at=now,
            processed_at=now,
            source_id="bench-synthetic",
        )
        started = time.perf_counter()
        detector.detect(frame)
        samples.append((time.perf_counter() - started) * 1000.0)
    samples.sort()
    p50 = statistics.median(samples)
    p95 = samples[max(0, round(0.95 * (len(samples) - 1)))]
    print("ILKA M3 CPU person detector benchmark [MOCK / SYNTHETIC]")
    print(f"model_id={detector.model_id} model_version={detector.model_version}")
    print(f"warmup_observations={len(warmup)} frames={len(samples)}")
    print(f"p50_ms={p50:.1f} p95_ms={p95:.1f}")
    print("CUDA was not selected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
