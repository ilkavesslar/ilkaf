"""Download TorchVision Keypoint R-CNN COCO weights for local HIE pose (Intel Mac).

Never called automatically by detectors. Official download.pytorch.org host only.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cv.pose.torchvision_keypoint import (
    WEIGHTS_BYTES,
    WEIGHTS_BYTES_MIN,
    WEIGHTS_FILE,
    WEIGHTS_SHA256,
    WEIGHTS_URL,
)

DEST = ROOT / "data" / "models" / WEIGHTS_FILE
_HOST = "https://download.pytorch.org/"


def main() -> int:
    print("Model: TorchVision KeypointRCNN ResNet50-FPN (COCO) [PROVISIONAL lab pose]")
    print(f"Source URL: {WEIGHTS_URL}")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.is_file() and DEST.stat().st_size >= WEIGHTS_BYTES_MIN:
        digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
        print(f"Already present: {DEST} ({DEST.stat().st_size} bytes)")
        print(f"SHA-256: {digest}")
        return 0
    partial = DEST.with_suffix(DEST.suffix + ".partial")
    try:
        request = urllib.request.Request(WEIGHTS_URL, headers={"User-Agent": "ilka-pose-fetch/1.0"})
        with urllib.request.urlopen(request, timeout=300) as response:
            if not str(response.geturl()).startswith(_HOST):
                print("Download left the official PyTorch host", file=sys.stderr)
                return 1
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    handle.flush()
        size = partial.stat().st_size
        if size < WEIGHTS_BYTES_MIN:
            print(f"Downloaded file too small ({size} bytes)", file=sys.stderr)
            partial.unlink(missing_ok=True)
            return 1
        digest = hashlib.sha256(partial.read_bytes()).hexdigest()
        if digest != WEIGHTS_SHA256:
            print(
                f"SHA-256 mismatch: expected {WEIGHTS_SHA256}, got {digest}",
                file=sys.stderr,
            )
            partial.unlink(missing_ok=True)
            return 1
        if size != WEIGHTS_BYTES:
            print(
                f"Warning: size {size} != pinned {WEIGHTS_BYTES} (digest OK)",
                file=sys.stderr,
            )
        partial.replace(DEST)
    except Exception as exc:  # noqa: BLE001
        partial.unlink(missing_ok=True)
        print(f"Pose weight download failed: {exc}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    print(f"Saved: {DEST} ({DEST.stat().st_size} bytes)")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
