"""Download MediaPipe Pose Landmarker Lite (.task) for local HIE pose.

Does not download automatically from detectors. Official MediaPipe model host only.
Weights stay out of Git.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "data" / "models" / "pose_landmarker_lite.task"
# Official MediaPipe model CDN (float16 lite, version 1).
URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
_HOST_PREFIX = "https://storage.googleapis.com/mediapipe-models/"
# Digests vary by CDN revision; we record after a successful download.
# Pin empty until first verified fetch writes DEST; verify size > 1 MiB.


def main() -> int:
    print("Model: MediaPipe Pose Landmarker Lite (COCO-17 mapped in ILKA)")
    print(f"Source URL: {URL}")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.is_file() and DEST.stat().st_size > 1_000_000:
        digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
        print(f"Already present: {DEST} ({DEST.stat().st_size} bytes)")
        print(f"SHA-256: {digest}")
        return 0
    partial = DEST.with_suffix(DEST.suffix + ".partial")
    try:
        request = urllib.request.Request(URL, headers={"User-Agent": "ilka-pose-fetch/1.0"})
        with urllib.request.urlopen(request, timeout=180) as response:
            final_url = str(response.geturl())
            if not final_url.startswith(_HOST_PREFIX):
                print("Download left the official MediaPipe host", file=sys.stderr)
                return 1
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
        if partial.stat().st_size < 1_000_000:
            print("Downloaded file is unexpectedly small", file=sys.stderr)
            partial.unlink(missing_ok=True)
            return 1
        partial.replace(DEST)
    except Exception as exc:  # noqa: BLE001
        partial.unlink(missing_ok=True)
        print(f"Pose model download failed: {exc}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    print(f"Saved: {DEST} ({DEST.stat().st_size} bytes)")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
