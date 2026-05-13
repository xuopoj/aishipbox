"""TUI helpers via questionary plus a non-interactive field resolver."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import questionary

from aishipbox.core import strings


FieldSpec = Union[type, Tuple[type, Any]]
SpecDict = Dict[str, FieldSpec]


class MissingFieldsError(Exception):
    def __init__(self, fields: List[str]):
        self.fields = fields
        super().__init__(strings.MISSING_FLAGS_FOR_YES.format(fields=", ".join(fields)))


def _unpack(spec: FieldSpec):
    if isinstance(spec, tuple):
        return spec
    return (spec, None)


def resolve_fields(
    spec: SpecDict,
    flags: Dict[str, str],
    yes: bool,
) -> Dict[str, Any]:
    """Resolve fields from flags. If yes=True, missing-required fields raise."""
    result: Dict[str, Any] = {}
    missing: List[str] = []
    for name, fspec in spec.items():
        ftype, default = _unpack(fspec)
        if name in flags and flags[name] is not None:
            result[name] = ftype(flags[name])
        elif default is not None:
            result[name] = default
        else:
            if yes:
                missing.append(name)
    if missing:
        raise MissingFieldsError(missing)
    return result


def ask_text(message: str, default: Optional[str] = None) -> str:
    return questionary.text(message, default=default or "").ask()


def ask_select(message: str, choices: List[str], default: Optional[str] = None) -> str:
    return questionary.select(message, choices=choices, default=default).ask()


def ask_checkbox(message: str, choices: List[str]) -> List[str]:
    return questionary.checkbox(message, choices=choices).ask()


def ask_confirm(message: str, default: bool = False) -> bool:
    return questionary.confirm(message, default=default).ask()
