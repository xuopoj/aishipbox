# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                # install deps (runtime + dev)
uv run pytest                          # unit tests (fast, no venv provisioning)
uv run pytest -m integration           # end-to-end; needs uv able to provide Python 3.9/3.10
uv run pytest tests/op/test_manifest.py::test_render_minimal -v   # one test
uv run aishipbox --help                # smoke the CLI
```

Integration tests call `uv venv --python <ver>`. In offline environments, set `UV_PYTHON_DOWNLOADS=never` and they'll skip cleanly rather than hang trying to fetch interpreters.

## Architecture

Three top-level subpackages with strict dependency direction:

```
aishipbox/cli.py          # thin dispatch only — never grows logic
       │
       ├── core/          # infrastructure: config, env, venv, packaging, ui, strings
       │                    knows nothing about algo or op
       ├── algo/          # MAS algorithm services (absorbed from mas-algo-cli)
       │                    Python 3.9 hosted runtime
       └── op/            # PanguLM custom operators (built fresh)
                            Python 3.10 hosted runtime
```

`algo/` and `op/` are **siblings, never import from each other**. Anything they'd both use belongs in `core/`.

## Invariants

- **Per-project venv.** `algo run` / `op run` always exec the project's `.venv/bin/python`, never `sys.executable`. Hosted Python versions live in `HOSTED_RUNTIMES` (core/config.py) — bump there when the platform changes; existing projects keep their pinned version via `.aishipbox.toml`.
- **`.aishipbox.toml` is the project marker.** Its `type` field routes in-project commands. Don't read project type from filenames.
- **All user-facing strings live in `core/strings.py`** (Chinese). Don't hardcode strings in commands — add a constant. The codebase grep-tests for English leaks.
- **`uv` is required at runtime**, not a fallback. `core.venv.require_uv()` raises `UvNotFound` instead of falling back to `python -m venv`.
- **moxing_mock is shadow-imported via PYTHONPATH** only during `op run` mock mode. Don't add it to the project's `requirements.txt`.

## Generated project layout

Each `aishipbox <type> new` writes a `.aishipbox.toml` (project marker) and `AGENTS.md` (agent guidance for that specific project, in Chinese). Per-project structure:

- **algo:** `main.py`, `requirements.txt`, `dependency/`, `lib/`, `.venv/` (3.9)
- **op:** `manifest.yml`, `program_package/{process.py,requirements.txt}`, `obs_input/`, `obs_output/` (mock), `.venv/` (3.10)

## Pack output format

- algo → `<name>.tar.gz` at the service dir (flat, no top-level folder).
- op → `program_package/<id>.tar` (uncompressed; matches the labelme2pascal example). Includes manifest.yml at archive root + everything in program_package/ except any prior `.tar`.

## Documentation

- Design: `docs/superpowers/specs/2026-05-11-aishipbox-design.md` — decisions and rationale
- Implementation plan: `docs/superpowers/plans/2026-05-11-aishipbox.md` — task-by-task TDD plan
- Reference operator: `resources/labelme2pascal_voc-workground/` (gitignored, kept locally)
- Reference for the absorb: `resources/mas-algo-cli/` (gitignored)

## What not to do

- Don't `import sys.executable` for project subprocess invocations.
- Don't add user-facing English strings; route through `core/strings.py`.
- Don't import from `aishipbox.algo` in `aishipbox.op` (or vice versa).
- Don't commit `resources/`; it's reference material, gitignored.
- Don't add `mas-algo-cli` as a runtime dep — it was absorbed.
