# aishipbox

JAC PanguLM 算法服务（algo）与自定义算子（op）开发 CLI。

把平台上线前后的本地等价开发环境收敛到一条命令链：脚手架、虚拟环境、本地 mock、调试、打包。

## 安装

```bash
uv tool install aishipbox
```

更新已安装的工具：

```bash
uv tool install --reinstall aishipbox        # 从 PyPI
uv tool install --reinstall .                # 从当前源码（dev）
```

## 设计

两个子命令完全隔离：项目结构、骨架模板、运行模型、打包格式独立演进。共用的基础设施（venv、env、字符串、packaging）放在 `core/`。

```
aishipbox/cli.py     # 仅做分发
├── core/            # 共用基础设施
├── algo/            # JAC 算法服务（HTTP/gRPC 微服务），Python 3.9
└── op/              # PanguLM 自定义算子（数据集流水线节点），Python 3.10
```

`algo` 与 `op` **互不依赖**；公共逻辑都在 `core/`。

## 快速开始

### 算法服务（algo）

```bash
aishipbox algo new my_algo -t basic         # basic / predict / cv
cd my_algo
aishipbox algo run                          # 本地起服务
aishipbox algo pack                         # 打 tar.gz
```

### 自定义算子（op）

```bash
aishipbox op new my_op                      # 交互向导（questionary）
cd my_op
# 把测试数据放入 obs_input/
aishipbox op run                            # mock 模式（默认）
aishipbox op run --obs                      # 真实 OBS（读取 .env）
aishipbox op run --debug                    # 等 VS Code 在端口 5678 附加
aishipbox op debug                          # 生成 .vscode/launch.json
aishipbox op pack                           # 打 program_package/<id>.tar
```

非交互向导（脚本/CI）：

```bash
aishipbox op new my_op --yes \
  --id my_op --op-name 示例 --version 0.0.1 \
  --category 数据转换 --modal IMAGE \
  --cpu-arch ARM --cpu 1 --memory 2048 --npu 0 \
  --auto-data-loading=false --skeleton transform
```

## 算子两种模式

由 `manifest.yml > runtime > auto-data-loading` 控制，op runner 在本地透明 emulate 平台行为。

| 模式 | 设置 | 输入 | 输出 | 适用 |
|---|---|---|---|---|
| 模式一 | `auto-data-loading: true` | 框架按文件类型构造 DataFrame，**逐文件**调用 PreProcess→Process→PostProcess | 算子返回 DataFrame；mock 模式下汇总写入 `obs_output/result.jsonl` | 单模态、按样本/按文件处理 |
| 模式二 | `auto-data-loading: false` | 空 DataFrame，算子自行从 `args.obs_input_path` 读取 | 无返回值，算子自行写 `args.obs_output_path` | 多模态、跨样本（如去重）、非标准输出模态 |

### 模式一的 DataFrame 形状（按文件扩展名分派）

| 扩展名 | DataFrame 列 | 来源 |
|---|---|---|
| `.jsonl` | 文件自身字段 | `pd.read_json(..., lines=True)` |
| `.csv` | 文件自身字段 | `pd.read_csv` |
| `.parquet` | 文件自身字段 + 系统注入 `file_path` / `file_name` | `pd.read_parquet`（需 pyarrow） |
| 其他 | 单行 `file_path` + `file_name` | runner 枚举文件 |

同一 `obs_input/` 目录禁止混合上述类型 —— runner 会失败并提示改用模式二。多模态请用模式二。

## 本地 mock 基础设施

`op run` 默认使用 mock 模式，把平台依赖在本地等价模拟：

- **`moxing.file`** — 18 个 API：`list_directory` / `copy` / `copy_parallel` / `read` / `write` / `append` / `glob` / `walk` / `stat` / `exists` / `is_directory` / `make_dirs` / `mk_dir` / `remove` / `rename` / `get_size` / `scan_dir` / `File`
- **`ma_utils.FileLogger.get_logger()`** — 平台标准日志入口，本地返回配置好格式的 stdlib logger
- **路径解析**：`obs://input/` → `obs_input/`，`obs://output/` → `obs_output/`；**其他 bucket 名**会立即报错（只在两条 mock 路径上保证等价）

为了避免 "本地通过、平台失败" 的 API 差异（pandas 1.3 ↔ 2.x、numpy 1 ↔ 2 都有真实破坏性变更），`aishipbox op new` 在新建项目时把平台预置的 `pandas==1.3.5` / `numpy==1.26.4` / `pyarrow==18.0.0` 装到本地 `.venv/`。这些版本来自 `aishipbox/core/config.py` 的 `PLATFORM_PRESET_PINS` 常量，**不会**写进 `program_package/dependency/requirements.txt` —— 那个文件会被打入算子包，平台 `pip install --no-index` 不应该被要求重装已预置的包。

## 项目结构

每个项目都包含 `.aishipbox.toml`（项目类型与运行时标记）、`AGENTS.md`（AI agent 专属操作指南）、独立的 `.venv/`（algo: 3.9, op: 3.10）。

算子项目额外包含：

```
my_op/
├── manifest.yml                      # 算子元数据（id/name/modal/runtime/arguments/labels...）
├── program_package/
│   ├── process.py                    # 必填，算子主实现
│   ├── dependency/
│   │   └── requirements.txt          # 平台预置之外的依赖
│   └── install.sh.example            # 自定义安装步骤模板
├── obs_input/  obs_output/           # 本地 mock 输入/输出
├── .env.example                      # --obs 模式凭据模板
├── AGENTS.md  .aishipbox.toml  .gitignore
└── .venv/                            # uv venv --python 3.10
```

打包结果：`program_package/<id>.tar`（未压缩）。归档内部按平台规范嵌套于 `<id>/` 之下。

## 文档

- 设计：`docs/superpowers/specs/2026-05-11-aishipbox-design.md`
- 实施计划：`docs/superpowers/plans/2026-05-11-aishipbox.md`
- PanguLM 算子手册：https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html
- MoXing API：https://support.huaweicloud.com/usermanual-standard-modelarts/modelarts_11_0001.html

## 开发

```bash
uv sync                                      # 装运行 + dev 依赖
uv run pytest                                # 单元测试（~100 个）
uv run pytest -m integration                 # 端到端（需要 uv 取得 Python 3.9/3.10）
uv run pytest tests/op/test_runner.py -v     # 单文件
uv tool install --reinstall .                # 重装全局 aishipbox（从当前源码）
```

离线环境跑集成测试：`UV_PYTHON_DOWNLOADS=never uv run pytest -m integration`，集成测试会自行 skip 而不是 hang。

测试分层：
- **单元** —— `tests/algo/` `tests/op/` `tests/core/`：纯逻辑，无 venv
- **集成** —— `tests/integration/`：通过 `uv venv --python <ver>` 起真实项目 venv 跑完整 `new → run → pack`
