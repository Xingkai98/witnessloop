"""``witnessloop check``：CI 入口，**fail-closed**。

校验三件事（design §5.1）：
1. change 目录契约（D2）
2. review manifest 存在且 hash 绑定、reviewer ≠ author（D3/D4）
3. 受保护路径的写入有结构化解释事件（D5）

外加不变集（D6）：policy / manifest 恒受保护，repo policy 移除不掉。
任何一步出错都非零退出——**未接入时也绝不静默通过**（D1）。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from witnessloop import constants as C
from witnessloop import contract, gitutil
from witnessloop import events as events_mod
from witnessloop import paths as pathutil
from witnessloop import policy as policy_mod


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()

    # D1：无 policy → 报「未接入」并非零退出。门禁 fail-closed，不静默通过。
    try:
        pol = policy_mod.load_policy(root)
    except policy_mod.PolicyError as exc:
        print(f"check：未通过 ✗ —— policy 非法：{exc}", file=sys.stderr)
        return C.EXIT_FAIL
    if pol is None:
        print(
            "check：未接入 witnessloop ✗\n"
            f"  没有找到 {C.POLICY_PATH}。门禁 fail-closed：未接入 = 不放行。\n"
            "  请先在目标仓运行 `witnessloop init` 并提交其产物。",
            file=sys.stderr,
        )
        return C.EXIT_NOT_ONBOARDED

    base = _resolve_base(root, args.base)
    head = args.head or os.environ.get("WITNESSLOOP_HEAD_REF") or "HEAD"

    if gitutil.rev_parse(root, base) is None:
        print(f"check：未通过 ✗ —— 无法解析 base ref：{base}", file=sys.stderr)
        return C.EXIT_FAIL
    try:
        changes = gitutil.changed_files(root, base, head)
    except gitutil.GitError as exc:
        print(f"check：未通过 ✗ —— {exc}", file=sys.stderr)
        return C.EXIT_FAIL

    # 被检 revision 的 sha：D3 用它核对 manifest 的 head_sha 是不是审对了 revision。
    # pr_paths 是本次 PR 自身的变更集——被检 head 可能是 merge commit，判定 stale
    # 时必须把 base 侧顺带进来的改动排除掉。
    scope = contract.SpanScope(
        checked_head=gitutil.rev_parse(root, head) or head,
        pr_paths=frozenset(
            pathutil.normalize(path)
            for change in changes
            for path in (change.path, change.old_path)
            if path
        ),
        evidence_patterns=pol.evidence_path_patterns,
    )

    change_ids = contract.changed_change_ids(changes, pol.changes_root)
    findings: list[contract.Finding] = []
    for change_id in change_ids:
        findings += contract.validate_change_dir(root, pol, change_id)
        findings += contract.validate_review_manifests(
            root, pol, change_id, scope=scope
        )
    findings += _require_change(pol, changes, change_ids)
    findings += _protected_writes(root, pol, changes)

    _report(base, head, changes, change_ids, findings)
    return C.EXIT_FAIL if findings else C.EXIT_PASS


def _resolve_base(root: Path, explicit: str | None) -> str:
    """base ref 解析：显式参数 → WITNESSLOOP_BASE_REF → GITHUB_BASE_REF → 主干。"""
    if explicit:
        return explicit
    env = os.environ.get("WITNESSLOOP_BASE_REF")
    if env:
        return env
    gh_base = os.environ.get("GITHUB_BASE_REF")
    if gh_base:
        return f"origin/{gh_base}"
    for candidate in ("origin/main", "main", "origin/master", "master"):
        if gitutil.rev_parse(root, candidate):
            return candidate
    return "main"


def _require_change(pol: policy_mod.Policy, changes, change_ids) -> list[contract.Finding]:
    """改了代码就必须挂一个 change 目录。

    没有这条时，`check` 只保证「**如果你**动了 change 目录/受保护路径，它要齐备」，
    于是最省事的绕过方式是什么都不建——只改 `src/` 的 PR 直接放行。
    """
    if change_ids or not pol.require_change_for:
        return []

    hits = sorted(
        {
            pathutil.normalize(path)
            for change in changes
            for path in (change.path, change.old_path)
            if path and pathutil.matches_any(pathutil.normalize(path), pol.require_change_for)
        }
    )
    if not hits:
        return []

    shown = ", ".join(hits[:5]) + ("…" if len(hits) > 5 else "")
    return [
        contract.Finding(
            hits[0],
            f"{shown} 属于必须挂 change 的路径（policy.require_change_for），"
            f"但本次 diff 里没有任何 change 目录（{pol.changes_root}/<id>/）。"
            "补一个 change 目录，或把该路径从 policy.require_change_for 里移除。",
        )
    ]


def _protected_writes(root: Path, pol: policy_mod.Policy, changes) -> list[contract.Finding]:
    """D5 + D6：受保护路径的写入必须有结构化解释事件。

    两类受保护路径，规则差一条：

    * **repo policy 声明**（如 ``openspec/specs/**``）——新增 / 修改 / 删除都要事件。
      这才是「写受保护 artifact 得给理由」的本义。
    * **不变集**（policy / init 台账 / 事件文件 / review manifest，D6）——**新增**
      不需要事件（创建证据本体/门禁自身配置就是正常工作流），**修改或删除**才要。
      否则每个正常 PR 都得为「新增自己那份 manifest」写一条解释事件（自相矛盾），
      接入 PR 也会被自己的门禁拦下（鸡生蛋）。

    **改名**按「对旧路径的删除」处理：``git mv`` 一个受保护文件等于把它从保护区
    删掉再在别处新建。若只看新路径，把 ``openspec/specs/x.md`` 改名到 ``src/x.md``
    就能无解释地让受保护 artifact 消失。因此 old_path 必须一并检查。
    """
    invariant = policy_mod.INVARIANT_PROTECTED_PATHS
    try:
        known = events_mod.load_all(root, pol)
    except events_mod.EventError as exc:
        return [contract.Finding(".", f"事件文件无法解析：{exc}")]

    findings: list[contract.Finding] = []
    for change in changes:
        # 每个变更文件贡献 1~2 个「待解释的路径」：新路径（写入），
        # 以及改名时的旧路径（等同于删除）。
        targets = [(change.path, change.status)]
        if change.old_path:
            targets.append((change.old_path, "D"))

        for raw_path, status in targets:
            path = pathutil.normalize(raw_path)
            by_policy = pathutil.matches_any(path, pol.protected_paths)
            by_invariant = pathutil.matches_any(path, invariant)
            if not (by_policy or by_invariant):
                continue
            if by_invariant and status == "A":
                continue  # 新增证据本体 / 门禁自身配置：不需要解释
            if any(
                events_mod.covers(event, path, pol.protected_write_event_types)
                for event in known
            ):
                continue
            findings.append(
                contract.Finding(
                    path,
                    "受保护路径被写入，但没有结构化解释事件"
                    f"（需 {pol.events_file} 里有 event_type="
                    f"{'/'.join(pol.protected_write_event_types)}、"
                    "artifact_path 指向该文件、reason/approved_by 非空的事件）",
                )
            )
    return findings


def _report(base, head, changes, change_ids, findings) -> None:
    # flush：不 flush 的话 stdout 缓冲会让摘要排在 stderr 的失败明细后面。
    print(
        f"check：基线 {base}...{head}，{len(changes)} 个变更文件，"
        f"{len(change_ids)} 个 change 目录",
        flush=True,
    )
    if change_ids:
        print(f"  change：{', '.join(change_ids)}", flush=True)
    if not findings:
        print("check：通过 ✓")
        return
    print(f"check：未通过 ✗（{len(findings)} 项）", file=sys.stderr)
    for index, finding in enumerate(findings, 1):
        print(f"  {index}. {finding.path}：{finding.message}", file=sys.stderr)
