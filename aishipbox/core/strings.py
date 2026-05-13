"""User-facing strings (Chinese). Single source for future i18n."""

UV_NOT_FOUND = "未找到 uv 命令，请先安装 uv：https://github.com/astral-sh/uv"
PROJECT_NOT_FOUND = "当前目录不是 aishipbox 项目（找不到 .aishipbox.toml）。请先运行 `aishipbox <op|algo> new`。"
PROJECT_TYPE_MISMATCH = "项目类型不匹配：检测到 {detected}，但当前命令需要 {expected}。"
TARGET_DIR_EXISTS = "目标目录已存在：{path}"
MISSING_FLAGS_FOR_YES = "使用 --yes 时缺少以下字段：{fields}"
MANIFEST_INVALID = "manifest.yml 校验失败："
OBS_CREDS_MISSING = "缺少 OBS 配置，请在 .env 中设置：{fields}"
PACK_OUTPUT_EXISTS = "输出文件已存在：{path}，使用 --force 覆盖。"
UNEXPECTED_ERROR = "发生未预期错误，设置 AISHIPBOX_DEBUG=1 查看完整堆栈。"
NEXT_STEPS_HEADER = "后续步骤："

# Algo
ALGO_TEMPLATE_BASIC = "basic   - 最简服务骨架"
ALGO_TEMPLATE_PREDICT = "predict - 预测/机器学习（pandas）"
ALGO_TEMPLATE_CV = "cv      - 计算机视觉（OpenCV/Pillow）"
ALGO_SELECT_TEMPLATE = "请选择模板："

# Op wizard
OP_WIZARD_TITLE = "新建自定义算子"
OP_FIELD_ID = "算子 ID"
OP_FIELD_NAME = "算子名称"
OP_FIELD_DESCRIPTION = "算子描述"
OP_FIELD_AUTHOR = "作者"
OP_FIELD_VERSION = "版本（x.y.z）"
OP_FIELD_CATEGORY = "类别（可多选）"
OP_FIELD_MODAL = "数据模态（可多选）"
OP_FIELD_FORMAT = "数据格式（如 JPG, PNG）"
OP_FIELD_LANGUAGE = "语言标签"
OP_FIELD_CPU_ARCH = "CPU 架构"
OP_FIELD_CPU = "CPU 核数"
OP_FIELD_MEMORY = "内存 (MB)"
OP_FIELD_NPU = "NPU 数量"
OP_FIELD_AUTO_DATA_LOADING = "是否自动加载数据"
OP_FIELD_SKELETON = "代码骨架"
OP_SKELETON_BLANK = "blank      - 空白骨架"
OP_SKELETON_TRANSFORM = "transform  - 含 moxing 数据转换示例"

OP_CATEGORIES = ["数据提取", "数据抽样", "数据转换", "数据过滤", "数据去重", "数据打标", "其他"]
OP_MODALS = ["TEXT", "IMAGE", "VIDEO", "AUDIO", "OTHER"]
OP_CPU_ARCHES = ["ARM"]
OP_XPU_DEVICES = ["SNT9B"]
