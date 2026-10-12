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

# 承载「实现后独立审阅」的阶段名（policy.evidence.building_stage 可覆写）。
# `check` 在**本次 diff 触及 require_change_for**（= 落了实现）时要求它的 manifest 存在
# （change building-review-gate / issue #13）。它只要求**证据存在**——不解析报告里的 verdict 文本。
DEFAULT_BUILDING_STAGE = "building"

# 承载 grill 决策记录的审阅阶段名（policy.evidence.grill_stage 可覆写）。
# `check` 校验「该 stage 的 manifest 所绑定报告」的正文完备性（见 evidence.py）。
DEFAULT_GRILL_STAGE = "grill"

# 承载「设计阶段对抗验证轮」（grill 后、停轮之前的证伪环节）的阶段名
# （policy.evidence.grill_adversarial_stage 可覆写）。
# 触发面与 building **共用同一条**（本次 diff 触及 require_change_for = 落了实现）——
# change grill-adversarial-gate / issue #16。判据同 building：只要求**证据存在**，
# 不解析 verdict 文本、不校验报告正文（空文件亦合格）。
DEFAULT_GRILL_ADVERSARIAL_STAGE = "grill-adversarial"

# 数据契约 schema 标签（写入各 json 的 `schema` 字段，便于人工识别）。
SCHEMA_POLICY = "witnessloop/policy@v1"
SCHEMA_INIT_MANIFEST = "witnessloop/init-manifest@v1"
SCHEMA_REVIEW_MANIFEST = "witnessloop/review-manifest@v1"
SCHEMA_EVENT = "witnessloop/event@v1"

# review manifest 里「内容哈希」字段 → 它绑定的 artifact（相对 change 目录）。
# `check` 校验与 `manifest build` 产出**共用这一张表 + 同一个 sha256_tree**，
# 杜绝两边漂移（manifest 的 report_hash 因为路径是动态的，单独处理）。
HASHED_ARTIFACTS = (
    ("tasks_hash", "tasks.md"),
    ("spec_hash", "specs"),
)

# review manifest 必填字段（design §5.3）。`diff_hash` 是 informational，不在此列。
# `stage` 纳入必填（change grill-evidence-gate D2b）：它此前「写而不校」，而 `check`
# 靠它定位 grill 报告——不校验则 stage 拼错会静默失效。
REVIEW_MANIFEST_REQUIRED_FIELDS = (
    "stage",
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
# `guard` 的**内部错误**（未预期异常）：fail-open，**绝不等于 1**（1 是「拦」）。
# 由进程入口 `entry.py` 捕获未预期异常时返回；**仅 `guard`** 用它——其余动词崩溃退 1（失败 / fail-closed）。
# `entry.py` 不可 import 本模块（要能在 witnessloop 自己导入不起来时兜底）⇒ 那里用字面量，
# 由 `tests/test_entry.py` 钉两处同值（漂移会让入口兜底与 CLI 语义分叉）。
EXIT_INTERNAL = 4

# 注意（回归审阅 Issue 3 修复）：`guard` 的「拦住」用 EXIT_FAIL(1)，**不是** 2。
# 早先用 2（= EXIT_USAGE）同值 ⇒ 任何 argparse 用法错误都被 CC 当成 block——
# 尤其**旧版 CLI 不认识 `guard` 子命令**时 argparse 退 2 ⇒ 每个 Write/Edit 全被拦
# （fail-open 反转成 fail-closed）。改由 `plugin/hooks/guard.sh` 把 1 映射成 CC 的 exit 2。
# ⇒ `guard` 的退出码形状与 `check` 一致：0 通过 / 1 未通过(拦) / 2 用法 / 3 未接入。
