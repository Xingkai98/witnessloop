"""交互层侧的取值策略：run id 与模板目录。

Claude Code 既没有稳定的「当前 run id」注入点，插件也没有固定的安装位置，
所以适配器与工具必须按**同一套规则**取值。这里把规则写成**可执行的规范**而不是
只散落在模板散文里——规范能写错，代码+测试不能。

规则：

* **run id**：角色专用环境变量 → ``WITNESSLOOP_RUN_ID``（当前 run）→ 生成。
  生成的形态是 ``<stage>-<role>-<UTC 时间戳>-<短随机>``，**role 编进 id**，
  所以生成路径下 `reviewer_run_id` 与 `author_run_id` 必然不同——
  门禁会对两者相等直接拒（那是「忘了另开 run」的症状）。
* **模板目录**：``WITNESSLOOP_TEMPLATES_DIR`` 优先，未设回落仓库的 ``templates/``。
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

#: 当前 run 的 id。**一个 run 一个值**——所以审阅者与作者各自的环境里应当不同。
RUN_ID_ENV = "WITNESSLOOP_RUN_ID"

#: 覆盖模板目录。`plugin/` 被单独拷走、脱离本仓时靠它把模板位置指回去。
TEMPLATES_DIR_ENV = "WITNESSLOOP_TEMPLATES_DIR"

#: 未覆盖时的模板目录 = 本仓根的 `templates/`（适配器默认也用 `${CLAUDE_PLUGIN_ROOT}/../templates`）。
DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def role_env_name(role: str) -> str:
    """角色专用的 run id 变量名（同一进程里要同时指定两个角色时用）。"""
    return f"WITNESSLOOP_{role.upper()}_RUN_ID"


def generate_run_id(
    stage: str, role: str, *, now: datetime | None = None, token: str | None = None
) -> str:
    """``<stage>-<role>-<UTC 时间戳>-<短随机>``。

    ``role`` 编进 id 是关键：生成路径下两个角色**必然不同**，不会自撞。
    """
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    suffix = token if token is not None else secrets.token_hex(3)
    return f"{stage}-{role}-{stamp}-{suffix}"


def resolve_run_id(stage: str, role: str, *, env=None) -> str:
    """环境优先、生成兜底。

    注意：只设共享的 ``WITNESSLOOP_RUN_ID`` 时，两个角色会拿到**同一个**值——
    那是刻意的（它就是「当前 run 的 id」），门禁会拒掉。想让两个角色不同，
    就给它们各自的环境，或用角色专用变量 + 生成兜底。
    """
    env = os.environ if env is None else env
    for name in (role_env_name(role), RUN_ID_ENV):
        value = (env.get(name) or "").strip()
        if value:
            return value
    return generate_run_id(stage, role)


def resolve_templates_dir(*, env=None, default: Path | None = None) -> Path:
    """模板目录：``WITNESSLOOP_TEMPLATES_DIR`` 优先，未设回落仓库的 ``templates/``。

    展开 ``~``——这是**人手工设**的变量，不是 git 输出的路径，不像门禁侧那样
    刻意不展开。
    """
    env = os.environ if env is None else env
    override = (env.get(TEMPLATES_DIR_ENV) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (default or DEFAULT_TEMPLATES_DIR).resolve()
