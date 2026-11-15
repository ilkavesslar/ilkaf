from __future__ import annotations

import sys

import pytest

from cv.errors import CvDependencyError
from cv.opencv import load_cv2


def test_load_cv2_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if name == "cv2":
            raise ImportError("simulated missing opencv")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "cv2", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(CvDependencyError, match="OpenCV is required"):
        load_cv2()
