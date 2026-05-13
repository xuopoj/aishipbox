"""Interactive wizard for `aishipbox op new`."""

from __future__ import annotations

from typing import Any, Dict

from aishipbox.core import strings, ui


def run_wizard(default_id: str) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    fields["id"] = ui.ask_text(strings.OP_FIELD_ID, default=default_id)
    fields["name"] = ui.ask_text(strings.OP_FIELD_NAME, default=fields["id"])
    fields["description"] = ui.ask_text(strings.OP_FIELD_DESCRIPTION, default="")
    fields["author"] = ui.ask_text(strings.OP_FIELD_AUTHOR, default="")
    fields["version"] = ui.ask_text(strings.OP_FIELD_VERSION, default="0.0.1")
    fields["category"] = ui.ask_select(strings.OP_FIELD_CATEGORY, strings.OP_CATEGORIES, default="其他")
    fields["modal"] = ui.ask_checkbox(strings.OP_FIELD_MODAL, strings.OP_MODALS) or ["OTHER"]
    fields["format"] = [s.strip() for s in ui.ask_text(strings.OP_FIELD_FORMAT, default="").split(",") if s.strip()]
    fields["language"] = [s.strip() for s in ui.ask_text(strings.OP_FIELD_LANGUAGE, default="zh").split(",") if s.strip()]
    fields["cpu_arch"] = [ui.ask_select(strings.OP_FIELD_CPU_ARCH, strings.OP_CPU_ARCHES, default="ARM")]
    fields["cpu"] = int(ui.ask_text(strings.OP_FIELD_CPU, default="1"))
    fields["memory"] = int(ui.ask_text(strings.OP_FIELD_MEMORY, default="2048"))
    fields["npu"] = int(ui.ask_text(strings.OP_FIELD_NPU, default="0"))
    fields["xpu_devices"] = ["SNT9B"] if fields["npu"] > 0 else []
    fields["auto_data_loading"] = ui.ask_confirm(strings.OP_FIELD_AUTO_DATA_LOADING, default=False)
    fields["skeleton"] = ui.ask_select(
        strings.OP_FIELD_SKELETON,
        [strings.OP_SKELETON_BLANK, strings.OP_SKELETON_TRANSFORM],
        default=strings.OP_SKELETON_TRANSFORM,
    ).split()[0]
    return fields
