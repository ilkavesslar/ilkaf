"""Detection scores and explicit stubs for pose and tracking metrics.

Precision, recall, and F1 are computed from counts the caller supplies.
OKS and IDF1 are not computed. A stub returns ``value=None`` so a missing
implementation cannot be read as a score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DetectionScores:
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float | None
    f1: float | None


@dataclass(frozen=True, slots=True)
class MetricResult:
    """A named metric. ``computed`` is false when this module refuses to score it."""

    name: str
    computed: bool
    value: float | None
    reason: str


def precision(true_positive: int, false_positive: int) -> float | None:
    """True positives over all predicted positives. ``None`` when nothing was predicted."""

    tp = _count(true_positive, "true_positive")
    fp = _count(false_positive, "false_positive")
    predicted = tp + fp
    if predicted == 0:
        return None
    return tp / predicted


def recall(true_positive: int, false_negative: int) -> float | None:
    """True positives over all ground-truth objects. ``None`` when there is no ground truth."""

    tp = _count(true_positive, "true_positive")
    fn = _count(false_negative, "false_negative")
    actual = tp + fn
    if actual == 0:
        return None
    return tp / actual


def f1(precision_value: float | None, recall_value: float | None) -> float | None:
    """Harmonic mean. ``None`` when either input is undefined. Both zero returns 0.0."""

    if precision_value is None or recall_value is None:
        return None
    _unit_interval(precision_value, "precision")
    _unit_interval(recall_value, "recall")
    total = precision_value + recall_value
    if total == 0.0:
        return 0.0
    return 2.0 * precision_value * recall_value / total


def precision_recall_f1(
    true_positive: int,
    false_positive: int,
    false_negative: int,
) -> DetectionScores:
    precision_value = precision(true_positive, false_positive)
    recall_value = recall(true_positive, false_negative)
    return DetectionScores(
        true_positive=_count(true_positive, "true_positive"),
        false_positive=_count(false_positive, "false_positive"),
        false_negative=_count(false_negative, "false_negative"),
        precision=precision_value,
        recall=recall_value,
        f1=f1(precision_value, recall_value),
    )


def oks_stub(
    *,
    prediction: Any = None,
    ground_truth: Any = None,
) -> MetricResult:
    """COCO Object Keypoint Similarity is not implemented.

    Arguments are accepted so callers can pass keypoints later. They are not
    scored. Returning a number here would invent an OKS.
    """

    del prediction, ground_truth
    return MetricResult(
        name="oks",
        computed=False,
        value=None,
        reason=(
            "OKS is not implemented. No score was computed. "
            "COCO OKS needs predicted keypoints, ground-truth keypoints, "
            "per-joint sigmas, and an object scale."
        ),
    )


def idf1_stub(
    *,
    hypothesis_ids: Any = None,
    ground_truth_ids: Any = None,
) -> MetricResult:
    """IDF1 (identity F1) is not implemented.

    Arguments are accepted and ignored. This stub does not pair identities
    and does not return zero, which would look like a measured miss rate.
    """

    del hypothesis_ids, ground_truth_ids
    return MetricResult(
        name="idf1",
        computed=False,
        value=None,
        reason=(
            "IDF1 is not implemented. No score was computed. "
            "Identity F1 needs a hypothesis-to-ground-truth identity matching "
            "over frames, which this module does not run."
        ),
    )


def _count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be a non-negative int")
    if value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a float in [0, 1]")
    number = float(value)
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return number
