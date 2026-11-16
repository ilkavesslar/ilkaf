"""Registry, manifest, latency-summary, and train-config checks. No downloads."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.registry.models import load_registry, parse_simple_yaml
from bench_detection_latency import skip_reason, summarize_latency_ms
from dataset_manifest import MANIFEST_PATH, validate_manifest


class RegistryTests(unittest.TestCase):
    def test_default_is_pinned_ssdlite_without_metrics(self) -> None:
        registry = load_registry()
        default = registry.default()
        self.assertEqual(default.model_id, "ssdlite320-mobilenet-v3")
        self.assertEqual(default.status, "lab_verified")
        self.assertEqual(default.weights_policy, "local_pin")
        self.assertEqual(default.provenance, "pretrained")
        self.assertEqual(default.device_profiles, ("intel_mac_cpu",))
        self.assertFalse(default.metrics_reported)
        self.assertTrue(all(card.provenance != "finetuned" for card in registry.cards))
        self.assertTrue(all(card.metrics_reported is False for card in registry.cards))
        placeholders = [card for card in registry.cards if card.status == "placeholder"]
        self.assertTrue(placeholders)
        self.assertTrue(all(card.weights_policy == "not_bundled" for card in placeholders))
        self.assertTrue(all(card.measured is False for card in placeholders))

    def test_manifest_entries_and_no_download_flag(self) -> None:
        document = parse_simple_yaml(MANIFEST_PATH.read_text(encoding="utf-8"))
        entries = validate_manifest(document)
        ids = {row["id"] for row in entries}
        self.assertEqual(
            ids,
            {
                "coco-2017-detection",
                "coco-2017-keypoints",
                "crowdhuman",
                "crowdpose",
                "mot17",
                "mot20",
                "posetrack",
                "ntu-rgbd-120",
                "ur-fall",
                "up-fall",
            },
        )
        self.assertTrue(all(row["ilka_usage"] != "allowed_for_eval" for row in entries))
        self.assertTrue(all(row["commercial_use"] != "yes" for row in entries))

    def test_train_config_does_not_claim_completion(self) -> None:
        path = ROOT / "scripts" / "train" / "config_example.yaml"
        document = parse_simple_yaml(path.read_text(encoding="utf-8"))
        self.assertIsInstance(document, dict)
        self.assertIs(document["run"]["claim_training_completed"], False)
        self.assertIsNone(document["run"]["output_checkpoint"])
        self.assertIs(document["runtime"]["download_weights"], False)
        self.assertIs(document["runtime"]["download_datasets"], False)
        self.assertEqual(document["optim"]["learning_rate"], 0.001)
        self.assertEqual(document["optim"]["epochs"], 1)
        self.assertEqual(document["model"]["init_model_id"], "ssdlite320-mobilenet-v3")


class LatencyHelperTests(unittest.TestCase):
    def test_skip_without_runtime_or_weights(self) -> None:
        reason = skip_reason(
            torch_available=False,
            torchvision_available=True,
            numpy_available=True,
            weights_file=Path("/tmp/does-not-matter.pth"),
        )
        self.assertIsNotNone(reason)
        self.assertIn("PyTorch", reason or "")

    def test_empty_samples_do_not_invent_a_time(self) -> None:
        with self.assertRaises(ValueError):
            summarize_latency_ms([])

    def test_median_of_known_samples(self) -> None:
        p50, _p95 = summarize_latency_ms([10.0, 30.0, 20.0])
        self.assertEqual(p50, 20.0)


if __name__ == "__main__":
    unittest.main()
