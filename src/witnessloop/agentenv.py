"""交互层侧的取值策略：run id 与模板目录。

Claude Code 既没有稳定的「当前 run id」注入点，插件也没有固定的安装位置，
所以适配器与工具必须按**同一套规则**取值。这里把规则写成**可执行的规范**而不是
只散落在模板散文里——规范能写错，代码+测试不能。

规则：

* **run id**：角色专用环境变量 → ``WITNESSLOOP_RUN_ID``（当前 run）→ **确定性兜底**。
  兜底形态是 ``<stage>-<role>-<anchor>``，``anchor`` = change id + head sha 的
  **≥12 位**短摘要——**同输入 → 同 id**。**role 编进 id**，所以兜底路径下
  `reviewer_run_id` 与 `author_run_id` **结构性不同**。

  幂等的**完整**键是 ``(change, stage, role, revision, base ref 的解析目标)``——
  只固定 run id 不够：base 漂移照样改 ``base_sha`` / ``diff_hash``。
  所以「逐字节可复现」只在**固定 base 与 revision 时**成立。

  ⚠️ 兜底的代价：这个 id 是**「审阅目标的指纹」**，只代表「哪个 change 的哪个
  revision 的哪个角色」，**不代表真实 run 身份**——「reviewer ≠ author」在兜底路径下
  结构性恒真，因此它只挡「**显式**把同一个值喂给两个角色」（如只设共享的
  ``WITNESSLOOP_RUN_ID``），**不**等于「挡忘了另开 run」。与既有的
  「防漂移、不防伪造」是同一条边界——要真实身份就得设 ``WITNESSLOOP_RUN_ID``。
* **模板目录**：``WITNESSLOOP_TEMPLATES_DIR`` 优先，未设回落仓库的 ``templates/``。
"""

from __future__ import annotations

import os
from pathlib import Path

#: 当前 run 的 id。**一个 run 一个值**——所以审阅者与作者各自的环境里应当不同。
RUN_ID_ENV = "WITNESSLOOP_RUN_ID"

#: 覆盖模板目录。`plugin/` 被单独拷走、脱离本仓时靠它把模板位置指回去。
TEMPLATES_DIR_ENV = "WITNESSLOOP_TEMPLATES_DIR"

#: 未覆盖时的模板目录 = 本仓根的 `templates/`（适配器默认也用 `${CLAUDE_PLUGIN_ROOT}/../templates`）。
DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"

#: 兜底 id 里保留的 head sha 摘要位数（Q1：≥12——太短会丧失 revision 区分力）。
ANCHOR_DIGEST_LEN = 12


def role_env_name(role: str) -> str:
    """角色专用的 run id 变量名（同一进程里要同时指定两个角色时用）。"""
    return f"WITNESSLOOP_{role.upper()}_RUN_ID"


def default_run_anchor(change_id: str, head_sha: str) -> str:
    """确定性兜底的锚：``<change-id>-<head sha 的 ≥12 位短摘要>``。

    稳定的输入 → 稳定的锚 → 稳定的 id。摘要取 ≥12 位（Q1）：太短会丧失 revision
    区分力，让两个不同 revision 撞到同一个兜底 id。
    """
    return f"{change_id}-{head_sha[:ANCHOR_DIGEST_LEN]}"


def generate_run_id(stage: str, role: str, anchor: str) -> str:
    """``<stage>-<role>-<anchor>``——**确定性**。

    ``role`` 编进 id 是关键：兜底路径下两个角色**必然不同**，不会自撞。
    """
    return f"{stage}-{role}-{anchor}"


def resolve_run_id(stage: str, role: str, *, anchor: str, env=None) -> str:
    """环境优先、确定性兜底。

    注意：只设共享的 ``WITNESSLOOP_RUN_ID`` 时，两个角色会拿到**同一个**值——
    那是刻意的（它就是「当前 run 的 id」），门禁会拒掉。想让两个角色不同，
    就给它们各自的环境，或用角色专用变量 + 兜底。
    """
    env = os.environ if env is None else env
    for name in (role_env_name(role), RUN_ID_ENV):
        value = (env.get(name) or "").strip()
        if value:
            return value
    return generate_run_id(stage, role, anchor)


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
