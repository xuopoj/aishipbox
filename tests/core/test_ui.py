import io
import sys

import pytest

from aishipbox.core.ui import resolve_fields, MissingFieldsError, stdin_is_interactive


def test_resolve_fields_all_provided():
    spec = {"id": str, "cpu": int}
    result = resolve_fields(spec, flags={"id": "abc", "cpu": "2"}, yes=True)
    assert result == {"id": "abc", "cpu": 2}


def test_resolve_fields_missing_required_raises():
    spec = {"id": str, "cpu": int}
    with pytest.raises(MissingFieldsError) as exc:
        resolve_fields(spec, flags={"id": "abc"}, yes=True)
    assert "cpu" in exc.value.fields


def test_resolve_fields_uses_defaults_when_yes():
    spec = {"id": str, "cpu": (int, 1)}
    result = resolve_fields(spec, flags={"id": "abc"}, yes=True)
    assert result == {"id": "abc", "cpu": 1}


def test_stdin_is_interactive_false_for_non_tty(monkeypatch):
    # A piped/redirected stdin (StringIO) is not a TTY.
    monkeypatch.setattr(sys, "stdin", io.StringIO("data"))
    assert stdin_is_interactive() is False


def test_stdin_is_interactive_false_when_stdin_none(monkeypatch):
    monkeypatch.setattr(sys, "stdin", None)
    assert stdin_is_interactive() is False


def test_stdin_is_interactive_true_for_tty(monkeypatch):
    class _TTY:
        def isatty(self):
            return True
    monkeypatch.setattr(sys, "stdin", _TTY())
    assert stdin_is_interactive() is True
