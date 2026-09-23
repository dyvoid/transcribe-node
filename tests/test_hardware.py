import subprocess

import pytest

import hardware


@pytest.fixture
def smi(monkeypatch):
    """Pretend nvidia-smi exists and returns the given CSV line."""

    def install(output: str) -> None:
        monkeypatch.setattr(hardware.shutil, "which", lambda _: "/usr/bin/nvidia-smi")
        monkeypatch.setattr(hardware.subprocess, "check_output", lambda *a, **k: output)

    return install


def test_parses_name_and_free_memory(smi):
    smi("NVIDIA GeForce RTX 4090, 20480\n")
    assert hardware._detect_nvidia() == ("NVIDIA GeForce RTX 4090", 20.0)


def test_name_containing_comma(smi):
    smi("NVIDIA A100-SXM4-40GB, MIG 1g.5gb, 4864\n")
    assert hardware._detect_nvidia() == ("NVIDIA A100-SXM4-40GB, MIG 1g.5gb", 4.8)


def test_unreported_free_memory_keeps_gpu(smi):
    smi("NVIDIA GeForce RTX 3050 Laptop GPU, [N/A]\n")
    assert hardware._detect_nvidia() == ("NVIDIA GeForce RTX 3050 Laptop GPU", 0.0)


def test_nvidia_smi_failure_falls_back(monkeypatch):
    monkeypatch.setattr(hardware.shutil, "which", lambda _: "/usr/bin/nvidia-smi")

    def boom(*a, **k):
        raise subprocess.CalledProcessError(9, "nvidia-smi")

    monkeypatch.setattr(hardware.subprocess, "check_output", boom)
    assert hardware._detect_nvidia() is None
