from aishipbox.core.env import load_env_file


def test_load_basic(tmp_path):
    env = tmp_path / ".env"
    env.write_text("FOO=bar\nBAZ=qux\n")
    assert load_env_file(env) == {"FOO": "bar", "BAZ": "qux"}


def test_load_skips_comments_and_blanks(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\n\nFOO=bar\n  # indented comment\nBAZ=qux\n")
    assert load_env_file(env) == {"FOO": "bar", "BAZ": "qux"}


def test_load_strips_quotes(tmp_path):
    env = tmp_path / ".env"
    env.write_text('FOO="bar baz"\nQ=\'single\'\n')
    assert load_env_file(env) == {"FOO": "bar baz", "Q": "single"}


def test_load_missing_returns_empty(tmp_path):
    assert load_env_file(tmp_path / ".env") == {}
