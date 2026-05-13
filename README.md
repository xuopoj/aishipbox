# aishipbox

JAC PanguLM 算法服务（algo）与自定义算子（op）开发 CLI。

## 安装

```bash
uv tool install aishipbox
```

## 快速开始

### 算法服务（algo）

```bash
aishipbox algo new my_algo -t basic
cd my_algo
aishipbox algo run
aishipbox algo pack
```

### 自定义算子（op）

```bash
aishipbox op new my_op           # 启动交互向导
cd my_op
# 把测试数据放入 obs_input/
aishipbox op run                  # 默认 mock 模式
aishipbox op run --obs            # 真实 OBS（读取 .env）
aishipbox op pack
```

非交互模式（用于脚本）：

```bash
aishipbox op new my_op --yes \
  --id my_op --op-name 示例 --version 0.0.1 \
  --category 数据转换 --modal IMAGE \
  --cpu-arch arm --cpu 1 --memory 2048 --npu 0 \
  --auto-data-loading=false --skeleton transform
```

## 项目结构

每个项目都生成 `.aishipbox.toml`（标记项目类型与运行时）和 `AGENTS.md`（供 AI agent 参考的项目说明）。每个项目使用独立的 `.venv/`，分别绑定到托管运行时所需的 Python 版本（algo 当前为 3.9，op 当前为 3.10）。

## 文档

- 设计：`docs/superpowers/specs/2026-05-11-aishipbox-design.md`
- 实施计划：`docs/superpowers/plans/2026-05-11-aishipbox.md`
- 算子手册：https://support.huaweicloud.com/usermanual-pangulm/pangulm_04_0043.html

## 开发

```bash
uv sync
uv run pytest                                  # 单元测试
uv run pytest -m integration                   # 端到端（需要 uv 能取得 Python 3.9/3.10）
```
