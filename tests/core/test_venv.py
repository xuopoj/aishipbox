import pytest

from aishipbox.core import venv as venv_mod


def _mock_uv(monkeypatch, calls, returncode=0, stderr=""):
    """Replace _run_uv with a recorder that returns a fixed (rc, stderr)."""
    monkeypatch.setattr(venv_mod.shutil, "which", lambda name: "/usr/bin/uv")

    def fake_run_uv(cmd):
        calls.append(cmd)
        return returncode, stderr
    monkeypatch.setattr(venv_mod, "_run_uv", fake_run_uv)


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
    _mock_uv(monkeypatch, [], returncode=1, stderr=uv_stderr)

    with pytest.raises(venv_mod.VenvError) as exc:
        venv_mod.provision_venv(tmp_path, "3.10")
    msg = str(exc.value)
    assert "--native-tls" in msg           # actionable workaround flag
    assert "3.10" in msg                   # names the interpreter version
    # raw uv error (UnknownIssuer) is streamed live, not duplicated in the message


def test_provision_native_tls_passes_flag(monkeypatch, tmp_path):
    calls = []
    _mock_uv(monkeypatch, calls)

    venv_mod.provision_venv(tmp_path, "3.10", native_tls=True)
    assert "--native-tls" in calls[0]

    calls.clear()
    venv_mod.provision_venv(tmp_path, "3.10")          # default: no flag
    assert "--native-tls" not in calls[0]
    assert "--allow-insecure-host" not in calls[0]


def test_provision_insecure_passes_allow_insecure_host(monkeypatch, tmp_path):
    calls = []
    _mock_uv(monkeypatch, calls)

    venv_mod.provision_venv(tmp_path, "3.10", insecure=True)
    cmd = calls[0]
    assert "--allow-insecure-host" in cmd
    assert "github.com" in cmd                         # the interpreter-download host


def test_provision_calls_uv(monkeypatch, tmp_path):
    calls = []
    _mock_uv(monkeypatch, calls)

    venv_mod.provision_venv(tmp_path, "3.10")

    assert calls[0][:5] == ["/usr/bin/uv", "venv", "--python", "3.10", str(tmp_path / ".venv")]


def test_ensure_package_installs_when_missing(monkeypatch, tmp_path):
    installed = []
    # module not importable in the project venv -> install it
    monkeypatch.setattr(venv_mod, "_module_available", lambda project_dir, mod: False)
    monkeypatch.setattr(venv_mod, "pip_install", lambda project_dir, *pkgs: installed.extend(pkgs))

    venv_mod.ensure_package(tmp_path, "debugpy", "debugpy>=1.8.0")
    assert installed == ["debugpy>=1.8.0"]


def test_ensure_package_skips_when_present(monkeypatch, tmp_path):
    installed = []
    monkeypatch.setattr(venv_mod, "_module_available", lambda project_dir, mod: True)
    monkeypatch.setattr(venv_mod, "pip_install", lambda project_dir, *pkgs: installed.extend(pkgs))

    venv_mod.ensure_package(tmp_path, "debugpy", "debugpy>=1.8.0")
    assert installed == []          # already there, no install


def test_run_uv_streams_and_captures_stderr(monkeypatch, capsys):
    # _run_uv tees uv's stderr: each line goes live to our stderr AND is captured.
    class FakeProc:
        def __init__(self):
            self._lines = iter(["Downloading pandas (11MiB)\n", "Installed 4 packages\n"])
            self.returncode = 0

        @property
        def stderr(self):
            return self

        def __iter__(self):
            return self._lines

        def wait(self):
            return 0

    def fake_popen(cmd, **kwargs):
        # caller must request line-buffered text stderr piping
        assert kwargs.get("stderr") == venv_mod.subprocess.PIPE
        assert kwargs.get("text") is True
        return FakeProc()

    monkeypatch.setattr(venv_mod.subprocess, "Popen", fake_popen)

    rc, captured = venv_mod._run_uv(["uv", "pip", "install", "pandas"])
    assert rc == 0
    assert "Downloading pandas" in captured          # captured for error detection
    err = capsys.readouterr().err
    assert "Downloading pandas" in err               # AND streamed live to the user
