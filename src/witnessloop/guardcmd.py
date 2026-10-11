"""``witnessloop guard``：写代码前缺 grill 证据就拦（change grill-evidence-gate / #7 ②）。

hook 属**交互层**（host 特定，见 `plugin/hooks/`），但本动词本身 **host 中立**——
任何宿主都能调：给一组**写目标路径**，命中 `policy.require_change_for` 且当前 change
的 grill 证据不完备 ⇒ exit 2（拦）。

**诚实边界**：本动词是「**防遗忘**」，**不是防对抗**——agent 可以改用 Bash 写文件
（`Write|Edit` matcher 不覆盖它）、也可以不装插件。真正的锚仍是 CI required check。

判定与 `check` **共用同一个** `evidence.grill_evidence_findings`（分两份实现必然漂移）。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from witnessloop import constants as C
from witnessloop import contract, gitutil
from witnessloop import evidence as evidence_mod
from witnessloop import paths as pathutil
from witnessloop import policy as policy_mod

#: 逃生口：设了就放行（给人用；覆盖不了 CI 那层的同判据）。
SKIP_ENV = "WITNESSLOOP_SKIP_GUARD"
#: 显式指定当前 change（优先级高于分支名推断）。
CHANGE_ENV = "WITNESSLOOP_CHANGE"


def _allow(message: str) -> int:
    print(f"guard：放行——{message}", file=sys.stderr)
    return C.EXIT_PASS


def resolve_change_id(
    root: Path, pol: policy_mod.Policy, explicit: str | None
) -> str | None:
    """当前 change id：显式 → `WITNESSLOOP_CHANGE` → 分支名首段。

    **推得的 id 必须命中一个现存的 active change 目录**，否则视为「推不出」。
    这条不是可有可无：`fix/login`、`dependabot/npm_and_yarn/x` 这类分支的首段会被
    当成 change id，而目录不存在 ⇒ 误拦（本地 fail-closed 的真实误伤）。
    （与 asterwynd `_current_change_id()` 同款：`if (CHANGES_DIR / head).is_dir()`。）
    """
    branch = gitutil.current_branch(root) or ""
    candidates = [explicit, os.environ.get(CHANGE_ENV), branch.split("/", 1)[0] if branch else None]
    for candidate in candidates:
        if not candidate:
            continue
        candidate = candidate.strip()
        if not candidate or "/" in candidate or "\\" in candidate:
            continue
        if candidate == C.ARCHIVE_DIR_NAME:
            continue
        if (root / pol.changes_root / candidate).is_dir():
            return candidate
    return None


def _code_paths(pol: policy_mod.Policy, paths: list[str]) -> list[str]:
    """命中所写目标里落 `require_change_for` 的那些（其余是文档/测试 → 豁免）。"""
    return sorted(
        {
            pathutil.normalize(path)
            for path in paths
            if path and pathutil.matches_any(pathutil.normalize(path), pol.require_change_for)
        }
    )


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()

    if os.environ.get(SKIP_ENV):
        return _allow(f"已跳过（{SKIP_ENV} 已设——本地守卫的逃生口；CI 那层不受影响）")

    try:
        pol = policy_mod.load_policy(root)
    except policy_mod.PolicyError as exc:
        print(f"guard：policy 非法（{exc}）——不拦。", file=sys.stderr)
        return C.EXIT_PASS
    if pol is None:
        print(
            f"guard：未接入 witnessloop（没有 {C.POLICY_PATH}）——不拦；"
            "本地守卫对未接入的仓无意见。",
            file=sys.stderr,
        )
        return C.EXIT_NOT_ONBOARDED

    paths = [p for p in (getattr(args, "path", None) or []) if p]
    if not paths:
        return _allow("没有给出写目标路径（--path）")

    if not _code_paths(pol, paths):
        return _allow("写目标不命中 require_change_for（文档/测试，豁免——否则会锁死证据产出）")

    change_id = resolve_change_id(root, pol, getattr(args, "change", None))
    if change_id is None:
        return _allow("推不出当前 change（分支名不是 <change-id>/…、或不命中现存 change 目录）")

    findings = evidence_mod.grill_evidence_findings_in_change(
        contract.change_dir(root, pol, change_id),
        grill_stage=pol.grill_stage,
        manifest_glob=pol.review_manifest_glob,
        label=change_id,
    )
    if not findings:
        return C.EXIT_PASS

    print(
        f"guard：拦住 ✗ —— change {change_id} 的 grill 证据不完备，"
        f"不允许写这些代码路径：{', '.join(_code_paths(pol, paths)[:5])}",
        file=sys.stderr,
    )
    for finding in findings[:5]:
        print(f"  - {finding.message}", file=sys.stderr)
    print(
        "  先跑 /grill（或补齐 reviews/grill-review.md + 它的 manifest）；"
        f"确有需要，设 {SKIP_ENV}=1 跳过。",
        file=sys.stderr,
    )
    return C.EXIT_BLOCKED
