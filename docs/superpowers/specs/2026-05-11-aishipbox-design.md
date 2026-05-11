# aishipbox — Design Doc

**Date:** 2026-05-11
**Status:** Draft, pending review

## Context

JAC has two adjacent kinds of artifacts targeting Huawei PanguLM infrastructure:

1. **MAS algorithm services** — a hosted-HTTP-service pattern. Existing CLI `mas-algo-cli` (binary `algo`) already supports `new / run / pack / debug / stubs / install-deps`. Hosted runtime: **Python 3.9**. Project shape: `main.py` with an `AlgoProcessor` class, `requirements.txt`, optional `dependency/` and `lib/`; packaged as a flat `.tar.gz`.
2. **PanguLM custom operators** — a batch-processing pattern referenced at https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html. The only existing example is `labelme2pascal_voc-workground/`. Hosted runtime: **Python 3.10**. Project shape: `manifest.yml` (id, name, category, modal, runtime/cpu-arch/resources, entrypoint, arguments) + `program_package/process.py` (a `Process` class with `__call__`). Uses Huawei `moxing` for OBS I/O. Packaged as `program_package/<name>.tar`.

There is no tooling for operators today; users hand-edit YAML and zip files manually. The two artifact types share enough shape (new / run / debug / pack) that a unified CLI is worth the up-front investment.

## Goals

- One CLI, `aishipbox`, that supports `new / run / debug / pack` for both project types.
- Lower the cost of creating a correct operator from scratch via an interactive wizard.
- Local debugging for both types without needing real OBS access.
- Python-3.x-version mismatches between the tool and the hosted runtimes are invisible to the user.
- AI-agent-friendly: every generated project ships with an `AGENTS.md` explaining the project type, runtime, entry points, and gotchas.

## Non-Goals

- Replacing or wrapping the hosted platform's deployment APIs. `pack` produces an archive; uploading it is out of scope.
- Bilingual UI. Chinese-only for now (target audience), extracted strings can be i18n'd later if needed.
- Supporting any third artifact type in v1.
- Editing/migrating existing manually-built operators (the wizard targets greenfield).
- Replacing IDE workflows. `debug` writes a VS Code `launch.json`; other editors are not a v1 concern.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| Binary name | `aishipbox` | Matches package, distinctive, user choice |
| CLI surface | Type-prefixed: `aishipbox algo …`, `aishipbox op …` | Explicit, scales if a 3rd type appears |
| Relationship to mas-algo-cli | **Absorb**: copy code into `aishipbox/algo/`, retire the standalone package | Single source, no version skew |
| Distribution | Python package, `uv tool install aishipbox` | Reuses absorbed code; `uv` ships its own Python |
| Tool runtime | Python 3.10+ (whatever uv provisions) | Decoupled from hosted runtimes |
| Service runtime | Per-project venv via `uv venv --python <hosted>` | algo→3.9, op→3.10 today; both can evolve |
| UI language | Chinese-only | Target users are Chinese; English `--help` is a stretch goal |
| Op `new` UX | Interactive `questionary` wizard, OR `--yes` + flags for scripting | Many manifest fields; wizard is friendlier |
| Op local debug | Mock `moxing` against local FS by default; `--obs` flag for real | Fast iteration without OBS credentials |
| Per-project marker | `.aishipbox.toml` with `{type, runtime, schema_version}` | Routes in-project commands; survives version bumps |
| Agent guidance | `AGENTS.md` generated into each new project | One file, broadly-recognized convention |

## Architecture

```
aishipbox/
├── cli.py                 # argparse entry; routes `aishipbox <type> <command>`
├── __main__.py
├── core/
│   ├── config.py          # AishipboxConfig (hosted py versions); ProjectConfig (.aishipbox.toml)
│   ├── venv.py            # uv-based venv provisioning, interpreter discovery
│   ├── env.py             # .env loader shared by both runners
│   ├── packaging.py       # tarball builder + exclude-pattern engine
│   ├── ui.py              # questionary wrappers + non-interactive resolver (flags + --yes)
│   └── strings.py         # Chinese string constants (one place for translation later)
├── algo/                  # absorbed mas-algo-cli
│   ├── commands/          # new, run, pack, debug, stubs, install_deps
│   ├── templates/         # basic, predict, cv (verbatim from mas-algo-cli)
│   ├── stubs/             # rest-stubs package
│   └── runner.py          # local HTTP server
└── op/
    ├── commands/          # new, run, pack, debug
    ├── wizard.py          # interactive manifest builder
    ├── manifest.py        # parse/serialize/validate manifest.yml
    ├── moxing_mock.py     # local-FS shim for `mox.file.*`
    ├── templates/         # process.py skeleton(s), .env.example, .gitignore, AGENTS.md
    └── runner.py          # `op run` entrypoint (mock or real moxing)
```

