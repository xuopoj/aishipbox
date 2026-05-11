import pytest

from aishipbox.core import venv as venv_mod


def test_python_executable_for_existing_venv(tmp_path):
    venv_dir = tmp_path / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    py = venv_dir / "bin" / "python"
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)
    assert venv_mod.python_executable(tmp_path) == py


def test_python_executable_missing_raises(tmp_path):
    with pytest.raises(venv_mod.VenvError):
        venv_mod.python_executable(tmp_path)


def test_uv_required_raises_when_missing(monkeypatch):
    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: None)
    with pytest.raises(venv_mod.UvNotFound):
        venv_mod.require_uv()


def test_provision_calls_uv(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        class R:
            returncode = 0
            stderr = ""
        return R()

    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_mod.provision_venv(tmp_path, "3.10")

    assert calls[0][:5] == ["/usr/bin/uv", "venv", "--python", "3.10", str(tmp_path / ".venv")]
