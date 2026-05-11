from aishipbox.core import strings


def test_required_keys_exist():
    required = [
        "UV_NOT_FOUND",
        "PROJECT_NOT_FOUND",
        "PROJECT_TYPE_MISMATCH",
        "TARGET_DIR_EXISTS",
        "MISSING_FLAGS_FOR_YES",
        "MANIFEST_INVALID",
        "OBS_CREDS_MISSING",
        "PACK_OUTPUT_EXISTS",
        "UNEXPECTED_ERROR",
        "NEXT_STEPS_HEADER",
    ]
    for key in required:
        assert hasattr(strings, key), f"missing string {key}"
        assert isinstance(getattr(strings, key), str)


def test_strings_are_chinese():
    """Spot-check that strings contain at least one CJK character."""
    sample = strings.UV_NOT_FOUND
    assert any("一" <= ch <= "鿿" for ch in sample), (
        f"expected Chinese characters in: {sample}"
    )