**Invariants:**
- `core/` knows nothing about `algo` or `op`.
- `algo/` is a faithful absorb of mas-algo-cli; minimal edits beyond import paths.
- `op/` is new code built on `core/`.
- `cli.py` is thin dispatch only.

### Per-project state (in user workspace)

```
my_op/
├── manifest.yml
├── program_package/
│   ├── process.py
│   └── requirements.txt
├── .venv/                 # uv venv on Python 3.10
├── .env / .env.example    # OBS creds for --obs mode
├── .aishipbox.toml        # {type="op", runtime="3.10", schema_version=1}
├── AGENTS.md              # agent guidance for this project
├── obs_input/             # mock-mode input (gitignored)
└── obs_output/            # mock-mode output (gitignored)
```

```
my_algo/
├── main.py                # AlgoProcessor
├── requirements.txt
├── dependency/            # offline .whl
├── lib/                   # .so (optional)
├── .venv/                 # uv venv on Python 3.9
├── .env / .env.example
├── .aishipbox.toml        # {type="algo", runtime="3.9", schema_version=1}
└── AGENTS.md
```

## CLI surface

```
aishipbox algo new <name> [-t basic|predict|cv] [--yes]
aishipbox algo run [path] [-p PORT] [--debug] [--debug-port PORT]
aishipbox algo pack [path] [-o OUTPUT]
aishipbox algo debug [path]
aishipbox algo stubs
aishipbox algo install-deps

aishipbox op new <name>
                  [--id ID] [--description …] [--author …] [--version …]
                  [--category …] [--modal …] [--cpu-arch …]
                  [--cpu N] [--memory MB] [--npu N]
                  [--auto-data-loading] [--skeleton blank|transform]
                  [--yes]
aishipbox op run [path] [--obs] [--debug]
aishipbox op pack [path] [-o OUTPUT] [--force]
aishipbox op debug [path]

aishipbox --version
```

## Per-command flows

### `aishipbox op new <name>`

1. Resolve target dir; refuse if exists.
2. **Interactive (default):** launch `questionary` wizard.
   - id (default = dir name), name, description, author, version (default `0.0.1`)
   - category — multi-select from {数据提取/抽样/转换/过滤/去重/打标/其他}
   - modal — multi-select from {TEXT, IMAGE, VIDEO, AUDIO, OTHER}
   - format, language — free-text or preset
   - cpu-arch — {arm, x86}
   - resources (cpu/memory/npu, defaults 1/2048/0)
   - auto-data-loading (y/n)
   - arguments — loop: name/type/desc, blank to finish
   - skeleton — {blank, transform-with-moxing}
3. **Non-interactive (`--yes`):** all fields resolved from flags. If `--yes` is set without enough flags, print a Chinese list of missing required fields and exit 2.
4. Render `manifest.yml`, `program_package/process.py`, `program_package/requirements.txt`, `.env.example`, `.gitignore`, `.aishipbox.toml`, `AGENTS.md`.
5. Provision venv: `uv venv --python 3.10 .venv`. Refuse if `uv` is not on PATH.
6. Install deps from `requirements.txt` + a thin `moxing_mock` shim into the venv (the shim makes `import moxing as mox` work locally even before real moxing is installed).
7. Print Chinese next-steps block.

### `aishipbox op run [path] [--obs] [--debug]`

