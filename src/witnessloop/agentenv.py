"""交互层侧的取值策略：run id。

Claude Code 没有稳定的「当前 run id」注入点，所以适配器与工具必须按**同一套规则**
取值。这里把规则写成**可执行的规范**而不是只散落在模板散文里——规范能写错，
代码+测试不能。

规则：角色专用环境变量 → ``WITNESSLOOP_RUN_ID``（当前 run）→ 生成。
生成的形态是 ``<stage>-<role>-<UTC 时间戳>-<短随机>``，**role 编进 id**，
所以生成路径下 `reviewer_run_id` 与 `author_run_id` 必然不同——
门禁会对两者相等直接拒（那是「忘了另开 run」的症状）。
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

#: 当前 run 的 id。**一个 run 一个值**——所以审阅者与作者各自的环境里应当不同。
RUN_ID_ENV = "WITNESSLOOP_RUN_ID"


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
