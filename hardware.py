"""Hardware detection: device, compute type, and available memory in one probe.

Detection and compute-type selection are one concept and live together here.
"""

import platform
import shutil
import subprocess
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class HardwareInfo:
    device: str  # "cuda" | "cpu"
    compute_type: str  # "int8_float16" | "int8"
    available_memory_gb: float
    platform: str
    gpu_name: str | None


def detect_hardware() -> HardwareInfo:
    gpu = _detect_nvidia()
    if gpu is not None:
        name, free_gb = gpu
        return HardwareInfo(
            device="cuda",
            compute_type="int8_float16",
            available_memory_gb=free_gb,
            platform=platform.platform(),
            gpu_name=name,
        )

    available_gb = round(psutil.virtual_memory().available / (1024**3), 1)
    return HardwareInfo(
        device="cpu",
        compute_type="int8",
        available_memory_gb=available_gb,
        platform=platform.platform(),
        gpu_name=None,
    )


def _detect_nvidia() -> tuple[str, float] | None:
    """Return (gpu_name, free_vram_gb) if an NVIDIA GPU is present, else None."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    lines = out.strip().splitlines()
    if not lines:
        return None
    name, free_mb = (part.strip() for part in lines[0].split(","))
    return name, round(float(free_mb) / 1024, 1)