1. Locate project root by walking up from `path` for `.aishipbox.toml`; verify `type == "op"`.
2. Load `.env`.
3. **Default (mock mode):** prepend bundled `moxing_mock` to `PYTHONPATH` so `import moxing` resolves to the shim. `obs_input_path` and `obs_output_path` env vars resolve to local `obs_input/` and `obs_output/` dirs.
4. **`--obs` mode:** require `OBS_AK`, `OBS_SK`, `OBS_ENDPOINT`, `OBS_INPUT_PATH`, `OBS_OUTPUT_PATH` in `.env`; use real `moxing` from venv. Error with field-list if any are missing.
5. **`--debug`:** wrap process invocation with `debugpy --listen 5678 --wait-for-client`.
6. Exec `.venv/bin/python program_package/process.py`, passing args parsed from `manifest.yml`'s `arguments` list.

### `aishipbox op debug [path]`

Write `.vscode/launch.json` with a debugpy attach config (port 5678) and a clear name "Attach to Op Service" (Chinese label). Idempotent.

### `aishipbox op pack [path] [-o OUTPUT] [--force]`

1. Validate `manifest.yml` against schema (required fields, semver regex on version, allowed values for category/modal/cpu-arch).
2. Validate `program_package/process.py` exists and defines a `Process` class.
3. Determine output: `OUTPUT` if given, else `program_package/<id>.tar` (uncompressed, to match the labelme2pascal example).
4. Refuse if output exists unless `--force`.
5. Build tar from `program_package/` contents, excluding `__pycache__`, `.DS_Store`, `*.pyc`, prior `*.tar`. `manifest.yml` inclusion: **TBD until Huawei spec is verified** — initial implementation will include it at the archive root; can be flipped to "outside the tar" later.

### `aishipbox algo new|run|pack|debug|stubs|install-deps`

Behavior unchanged from mas-algo-cli today, with these modifications:
- Output strings translated to Chinese.
- `new` provisions a per-project venv on Python 3.9 via `uv venv --python 3.9 .venv` (instead of relying on a workspace-shared venv).
- `new` writes `.aishipbox.toml` and `AGENTS.md`.
- `run` / `debug` / `pack` route via `.aishipbox.toml` to verify project type.

## moxing_mock

A bundled package shadowed onto `PYTHONPATH` before `import moxing`. Implements the minimum surface used by real operators:

```python
# aishipbox/op/moxing_mock/moxing/file.py

def list_directory(path, recursive=False): ...
def copy(src, dst): ...
def exists(path): ...
def make_dirs(path): ...
```

All paths beginning with `obs://` are mapped to a configurable local root (`obs_input/`, `obs_output/`). Other paths pass through. This keeps user code unchanged between mock and real modes.

## Configuration

**Tool-level constants (in `core/config.py`):**
```python
HOSTED_RUNTIMES = {"algo": "3.9", "op": "3.10"}
SCHEMA_VERSION = 1
```
Bumped when hosted runtimes evolve. Existing projects keep their pinned runtime via `.aishipbox.toml`.

**Per-project (`.aishipbox.toml`):**
```toml
schema_version = 1
type = "op"            # or "algo"
runtime = "3.10"       # frozen at creation time
created_at = "2026-05-11T14:23:00Z"
```

## Error handling

- Fail fast at entry; never start expensive work after a recoverable validation error.
- Chinese messages with an actionable next step.
- Stack traces hidden by default; `AISHIPBOX_DEBUG=1` shows them.

| Case | Behavior |
|---|---|
| `uv` not on PATH | Refuse at startup, print install hint |
| `op|algo run` outside a project | Reference `.aishipbox.toml`, suggest `new` |
| Project type mismatch (`op run` in algo dir) | Show detected type, suggest correct command |
| `op new`: target dir exists | Refuse; no partial scaffold |
| `op new`: wizard cancelled | Clean up any partially-written dir |
| `op new --yes` missing required flags | List all missing fields, exit 2 |
| `op pack`: manifest invalid | Print all schema errors at once, exit 1 |
| `op run --obs` missing credentials | List missing env vars, exit 1 |
| `pack` output exists | Refuse unless `--force` |

Shared: command handlers return `int`; `cli.py` calls `sys.exit(...)`. Escaping exceptions print a Chinese "unexpected error" message + the `AISHIPBOX_DEBUG=1` hint.

## Testing

