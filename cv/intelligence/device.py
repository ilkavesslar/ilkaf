"""Device profile selection for Human Intelligence inference.

Intel Mac development stays CPU-only. NVIDIA CUDA is opt-in and must not be
assumed present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DeviceProfile = Literal["intel_mac_cpu", "nvidia_cuda", "cpu"]


@dataclass(frozen=True, slots=True)
class DeviceSelection:
    profile: DeviceProfile
    torch_device: str
    cuda_available: bool
    detail: str


def select_device(preferred: DeviceProfile | None = None) -> DeviceSelection:
    """Return a safe torch device string. Never raises if CUDA is missing."""

    cuda = False
    try:
        import torch

        cuda = bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001 — optional runtime
        return DeviceSelection(
            profile="cpu",
            torch_device="cpu",
            cuda_available=False,
            detail="PyTorch is unavailable; callers must use CPU adapters or skip inference.",
        )

    if preferred == "nvidia_cuda":
        if cuda:
            return DeviceSelection(
                profile="nvidia_cuda",
                torch_device="cuda",
                cuda_available=True,
                detail="CUDA is available for production workers.",
            )
        return DeviceSelection(
            profile="cpu",
            torch_device="cpu",
            cuda_available=False,
            detail="nvidia_cuda requested but CUDA is unavailable; falling back to CPU.",
        )

    return DeviceSelection(
        profile="intel_mac_cpu" if preferred in (None, "intel_mac_cpu", "cpu") else "cpu",
        torch_device="cpu",
        cuda_available=cuda,
        detail="CPU profile selected for development and Intel Mac compatibility.",
    )
