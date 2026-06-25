# 安装 uv

aishipbox 把 **uv** 作为硬性运行时依赖（不是可选项）：建虚拟环境、装依赖、装工具本身、跑测试全都通过 uv。所以用 aishipbox 之前必须先装好 uv。

> uv 是 Astral 出的 Python 包与项目管理器（Rust 写的，单二进制，免预装 Python），同时充当 pip / venv / pipx / pyenv 的快速替代。

---

## 1. 推荐：官方独立安装脚本

无需预装 Python，一条命令搞定，支持 `uv self update` 自更新。

**macOS / Linux：**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

若没有 `curl`，用 `wget`：

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

**Windows（PowerShell）：**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装脚本会把 `uv` / `uvx` 放到 `~/.local/bin`（Windows 为 `%USERPROFILE%\.local\bin`）。**装完需要新开一个终端**（或重新加载 shell 配置）让 PATH 生效。

---

## 2. 用包管理器安装

按你已有的工具链任选其一：

| 平台 / 工具 | 命令 |
|---|---|
| Homebrew (macOS/Linux) | `brew install uv` |
| MacPorts | `sudo port install uv` |
| WinGet (Windows) | `winget install --id=astral-sh.uv -e` |
| Scoop (Windows) | `scoop install main/uv` |
| pipx（需已装 Python） | `pipx install uv` |
| pip（需已装 Python） | `pip install uv` |
| Cargo（需 Rust 工具链） | `cargo install --locked uv` |

> 用包管理器装的，不要用 `uv self update`（会冲突）；改用对应包管理器升级，如 `brew upgrade uv` / `pip install --upgrade uv`。

---

## 3. 验证安装

```bash
uv --version
```

能打印版本号即成功。若提示 `command not found`：

- **新开一个终端**（PATH 在装完当下不会自动生效）。
- 确认 `~/.local/bin` 在 `PATH` 里：`echo $PATH | tr ':' '\n' | grep local/bin`。
- 手动加入（bash/zsh）：把 `export PATH="$HOME/.local/bin:$PATH"` 写进 `~/.bashrc` / `~/.zshrc` 后 `source` 它。

---

## 4. 装好 uv 之后：安装 aishipbox

```bash
uv tool install aishipbox            # 从 PyPI
# 或从当前源码（开发）
uv tool install --reinstall .
aishipbox op --help                  # 确认可用
```

---

## 5. 升级 / 卸载 uv

**升级（独立脚本安装的）：**

```bash
uv self update
```

**指定版本安装**（脚本方式，URL 里带版本号）：

```bash
curl -LsSf https://astral.sh/uv/0.11.24/install.sh | sh
```

**卸载：**

```bash
uv cache clean                       # 清缓存
rm -r "$(uv python dir)"             # 删 uv 管理的 Python
rm -r "$(uv tool dir)"               # 删 uv 装的工具
rm ~/.local/bin/uv ~/.local/bin/uvx  # 删二进制（macOS/Linux）
```

Windows 删二进制：

```powershell
rm $HOME\.local\bin\uv.exe
rm $HOME\.local\bin\uvx.exe
rm $HOME\.local\bin\uvw.exe
```

---

## 参考

- uv 官方安装文档：https://docs.astral.sh/uv/getting-started/installation/
- uv 文档主页：https://docs.astral.sh/uv/