**Unit (pytest, fast):**
- `core/venv.py` — provision/locate, with `uv` mocked.
- `core/packaging.py` — tar build, exclude patterns.
- `op/manifest.py` — parse/serialize/validate; golden file tests.
- `op/moxing_mock.py` — `list_directory`/`copy` against `tmp_path`.
- `op/wizard.py` — field validators (no TUI interaction).
- `core/strings` — sanity grep: no English leaks in user-facing strings.

**Integration (`@pytest.mark.integration`):**
- `aishipbox op new my_op --yes --category transform --modal IMAGE ...` end-to-end → assert files + venv.
- `aishipbox op run` in mock mode → drop sample inputs, assert outputs.
- `aishipbox op pack` → unpack the tar, assert structure.
- Same trio for algo (`new --yes -t basic`, `run`, `pack`).

**Not tested:**
- Real OBS calls (`--obs`).
- Interactive wizard UX (manual smoke).
- Hosted-platform deployment.

**CI:** GitHub Actions matrix on Linux/macOS, Python 3.10. Integration jobs install `uv` in the runner.

## Distribution

- Built with `hatchling` (matches mas-algo-cli today).
- Published to PyPI as `aishipbox`.
- Entry point: `aishipbox = "aishipbox.cli:main"` plus `pyproject.toml` script.
- Install: `uv tool install aishipbox` (recommended) or `pipx install aishipbox`.
- Runtime requirement: `requires-python = ">=3.10"` for the tool itself.
- Hard runtime dep: `questionary`, `pyyaml`, `tomli` (or stdlib `tomllib` on 3.11+). `debugpy` only when the user runs in debug mode (bundled but optional).

## AGENTS.md content (generated)

Each new project gets an `AGENTS.md` in its root. Contents are Chinese; structure is shared:

```markdown
# AGENTS.md

本项目类型：<op|algo>
托管运行时：Python <3.10|3.9>
工具：aishipbox vX.Y.Z

## 入口
- op:   program_package/process.py 中的 Process 类（实现 __call__）
- algo: main.py 中的 AlgoProcessor 类

## 常用命令
- 本地调试：  aishipbox <op|algo> run
- 真实 OBS：  aishipbox op run --obs   (仅 op)
- 打包：      aishipbox <op|algo> pack

## 关键约束
- op 使用 moxing 进行 OBS I/O；本地默认走 obs_input/ 与 obs_output/ 镜像。
- algo 部署到 MAS 托管服务，遵循 main.py + requirements.txt 结构。
- 不要修改 .aishipbox.toml 的 schema_version / type 字段。

## 平台参考
- 算子手册：  https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html
```

## Open spec items (deferred, do not block implementation)

1. **Operator pack archive layout.** The example shows `program_package/<name>.tar` but it's unclear whether `manifest.yml` lives inside the tar at root or alongside `program_package/`. Initial implementation: include at archive root, behind a feature flag so we can flip later without re-architecting.
2. **moxing_mock surface completeness.** Will start from what `process.py` in labelme2pascal touches (`list_directory`, `copy`); extend as real operators reveal additional methods (`exists`, `make_dirs`, `read`, `write`).
3. **Algo wizard.** Out of scope for v1; keep mas-algo-cli's simple template picker. Add a wizard later if operator UX proves valuable.

## Migration / rollout

- The initial aishipbox release absorbs mas-algo-cli's source into `aishipbox/algo/` directly (per the Absorb decision above); aishipbox does not depend on mas-algo-cli at runtime.
- A short migration note in aishipbox's README explains the `algo new` → `aishipbox algo new` rename and the move to a per-project venv.
- mas-algo-cli is marked deprecated on PyPI once aishipbox v0.1 ships, with a pointer to aishipbox.

## Risks

- **Operator hosted runtime is moving** (currently 3.10). The `HOSTED_RUNTIMES` constants need updating; existing projects will not break because runtime is pinned per-project.
- **Huawei docs not directly fetchable** from this environment; some spec details (esp. pack archive layout) will need user confirmation.
- **questionary terminal compatibility** — Windows terminals can be quirky. Fallback path: if `questionary` cannot start (no TTY), error and instruct the user to use `--yes` + flags.
