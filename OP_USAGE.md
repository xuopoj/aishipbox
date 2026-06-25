# 自定义算子（op）使用指南

本指南从概念到工具到 agent 协作，分四部分：

1. [什么是自定义算子](#1-什么是自定义算子)
2. [怎么构建自定义算子（平台契约）](#2-怎么构建自定义算子平台契约)
3. [使用 aishipbox 构建算子](#3-使用-aishipbox-构建算子)
4. [用 coding agent 配合 aishipbox 快速构建](#4-用-coding-agent-配合-aishipbox-快速构建)

> 前置：先装好 uv 与 aishipbox，见 [INSTALL_UV.md](INSTALL_UV.md)，然后 `uv tool install aishipbox`。托管运行时为 **Python 3.10**。

---

## 1. 什么是自定义算子

自定义算子（custom operator）是 ModelArts Studio / PanguLM **数据集加工流水线**里的一个处理节点。平台把数据集按你声明的方式喂给算子，算子做一段处理（提取、抽样、转换、过滤、去重、打标……），产出加工后的数据。

一个算子要回答三个问题：

- **它是什么** —— 元数据：ID、名称、版本、处理类别、数据模态、资源需求、可调参数。这些写在 `manifest.yml`。
- **它怎么处理数据** —— 实现：`process.py` 里的 `Process` 类。平台按接口协议调用它。
- **它怎么部署** —— 打包：按平台规范打成一个 `.tar`，上传到平台。

算子运行在平台托管的 Linux 容器里（**Python 3.10**，ARM 或 X86），通过 `moxing`（OBS 对象存储访问）和 `ma_utils`（日志）等平台 SDK 与基础设施交互。基础镜像预装约 250 个常用包（pandas/numpy/torch/transformers/pyarrow/opencv-python/pillow/moxing-framework 等）。

**aishipbox 的作用**：把上述「写 manifest → 写实现 → 本地验证 → 打包」整条链路收敛成几条命令，并在本地用 mock 等价模拟平台的 `moxing` / `ma_utils` / OBS 路径，让你在上传前就能跑通。

---

## 2. 怎么构建自定义算子（接口定义）

这一节讲**算子接口定义**，与具体工具无关。第 3 节再讲 aishipbox 如何把这些自动化。

### 2.1 manifest.yml —— 算子是什么

声明元数据与可调参数。关键字段：

- 顶层：`id`（英文字母开头、`[A-Za-z0-9_]`、≤128、创建后不可变）、`name`、`version`（`x.y.z`）、`description`、`author`。
- `tags`：`category`（单选：数据提取/抽样/转换/过滤/去重/打标/其他）、`modal`（TEXT/IMAGE/VIDEO/AUDIO/OTHER）、`language`、`format`。
- `runtime`：`cpu-arch`（ARM / X86）、`resources`（cpu/memory/npu）、`environment: python`、`entrypoint: process.py`、`auto-data-loading`（见 2.3）。
- `arguments`：业务参数（STRING/FLOAT/INT/ENUM/LIST/OBS/BOOLEAN…），运行时挂到 `args.<key>`。
- `labels`：打标类算子的输出标签定义。

> 完整字段规范（类型、必填/可选、枚举、示例）见每个 aishipbox 项目自带的 `AGENTS.md`。

### 2.2 process.py —— 算子怎么处理数据

入口是 `Process` 类（必填，实现 `__call__`）。平台按 **PreProcess → Process → PostProcess** 顺序调用，前后两个可选：

```python
class PreProcess:                 # 可选；CPU 侧轻量预处理，提升 NPU 利用率
    def __init__(self, args): ...
    def __call__(self, input): ...

class Process:                    # 必填；模型加载与推理主逻辑
    def __init__(self, args): ...
    def __call__(self, input): ...

class PostProcess:                # 可选；推理后 CPU 侧处理
    def __init__(self, args): ...
    def __call__(self, input): ...
```

- `__init__` 整次运行**只调一次**（适合加载模型 / 分配状态）。
- `args` 是框架注入的对象，含 `args.obs_input_path` / `args.obs_output_path`，以及 manifest 里声明的业务参数（`args.<key>`）。
- 日志用平台入口，**不要**用 `logging.basicConfig`：

  ```python
  import ma_utils as utils
  logger = utils.FileLogger.get_logger()
  ```

### 2.3 两种运行模式（auto-data-loading）

由 `manifest.yml > runtime > auto-data-loading` 决定，是构建算子时最重要的一个选择：

| 模式 | 设置 | 输入 | 输出 | 适用 |
|---|---|---|---|---|
| **模式一** | `true` | 框架按文件类型构造 pandas.DataFrame，**逐文件**调用算子链 | `__call__` 返回 DataFrame，框架写回 | 单模态、按样本/按文件处理 |
| **模式二** | `false` | 空 DataFrame；自行从 `args.obs_input_path` 读 | 无返回值，自行写 `args.obs_output_path` | 多模态、跨样本（如去重）、非标准输出 |

**模式一 DataFrame 形状**（按输入文件扩展名分派）：

| 扩展名 | DataFrame 列 |
|---|---|
| `.jsonl` / `.csv` | 文件自身字段 |
| `.parquet` | 文件自身字段 + 注入 `file_path` / `file_name` |
| 其他 | 单行 `file_path` + `file_name` |

模式一要求：`__call__` 每文件调一次、必须返回 DataFrame；同一输入目录**不能混合**上述类型。需要多模态/跨样本就用模式二。

### 2.4 OBS 访问（moxing.file）

无论哪种模式，文件 I/O 都走 `moxing`：

```python
import moxing as mox
mox.file.copy("obs://input/a.jpg", "obs://output/a.jpg")
mox.file.list_directory("obs://input/", recursive=True)
data = mox.file.read("obs://input/a.txt")
mox.file.write("obs://output/b.txt", "...")
# 另有 copy_parallel / append / exists / glob / walk / stat / remove / rename / ...
```

### 2.5 打包规范

平台要求算子包是一个 `.tar`，内部按算子 `id` 嵌套：

```
<id>/
├── manifest.yml
└── program_package/
    ├── process.py
    ├── dependency/requirements.txt   # 平台没有的额外依赖
    └── install.sh                    # 可选，自定义安装步骤
```

平台运行时执行 `pip install --no-index --find-links=./dependency -r ./dependency/requirements.txt` —— `--no-index` 意味着只能从 `dependency/` 找 wheel，所以预装包不要写进 `requirements.txt`，且额外依赖的 wheel 必须是 Linux + Python 3.10 + 对应架构。

---

## 3. 使用 aishipbox 构建算子

aishipbox 把第 2 节的契约自动化。命令速查：

```bash
aishipbox op new <name> [flags]    # 新建项目（脚手架 + venv + 预置包）
aishipbox op run [path]            # 本地运行（默认 mock 模式）
aishipbox op run --obs             # 用真实 OBS 运行（读 .env）
aishipbox op run --debug           # 启动后等 VS Code 在 5678 端口附加
aishipbox op debug [path]          # 生成 .vscode/launch.json
aishipbox op download <pkg> [path] # 下载依赖 wheel 到 dependency/ 并写 requirements.txt
aishipbox op pack [path]           # 打包成 program_package/<id>.tar
```

`path` 默认当前目录；命令多在算子项目根目录内执行。

### 3.1 op new —— 新建项目

**交互式（人工首次使用）：**

```bash
aishipbox op new my_op
```

进入向导逐项填写 ID/名称/版本/类别/模态/架构/资源/模式/骨架。

**非交互式（脚本 / agent）：** 带 `--yes` 即可，未提供的字段用默认值填充：

```bash
aishipbox op new my_op --yes                                  # 全默认
aishipbox op new my_op --yes \                                # 或只覆盖关心的字段
  --category 数据转换 --modal IMAGE --auto-data-loading=false --skeleton transform
```

字段默认值（与向导一致）：`id`/`name`=项目名、`version`=`0.0.1`、`category`=`其他`、`modal`=`[OTHER]`、`cpu-arch`=`[ARM]`、`cpu`=`1`、`memory`=`2048`、`npu`=`0`、`auto-data-loading`=`false`、`skeleton`=`transform`。可选值见项目内 `AGENTS.md`。

> 非交互环境（管道 / 无 TTY）下漏掉 `--yes` 不会卡在向导上 —— 会立即报错提示改用 `--yes`，退出码 `2`。

`--skeleton` 选 `blank`（空白）或 `transform`（含 moxing 文件拷贝示例，对应模式二）。

新建后的目录：

```
my_op/
├── manifest.yml                      # 算子元数据
├── program_package/
│   ├── process.py                    # 算子主实现（必填）
│   ├── dependency/requirements.txt   # 平台预置之外的依赖
│   └── install.sh.example            # 自定义安装步骤模板
├── obs_input/  obs_output/           # 本地 mock 输入/输出
├── .env.example                      # --obs 模式凭据模板
├── AGENTS.md  .aishipbox.toml  .gitignore
└── .venv/                            # Python 3.10（已装好平台预置的 pandas/numpy/pyarrow）
```

### 3.2 实现算子

编辑 `program_package/process.py`，按第 2.2 / 2.3 节的契约实现 `Process`（及可选的 Pre/PostProcess）。先 `cat manifest.yml` 确认当前是模式一还是模式二。

### 3.3 op run —— 本地运行与 mock

```bash
cd my_op
# 把测试数据放进 obs_input/
aishipbox op run                  # mock 模式（默认）
```

mock 模式把平台依赖在本地等价模拟：

- **`moxing.file`**：`obs://input/` → `obs_input/`，`obs://output/` → `obs_output/`；**其他 bucket 名会立即报错**（只在这两条路径上保证等价）。覆盖 18 个 API（list_directory / copy / copy_parallel / read / write / append / glob / walk / stat / exists / is_directory / make_dirs / mk_dir / remove / rename / get_size / scan_dir / File）。
- **`ma_utils.FileLogger.get_logger()`**：返回配置好格式的本地 logger。
- 模式一下，各文件返回的 DataFrame 会汇总写到 `obs_output/result.jsonl`（仅本地约定）。

**真实 OBS：**

```bash
cp .env.example .env              # 填 OBS_AK/SK/ENDPOINT/INPUT_PATH/OUTPUT_PATH
aishipbox op run --obs
```

### 3.4 op debug —— 断点调试

```bash
aishipbox op debug                # 生成 .vscode/launch.json（"Attach to Op Service"）
aishipbox op run --debug          # 启动后等 VS Code 在 5678 端口附加
```

在 VS Code 选 "Attach to Op Service" 即可命中 `process.py` 断点。

### 3.5 op download —— 添加依赖

只有平台**没有**的包才需要打进算子包。`op download` 自动处理跨平台 wheel：

```bash
aishipbox op download requests
```

它按 `manifest.yml > runtime > cpu-arch` 选目标平台（`ARM`→`manylinux2014_aarch64`，`X86`→`manylinux2014_x86_64`），下载 **Linux + Python 3.10** 的 wheel 到 `dependency/`（`--no-deps`，不拉传递依赖），并把 `<package>==<version>` 写入 `requirements.txt`。

- 与开发机平台无关（macOS/Windows 上也能下到正确的 Linux wheel）。
- 平台预置包会被拒绝下载（pandas/numpy/pyarrow，大小写不敏感）。
- 可重复执行（幂等），多架构会各下一份并校验版本一致。
- 无法从 PyPI 获取的依赖：手动放 `.whl` 进 `dependency/`，复杂步骤写进 `install.sh`（参考 `install.sh.example`）。

### 3.6 op pack —— 打包

```bash
aishipbox op pack                 # → program_package/<id>.tar
aishipbox op pack --force         # 覆盖已存在的 tar
aishipbox op pack -o out.tar      # 指定输出路径
```

打包前校验 `manifest.yml`（不合规直接报错列出全部问题）和 `process.py`（须含 `Process` 类）。产物是未压缩 `.tar`，按第 2.5 节规范嵌套于 `<id>/` 下；`obs_input/`、`obs_output/`、`AGENTS.md`、`.aishipbox.toml` 及 `*.tar`/`*.example` 不会被打进包。

**改动 `manifest.yml` 或依赖后必须重新 `pack`。**

---

## 4. 用 coding agent 配合 aishipbox 快速构建

aishipbox 专为 coding agent（Claude Code 等）协作设计：命令非交互友好（`--yes` 永不卡住），每个项目自带 `AGENTS.md` 作为 agent 的项目内操作手册（含完整 manifest 字段规范与约束）。

### 4.1 分工：人起项目，agent 实现

推荐流程是**人先用 `op new` 起好项目骨架**（确定算子身份：id/类别/模态/模式），**再让 agent 接手**填 manifest 细节、实现 process.py、本地验证、打包。

```bash
# 人：起项目（选好模式与骨架）
aishipbox op new img_dedup --yes \
  --category 数据去重 --modal IMAGE --auto-data-loading=false --skeleton transform
cd img_dedup
# 在这个目录里启动你的 coding agent（它会读到项目内 AGENTS.md）
```

然后 agent 的典型步骤：

1. **读 `AGENTS.md`** —— 拿到 manifest 完整字段规范、两种模式契约、moxing/ma_utils 用法、约束。
2. **编辑 `manifest.yml`** —— 补 description/arguments/resources 等细节（直接改文件，比堆一长串 flag 可靠）。
3. **实现 `program_package/process.py`** —— 按当前模式写 Process 逻辑。
4. **加依赖**（按需）：`aishipbox op download <pkg>`。
5. **本地验证**：把样例放进 `obs_input/`，跑 `aishipbox op run`，看 `obs_output/`。
6. **打包**：`aishipbox op pack`。

### 4.2 示例 prompt → agent 动作

把项目起好、在项目目录里启动 agent 后，可以这样让它干活：

**示例 A —— 实现一个图片去重算子（模式二）：**

> 「读 AGENTS.md。这是个 IMAGE 模态、数据去重、auto-data-loading=false 的算子。请在 process.py 里实现：从 args.obs_input_path 读取所有图片，按内容 hash 去重，把保留的图片写到 args.obs_output_path。需要的依赖用 `aishipbox op download` 装。然后跑 `aishipbox op run` 验证，最后 `aishipbox op pack`。」

agent 会依次：读 AGENTS.md → 写 `Process.__call__`（用 `mox.file.list_directory` / `copy`）→ `aishipbox op download imagehash` → `aishipbox op run` → 看 `obs_output/` → `aishipbox op pack`。

**示例 B —— 在已有项目上加业务参数：**

> 「给这个算子加一个 FLOAT 参数 threshold（默认 0.9，范围 0~1），在 manifest.yml 的 arguments 里声明，并在 process.py 里用 args.threshold。改完重新 pack。」

agent 会：按 AGENTS.md 的 arguments 规范改 `manifest.yml` → 在 `process.py` 用 `self.args.threshold` → `aishipbox op pack`（pack 会顺带校验 manifest）。

### 4.3 给 agent 的要点

- **始终带 `--yes`** 跑 `op new`（agent 环境无 TTY，否则报错）。
- **manifest 细节直接编辑文件**，不必都用 flag。
- **`AGENTS.md` 是权威参考**，字段枚举/约束以它为准。
- **每改 manifest 或依赖就 `op pack`**，pack 自带校验，是最省事的「lint」。
- 本地 mock 只认 `obs://input/` 和 `obs://output/`，其他 OBS 路径需 `--obs` 模式。

---

## 端到端示例

```bash
# 1. 人：起项目（模式二 + transform 骨架）
aishipbox op new img_copy --yes \
  --category 数据转换 --modal IMAGE --auto-data-loading=false --skeleton transform
cd img_copy

# 2. agent / 人：按需微调 manifest.yml（字段规范见 AGENTS.md）

# 3. 放测试数据
cp ~/some_images/*.jpg obs_input/

# 4. 实现 program_package/process.py 的 transform()

# 5. 加平台没有的依赖（按需）
aishipbox op download pillow

# 6. 本地跑，看 obs_output/
aishipbox op run

# 7. 打包上传
aishipbox op pack                 # → program_package/img_copy.tar
```

---

## 常见问题

- **向导卡住 / agent 无响应**：非交互环境忘了 `--yes`。补上即可（字段可省略走默认）。
- **`op run` 报缺少 pandas**：模式一需要 pandas，`op new` 已装平台预置版本进 `.venv/`。若 `.venv` 损坏，重跑 `op new`（换名或先删项目），或手动 `uv venv --python 3.10 .venv` 后装回预置包。预置包不能用 `op download`（会被拒绝）。
- **`其他 bucket 名报错`**：mock 只支持 `obs://input/` 和 `obs://output/`，其余路径用 `--obs` 连真实 OBS。
- **平台装包失败**：检查是否把预置包写进了 `requirements.txt`，或 wheel 架构/Python 版本不匹配（用 `op download` 而非手动下载可避免）。

## 参考

- 平台手册：https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html
- 算子配置文件规范：https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0044.html
- MoXing API：https://support.huaweicloud.com/usermanual-standard-modelarts/modelarts_11_0001.html
- 项目内 `AGENTS.md`：完整 manifest 字段规范 + 给 agent 的操作约束
