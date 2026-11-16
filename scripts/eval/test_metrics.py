"""Unit tests for detection scores and the OKS / IDF1 stubs."""

from __future__ import annotations

import unittest

from metrics import f1, idf1_stub, oks_stub, precision, precision_recall_f1, recall


class PrecisionRecallF1Tests(unittest.TestCase):
    def test_balanced_counts(self) -> None:
        scores = precision_recall_f1(1, 1, 0)
        self.assertEqual(scores.precision, 0.5)
        self.assertEqual(scores.recall, 1.0)
        self.assertAlmostEqual(scores.f1 or 0.0, 2.0 / 3.0)

    def test_undefined_when_there_are_no_objects(self) -> None:
        scores = precision_recall_f1(0, 0, 0)
        self.assertIsNone(scores.precision)
        self.assertIsNone(scores.recall)
        self.assertIsNone(scores.f1)

    def test_precision_zero_does_not_invent_recall(self) -> None:
        self.assertEqual(precision(0, 1), 0.0)
        self.assertIsNone(recall(0, 0))
        self.assertIsNone(f1(0.0, None))

    def test_both_zero_is_zero_f1(self) -> None:
        self.assertEqual(f1(0.0, 0.0), 0.0)

    def test_rejects_bool_and_negative(self) -> None:
        with self.assertRaises(TypeError):
            precision(True, 0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            recall(0, -1)


class StubTests(unittest.TestCase):
    def test_oks_is_not_a_number(self) -> None:
        result = oks_stub(prediction=[(0.0, 0.0)], ground_truth=[(1.0, 1.0)])
        self.assertEqual(result.name, "oks")
        self.assertFalse(result.computed)
        self.assertIsNone(result.value)

    def test_idf1_is_not_a_number(self) -> None:
        result = idf1_stub(hypothesis_ids=[1], ground_truth_ids=[1])
        self.assertEqual(result.name, "idf1")
        self.assertFalse(result.computed)
        self.assertIsNone(result.value)


if __name__ == "__main__":
    unittest.main()
