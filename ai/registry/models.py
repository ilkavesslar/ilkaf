"""PROVISIONAL model cards. Not a production model ADR.

Reads ``registry.yaml`` beside this file. Does not download weights, does not
load Torch, and does not report accuracy.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEVICE_PROFILES = frozenset({"intel_mac_cpu", "nvidia_cuda"})
WEIGHTS_POLICIES = frozenset({"local_pin", "download_script", "not_bundled"})
PROVENANCE = frozenset({"pretrained", "finetuned"})
STATUSES = frozenset({"lab_verified", "placeholder"})

REGISTRY_PATH = Path(__file__).resolve().parent / "registry.yaml"


@dataclass(frozen=True, slots=True)
class ModelCard:
    """One registry row. ``metrics_reported`` is always false in this tree."""

    model_id: str
    task: str
    framework: str
    device_profiles: tuple[str, ...]
    weights_policy: str
    provenance: str
    status: str
    measured: bool
    cv_detector_name: str
    cv_model_id: str
    weights_env: str
    notes: str
    metrics_reported: bool = False

    def supports(self, profile: str) -> bool:
        return profile in self.device_profiles


@dataclass(frozen=True, slots=True)
class ModelRegistry:
    schema_version: int
    default_model_id: str
    cards: tuple[ModelCard, ...]

    def get(self, model_id: str) -> ModelCard:
        for card in self.cards:
            if card.model_id == model_id:
                return card
        known = ", ".join(card.model_id for card in self.cards)
        raise KeyError(f"unknown model_id {model_id!r}; known: {known}")

    def default(self) -> ModelCard:
        return self.get(self.default_model_id)


def parse_simple_yaml(text: str) -> Any:
    """Parse the small YAML subset used by this registry and the dataset manifest.

    Supported: indent-based maps, lists, scalars, ``#`` comments, double-quoted
    strings. Not supported: tabs, anchors, flow collections, or multiline
    scalars. PyYAML is intentionally not required.
    """

    lines = _prepare(text)
    if not lines:
        return None
    value, index = _parse_node(lines, 0, 0)
    if index != len(lines):
        raise ValueError(f"yaml trailing content at line {lines[index][2]}")
    return value


def load_registry(path: Path | None = None) -> ModelRegistry:
    """Load and reject cards that claim a finished fine-tune or a metric."""

    source = REGISTRY_PATH if path is None else path
    document = parse_simple_yaml(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("model registry root must be a mapping")
    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(f"model registry schema_version must be {SCHEMA_VERSION}")
    default_model_id = document.get("default_model_id")
    if not isinstance(default_model_id, str) or not default_model_id:
        raise ValueError("default_model_id is required")
    raw_cards = document.get("models")
    if not isinstance(raw_cards, list) or not raw_cards:
        raise ValueError("models must be a non-empty list")
    cards: list[ModelCard] = []
    seen: set[str] = set()
    for raw in raw_cards:
        card = _card_from_mapping(raw)
        if card.model_id in seen:
            raise ValueError(f"duplicate model_id: {card.model_id}")
        seen.add(card.model_id)
        cards.append(card)
    if default_model_id not in seen:
        raise ValueError(f"default_model_id is not registered: {default_model_id}")
    verified = [card for card in cards if card.status == "lab_verified"]
    if len(verified) != 1:
        raise ValueError("exactly one lab_verified model is required")
    default = next(card for card in cards if card.model_id == default_model_id)
    if default.status != "lab_verified":
        raise ValueError("default model must be lab_verified")
    if "intel_mac_cpu" not in default.device_profiles:
        raise ValueError("default model must list intel_mac_cpu")
    if default.weights_policy != "local_pin":
        raise ValueError("default model must use weights_policy local_pin")
    if not default.measured:
        raise ValueError("default model must be measured on its lab path")
    return ModelRegistry(version, default_model_id, tuple(cards))


def _card_from_mapping(raw: Any) -> ModelCard:
    if not isinstance(raw, dict):
        raise ValueError("each model card must be a mapping")
    model_id = _required_str(raw, "model_id")
    task = _required_str(raw, "task")
    framework = _required_str(raw, "framework")
    profiles = raw.get("device_profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError(f"{model_id}: device_profiles must be a non-empty list")
    if any(not isinstance(item, str) for item in profiles):
        raise ValueError(f"{model_id}: device_profiles entries must be strings")
    unknown = [item for item in profiles if item not in DEVICE_PROFILES]
    if unknown:
        raise ValueError(f"{model_id}: unknown device_profiles {unknown}")
    if len(set(profiles)) != len(profiles):
        raise ValueError(f"{model_id}: device_profiles has duplicates")
    weights_policy = _required_str(raw, "weights_policy")
    if weights_policy not in WEIGHTS_POLICIES:
        raise ValueError(f"{model_id}: unknown weights_policy {weights_policy}")
    provenance = _required_str(raw, "provenance")
    if provenance not in PROVENANCE:
        raise ValueError(f"{model_id}: unknown provenance {provenance}")
    if provenance == "finetuned":
        record = raw.get("training_run_record")
        if not isinstance(record, str) or not record.strip():
            raise ValueError(
                f"{model_id}: finetuned provenance requires training_run_record; "
                "this tree does not claim a completed training run"
            )
    status = _required_str(raw, "status")
    if status not in STATUSES:
        raise ValueError(f"{model_id}: unknown status {status}")
    measured = raw.get("measured")
    if not isinstance(measured, bool):
        raise ValueError(f"{model_id}: measured must be a boolean")
    if status == "placeholder" and measured:
        raise ValueError(f"{model_id}: a placeholder cannot be measured")
    if status == "lab_verified" and not measured:
        raise ValueError(f"{model_id}: lab_verified requires measured true")
    if raw.get("metrics_reported") is not False:
        raise ValueError(f"{model_id}: metrics_reported must be false; do not store accuracy here")
    for banned in ("map", "accuracy", "precision", "recall", "f1", "oks", "idf1"):
        if banned in raw:
            raise ValueError(f"{model_id}: field {banned} is not allowed on a model card")
    notes = _required_str(raw, "notes")
    return ModelCard(
        model_id=model_id,
        task=task,
        framework=framework,
        device_profiles=tuple(profiles),
        weights_policy=weights_policy,
        provenance=provenance,
        status=status,
        measured=measured,
        cv_detector_name=_optional_str(raw, "cv_detector_name"),
        cv_model_id=_optional_str(raw, "cv_model_id"),
        weights_env=_optional_str(raw, "weights_env"),
        notes=notes,
        metrics_reported=False,
    )


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip()


def _prepare(text: str) -> list[tuple[int, str, int]]:
    prepared: list[tuple[int, str, int]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            raise ValueError(f"tabs are not allowed (line {number})")
        content = _strip_comment(raw).rstrip()
        if not content.strip():
            continue
        indent = len(content) - len(content.lstrip(" "))
        prepared.append((indent, content.strip(), number))
    return prepared


def _strip_comment(raw: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(raw):
        if quote is not None:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "#":
            return raw[:index]
    return raw


def _parse_node(lines: list[tuple[int, str, int]], index: int, min_indent: int) -> tuple[Any, int]:
    if index >= len(lines) or lines[index][0] < min_indent:
        raise ValueError("expected a yaml value")
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index)
    return _parse_map(lines, index)


def _parse_list(lines: list[tuple[int, str, int]], index: int) -> tuple[list[Any], int]:
    indent = lines[index][0]
    items: list[Any] = []
    while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
        number = lines[index][2]
        rest = lines[index][1][2:].strip()
        index += 1
        if rest == "":
            if index >= len(lines) or lines[index][0] <= indent:
                items.append(None)
                continue
            value, index = _parse_node(lines, index, indent + 1)
            items.append(value)
            continue
        if _looks_like_key(rest):
            key, raw_value = _split_key(rest, number)
            item: dict[str, Any] = {}
            if raw_value == "":
                value, index = _parse_node(lines, index, indent + 1)
                item[key] = value
            else:
                item[key] = _parse_scalar(raw_value, number)
            index = _fill_map(lines, index, indent + 2, item)
            items.append(item)
            continue
        items.append(_parse_scalar(rest, number))
    return items, index


def _parse_map(lines: list[tuple[int, str, int]], index: int) -> tuple[dict[str, Any], int]:
    indent = lines[index][0]
    mapping: dict[str, Any] = {}
    index = _fill_map(lines, index, indent, mapping)
    return mapping, index


def _fill_map(
    lines: list[tuple[int, str, int]],
    index: int,
    indent: int,
    mapping: dict[str, Any],
) -> int:
    while index < len(lines) and lines[index][0] == indent and not lines[index][1].startswith("- "):
        number = lines[index][2]
        key, raw_value = _split_key(lines[index][1], number)
        if key in mapping:
            raise ValueError(f"duplicate key {key!r} (line {number})")
        index += 1
        if raw_value == "":
            if index < len(lines) and lines[index][0] > indent:
                value, index = _parse_node(lines, index, indent + 1)
            else:
                value = None
            mapping[key] = value
            continue
        mapping[key] = _parse_scalar(raw_value, number)
    return index


def _looks_like_key(text: str) -> bool:
    if text.startswith('"') or text.startswith("'"):
        return False
    return ":" in text


def _split_key(text: str, number: int) -> tuple[str, str]:
    if text.startswith("- "):
        raise ValueError(f"expected a key (line {number})")
    colon = text.find(":")
    if colon <= 0:
        raise ValueError(f"expected key: value (line {number})")
    key = text[:colon].strip()
    raw_value = text[colon + 1 :].strip()
    if not key or any(char.isspace() for char in key):
        raise ValueError(f"invalid key {text!r} (line {number})")
    return key, raw_value


def _is_float(raw: str) -> bool:
    if raw.count(".") != 1:
        return False
    left, right = raw.split(".", 1)
    if left in {"", "-", "+"}:
        return right.isdigit()
    if left.startswith(("+", "-")):
        left = left[1:]
    return bool(left) and left.isdigit() and right.isdigit()


def _parse_scalar(raw: str, number: int) -> Any:
    if raw in {"null", "~"}:
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw.startswith('"'):
        return _parse_double_quoted(raw, number)
    if raw.startswith("'"):
        return _parse_single_quoted(raw, number)
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        return int(raw)
    if _is_float(raw):
        return float(raw)
    return raw


def _parse_double_quoted(raw: str, number: int) -> str:
    if len(raw) < 2 or not raw.endswith('"'):
        raise ValueError(f"unterminated string (line {number})")
    body = raw[1:-1]
    chars: list[str] = []
    escaped = False
    for char in body:
        if escaped:
            mapping = {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}
            if char not in mapping:
                raise ValueError(f"unknown escape \\{char} (line {number})")
            chars.append(mapping[char])
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        chars.append(char)
    if escaped:
        raise ValueError(f"unterminated escape (line {number})")
    return "".join(chars)


def _parse_single_quoted(raw: str, number: int) -> str:
    if len(raw) < 2 or not raw.endswith("'"):
        raise ValueError(f"unterminated string (line {number})")
    return raw[1:-1].replace("''", "'")


def _print_registry(registry: ModelRegistry) -> None:
    print("ILKA model registry [PROVISIONAL]")
    print(f"default_model_id={registry.default_model_id}")
    print("measured_means: lab_runtime_path_not_accuracy")
    print("accuracy: not_reported")
    for card in registry.cards:
        profiles = ",".join(card.device_profiles)
        print(
            f"{card.model_id} task={card.task} framework={card.framework} "
            f"status={card.status} measured={str(card.measured).lower()} "
            f"weights_policy={card.weights_policy} provenance={card.provenance} "
            f"device_profiles={profiles}"
        )


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        registry = load_registry()
    except (OSError, ValueError) as exc:
        print(f"model registry is invalid: {exc}", file=sys.stderr)
        return 1
    _print_registry(registry)
    print("No weights were downloaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
