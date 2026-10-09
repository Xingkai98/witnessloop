"""跨模块共享的常量与契约字面量。

v1 硬编码 OpenSpec 形状的 change 契约（见 design §4「spec 依赖」轴）——
这里没有 spec 适配器抽象层，只有常量。
"""

# witnessloop 自身的仓库 slug（init 写的 caller workflow 用它钉版本）。
REPO_SLUG = "Xingkai98/witnessloop"

# caller workflow 引用的 reusable workflow，tag 钉版本（design §5.1）。
DEFAULT_GATE_REF = f"{REPO_SLUG}/.github/workflows/gate.yml@v1"

# init 创建的文件（相对目标仓根）。
POLICY_PATH = ".witnessloop/policy.json"
INIT_MANIFEST_PATH = ".witnessloop/init-manifest.json"
GATE_WORKFLOW_PATH = ".github/workflows/witnessloop.yml"

# change 目录默认根（policy 可覆写）。
DEFAULT_CHANGES_ROOT = "openspec/changes"

# 归档目录名：`<changes_root>/archive/**` 放下线后的 change。
ARCHIVE_DIR_NAME = "archive"

# `require_change_for` 的默认值：命中这些路径的改动**必须**挂一个 change 目录。
# 否则「什么都不建」就是最省事的绕过方式——只改 `src/` 的 PR 会直接放行。
# 刻意**不含** `docs/**` / `tests/**` 这类目录：纯文档/纯测试改动不该被拦。
DEFAULT_REQUIRE_CHANGE_FOR = (
    "src/**",
    "lib/**",
    "app/**",
    "apps/**",
    "packages/**",
    "server/**",
    "cmd/**",
    "internal/**",
)

# OpenSpec 形状的 change 目录必需件（policy.required_artifacts 可覆写）。
DEFAULT_REQUIRED_ARTIFACTS = ("proposal.md", "design.md", "tasks.md", "specs", "reviews")

# policy.evidence 默认值。
DEFAULT_REVIEW_MANIFEST_GLOB = "reviews/*.manifest.json"
DEFAULT_EVENTS_FILE = "workflow-events.jsonl"
DEFAULT_PROTECTED_EVENT_TYPES = ("protected_path_write",)

# 数据契约 schema 标签（写入各 json 的 `schema` 字段，便于人工识别）。
SCHEMA_POLICY = "witnessloop/policy@v1"
SCHEMA_INIT_MANIFEST = "witnessloop/init-manifest@v1"
SCHEMA_REVIEW_MANIFEST = "witnessloop/review-manifest@v1"
SCHEMA_EVENT = "witnessloop/event@v1"

# review manifest 必填字段（design §5.3）。`diff_hash` 是 informational，不在此列。
REVIEW_MANIFEST_REQUIRED_FIELDS = (
    "reviewer_run_id",
    "author_run_id",
    "base_sha",
    "head_sha",
    "tasks_hash",
    "spec_hash",
    "report_hash",
    "report_path",
)

# 退出码。
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_NOT_ONBOARDED = 3
