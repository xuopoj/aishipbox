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


def test_provision_tls_download_failure_gives_guidance(monkeypatch, tmp_path):
    uv_stderr = (
        "error: Request failed after 3 retries\n"
        "  Caused by: Failed to download https://github.com/astral-sh/"
        "python-build-standalone/releases/download/.../cpython-3.10.18...tar.gz\n"
        "  Caused by: invalid peer certificate: UnknownIssuer"
    )

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stderr = uv_stderr
        return R()

    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    with pytest.raises(venv_mod.VenvError) as exc:
        venv_mod.provision_venv(tmp_path, "3.10")
    msg = str(exc.value)
    assert "--native-tls" in msg           # actionable workaround flag
    assert "3.10" in msg                   # names the interpreter version
    assert "UnknownIssuer" in msg          # keeps the original detail


def test_provision_native_tls_passes_flag(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        class R:
            returncode = 0
            stderr = ""
        return R()

    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_mod.provision_venv(tmp_path, "3.10", native_tls=True)
    assert "--native-tls" in calls[0]

    calls.clear()
    venv_mod.provision_venv(tmp_path, "3.10")          # default: no flag
    assert "--native-tls" not in calls[0]
    assert "--allow-insecure-host" not in calls[0]


def test_provision_insecure_passes_allow_insecure_host(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        class R:
            returncode = 0
            stderr = ""
        return R()

    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(venv_mod.subprocess, "run", fake_run)

    venv_mod.provision_venv(tmp_path, "3.10", insecure=True)
    cmd = calls[0]
    assert "--allow-insecure-host" in cmd
    assert "github.com" in cmd                         # the interpreter-download host


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
