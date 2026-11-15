"""Download the official SSDLite COCO weights and keep them only if the digest matches.

The pinned SHA-256 is ``cv.detectors.person_cpu.WEIGHTS_SHA256``. PyTorch does not
publish that full digest as a separate checksum file. It publishes the leading
eight hex characters in the official filename, and ``torch.hub`` checks that
SHA-256 prefix. The full pin was taken from
``https://download.pytorch.org/models/ssdlite320_mobilenet_v3_large_coco-a79551df.pth``
after that prefix matched and the size matched TorchVision's 13.418 MiB catalog
entry. A mismatch deletes the partial file and does not report success.

This script does not certify detection accuracy. The lab detector stays provisional.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_cv() -> tuple[int, str, str, object, type[Exception]]:
    """Import detector constants after the repository root is on sys.path."""
    from cv.detectors.person_cpu import (
        WEIGHTS_BYTES,
        WEIGHTS_SHA256,
        WEIGHTS_URL,
        verify_weights_file,
    )
    from cv.errors import DetectorModelError

    return (
        WEIGHTS_BYTES,
        WEIGHTS_SHA256,
        WEIGHTS_URL,
        verify_weights_file,
        DetectorModelError,
    )


(
    WEIGHTS_BYTES,
    WEIGHTS_SHA256,
    WEIGHTS_URL,
    verify_weights_file,
    DetectorModelError,
) = _load_cv()

DEST = ROOT / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"
_OFFICIAL_HOST = "https://download.pytorch.org/"


def _download(dest: Path) -> None:
    request = urllib.request.Request(WEIGHTS_URL, headers={"User-Agent": "ilka-weight-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        final_url = response.geturl()
        if not str(final_url).startswith(_OFFICIAL_HOST):
            raise DetectorModelError("person detector weight download left the official host")
        with dest.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)


def main() -> int:
    print("Model: TorchVision SSDLite320 MobileNetV3-Large (COCO) [PROVISIONAL lab detector]")
    print(f"Source URL: {WEIGHTS_URL}")
    print("Integrity: pinned SHA-256. Success is reported only after the file matches.")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    partial = DEST.with_suffix(DEST.suffix + ".partial")
    try:
        _download(partial)
        if partial.stat().st_size != WEIGHTS_BYTES:
            raise DetectorModelError(
                "person detector weights size does not match the pinned artifact"
            )
        verify_weights_file(partial, expected_sha256=WEIGHTS_SHA256)
    except DetectorModelError as exc:
        partial.unlink(missing_ok=True)
        print(str(exc), file=sys.stderr)
        print("Weights were not saved. The download is not verified.", file=sys.stderr)
        return 1
    except (OSError, urllib.error.URLError):
        partial.unlink(missing_ok=True)
        print("Weight download failed. The download is not verified.", file=sys.stderr)
        return 1
    partial.replace(DEST)
    print(f"Verified SHA-256 and wrote {DEST}")
    print("Set ILKA_CV_PERSON_WEIGHTS to that path. Do not commit the file.")
    print("This does not certify detection accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
