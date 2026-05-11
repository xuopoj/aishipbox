import pytest

from aishipbox.core.ui import resolve_fields, MissingFieldsError


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
