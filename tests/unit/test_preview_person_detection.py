from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest
from cv.frame import Frame


def _load_preview() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "preview_person_detection.py"
    spec = importlib.util.spec_from_file_location("ilka_preview_person_detection", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def preview() -> ModuleType:
    return _load_preview()


def test_preview_missing_video_exits_nonzero(preview: ModuleType, tmp_path: Path) -> None:
    missing_video = tmp_path / "absent.mp4"
    missing_weights = tmp_path / "absent.pth"
    code = preview.main(
        [
            "--video",
            str(missing_video),
            "--weights",
            str(missing_weights),
            "--no-display",
            "--no-save",
        ]
    )
    assert code != 0


def test_preview_missing_weights_exits_nonzero(preview: ModuleType, tmp_path: Path) -> None:
    video = tmp_path / "placeholder.avi"
    video.write_bytes(b"not-a-decoded-clip")
    missing_weights = tmp_path / "absent.pth"
    code = preview.main(
        [
            "--video",
            str(video),
            "--weights",
            str(missing_weights),
            "--no-display",
            "--no-save",
        ]
    )
    assert code != 0


def test_invalid_min_confidence_exits_without_output(
    preview: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "annotated.mp4"
    code = preview.main(
        [
            "--video",
            str(tmp_path / "clip.avi"),
            "--weights",
            str(tmp_path / "weights.pth"),
            "--min-confidence",
            "2",
            "--output",
            str(output),
            "--no-display",
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert not output.exists()
    assert "min-confidence" in captured.err
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out


def test_boundary_confidence_is_accepted(
    preview: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for value in ("0", "1", "0.0", "1.0"):
        code = preview.main(
            [
                "--video",
                str(tmp_path / "missing.avi"),
                "--weights",
                str(tmp_path / "missing.pth"),
                "--min-confidence",
                value,
                "--no-display",
                "--no-save",
            ]
        )
        captured = capsys.readouterr()
        assert code == 1
        assert "min-confidence" not in captured.err


def test_max_frames_does_not_read_past_budget(
    preview: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video = tmp_path / "clip.avi"
    weights = tmp_path / "weights.pth"
    output = tmp_path / "annotated.mp4"
    video.write_bytes(b"not-decoded")
    weights.write_bytes(b"local-weights")
    reads = {"count": 0}

    class _Image:
        shape = (8, 8, 3)

        def copy(self) -> _Image:
            return self

    class _Source:
        def __init__(self, _path: Path, source_id: str | None = None) -> None:
            self.source_id = source_id or "clip"

        def open(self) -> None:
            return None

        def read(self) -> Frame | None:
            reads["count"] += 1
            if reads["count"] > 5:
                return None
            now = datetime.now(UTC)
            return Frame(
                data=_Image(),
                index=reads["count"] - 1,
                captured_at=now,
                processed_at=now,
                source_id="clip",
            )

        def close(self) -> None:
            return None

    class _Detector:
        def __init__(self, *, weights_path: Path, min_confidence: float) -> None:
            self.model_id = "stub"
            self.model_version = "stub"
            self.weights_path = weights_path
            self.min_confidence = min_confidence

        def detect(self, _frame: Frame) -> list[object]:
            return []

    monkeypatch.setattr(preview, "FileSource", _Source)
    monkeypatch.setattr(preview, "CpuPersonDetector", _Detector)
    monkeypatch.setattr(preview, "load_cv2", lambda: object())
    monkeypatch.setattr(preview, "_probe_fps", lambda _path: 25.0)
    monkeypatch.setattr(
        preview,
        "_annotate",
        lambda image, _observations, **_kwargs: image,
    )
    code = preview.main(
        [
            "--video",
            str(video),
            "--weights",
            str(weights),
            "--output",
            str(output),
            "--max-frames",
            "2",
            "--no-display",
            "--no-save",
        ]
    )
    assert code == 0
    assert reads["count"] == 2
    assert not output.exists()
