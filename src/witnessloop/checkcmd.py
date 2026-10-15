"""``witnessloop check``：CI 入口，**fail-closed**。

校验四件事（design §5.1）：
1. change 目录契约（D2）
2. review manifest 存在且 hash 绑定、reviewer ≠ author（D3/D4）
3. 受保护路径的写入有结构化解释事件（D5）
4. **测试执行点存在且已接线**（change adopter-test-gate / issue #4，见
   `_tests_execution_point`）——只做存在性与字符串检查，**不执行**那条命令

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
from witnessloop import evidence as evidence_mod
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

    base = gitutil.resolve_base(root, args.base)
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
        evidence_patterns=pol.stale_exempt_paths,
    )

    # 本次 diff 触及的 change：**active ∪ 归档授予**（change archive-awareness / issue #21）。
    # 归档 move 把那个 change「归属」回本次 diff——**不豁免任何东西**：它照旧走下面同一套门禁，
    # 只是路径落在 `archive/<name>/` 下、`change_id` 多一个别名（D8）。⚠️ 以**目录**为键（列表）：
    # 同一个 id 可以同时来自 active 与归档，两份都要校验。
    targets = contract.change_targets(root, pol, changes)
    change_ids = sorted({target.change_id for target in targets})
    # building-review-gate：**本次 diff 落了实现**（触及 require_change_for）⇒ 每个被触及的 change
    # 都要有实现后的独立审阅证据。触发用**客观的 diff 事实**，不用「tasks 是否勾选」那种自声明
    # （不勾选就能绕过）。**多 change 同 PR 时每个都要**——「一个 PR 推进一个 change」是前提。
    code_hits = _code_hits(pol, changes)
    findings: list[contract.Finding] = []
    for target in targets:
        findings += contract.validate_change_dir(
            root, pol, target.change_id, directory=target.directory, label=target.label
        )
        findings += contract.validate_review_manifests(
            root, pol, target.change_id, scope=scope,
            directory=target.directory, label=target.label,
            accepted_change_ids=target.accepted_change_ids,
        )
        # D9/#2：报告正文的**完备性**——与本地 `guard` 共用同一个判定（evidence.py）。
        findings += evidence_mod.grill_evidence_findings_in_change(
            target.directory,
            grill_stage=pol.grill_stage,
            manifest_glob=pol.review_manifest_glob,
            label=target.label,
        )
        # building-review-gate / issue #13 + grill-adversarial-gate / issue #16：本次 diff 落了实现 ⇒
        # 该 change 的**设计环**（对抗验证轮）与**实现环**（独立审阅）**两端**都要有证据。
        # 两者**共用同一条 `code_hits` 触发**（一个概念，不引入第二套「什么算代码」），且都只要求
        # **证据存在**（+ 复用既有 revision 绑定保证「发生在最终 revision 之上」）——
        # **不解析报告里的 verdict 文本**、不校验正文（见 docs/gate.md §9 building / §10 grill-adversarial）。
        if code_hits:
            findings += evidence_mod.stage_manifest_findings_in_change(
                target.directory,
                stage=pol.grill_adversarial_stage,
                manifest_glob=pol.review_manifest_glob,
                label=target.label,
                reason="设计阶段的对抗验证轮（grill 之后、停轮之前的证伪环节）必须有审阅证据",
            )
            findings += evidence_mod.stage_manifest_findings_in_change(
                target.directory,
                stage=pol.building_stage,
                manifest_glob=pol.review_manifest_glob,
                label=target.label,
                reason="本 change 改了受管控代码，必须有实现后的独立审阅证据（review-loop）",
            )
    findings += _tests_execution_point(root, pol)
    findings += _require_change(pol, changes, change_ids)
    findings += _protected_writes(root, pol, changes)

    _report(base, head, changes, targets, findings)
    return C.EXIT_FAIL if findings else C.EXIT_PASS


def _tests_execution_point(root: Path, pol: policy_mod.Policy) -> list[contract.Finding]:
    """D4：策略声明了测试执行点 ⇒ 要求「**文件存在 + 去空白非空 + 不含哨兵**」。

    **零依赖**：只看文件与字符串，**不解析 YAML、不执行该命令**——执行是 `gate.yml`
    那一步的职责（这里跑命令会既慢又给出错误归因）。

    第三条判据（非空）不可省：只判「存在 + 无哨兵」时，**空文件**会让 `check` 判绿
    **且** 门禁 `sh -c ""` 退 0 ⇒ 「有执行点、门禁跑了、required 绿、一个测试没跑」，
    正是 issue #4 的形态外加一枚绿勾（grill v2 实测）。
    """
    if pol.tests_disabled:
        # 显式 opt-out（`tests.disabled: true`）⇒ 本条不判。
        # ⚠️ 它**只关这条判定**：门禁那一步照旧「文件在就跑、不在就跳过」（正交）。
        return []

    rel = C.ADOPTER_TESTS_PATH
    path = root / rel
    if not path.is_file():
        return [
            contract.Finding(
                rel,
                "策略声明了测试执行点，但该文件不存在（执行点缺失）。"
                "写入要跑的测试命令，或在 policy 里显式 `tests.disabled: true` 退出这条判定。",
            )
        ]
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # 读不出 ⇒ 不可核验 ⇒ 红（与「证据文件读不出」同口径）。绝不静默放行。
        why = "无法解码" if isinstance(exc, UnicodeDecodeError) else "无法读取"
        return [contract.Finding(rel, f"测试执行点{why}：{exc}")]

    if not content.strip():
        return [
            contract.Finding(
                rel,
                "测试执行点为空（未接线）。空文件会让 `check` 与门禁**同时**判绿而一个测试都不跑。",
            )
        ]
    if C.ADOPTER_TESTS_SENTINEL in content:
        return [
            contract.Finding(
                rel,
                f"测试执行点未接线（仍是哨兵 {C.ADOPTER_TESTS_SENTINEL}）。"
                "把它替换成真实的测试命令。",
            )
        ]
    return []


def _code_hits(pol: policy_mod.Policy, changes) -> list[str]:
    """本次 diff 里命中 `policy.require_change_for` 的路径。

    「**什么算代码**」的**唯一**口径——`_require_change`（改代码必须挂 change）、`building` 门禁
    （落了实现必须有实现后审阅）与 `grill-adversarial` 门禁（落了实现必须有设计对抗轮证据）
    **三者共用它**。分两份实现必然漂移（本仓已因「两边各写一套」踩过坑）。
    """
    if not pol.require_change_for:
        return []
    return sorted(
        {
            pathutil.normalize(path)
            for change in changes
            for path in (change.path, change.old_path)
            if path and pathutil.matches_any(pathutil.normalize(path), pol.require_change_for)
        }
    )


def _require_change(pol: policy_mod.Policy, changes, change_ids) -> list[contract.Finding]:
    """改了代码就必须挂一个 change 目录。

    没有这条时，`check` 只保证「**如果你**动了 change 目录/受保护路径，它要齐备」，
    于是最省事的绕过方式是什么都不建——只改 `src/` 的 PR 直接放行。

    ⚠️ **归档感知（issue #21）不是给它加豁免**：`change_ids` 现在由 `change_targets` 派生
    （active ∪ 归档授予），所以「实现 PR 同时归档」那张 PR 的集合**非空** ⇒ 这一条自然修好。
    给它加一个「有归档 move 就返回 []」的分支是**错的**——那会让归档 + 改代码的 PR
    连三条 stage 证据门也一起绕过（实测 0 项红 = 放行）。
    """
    if change_ids:
        return []
    hits = _code_hits(pol, changes)
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
        # 归档 = 把已审的 change 从 active 挪进 archive/ 的**纯改名**，是簿记动作，
        # 不是受保护写入。豁免面刻意收窄（见 contract.is_archive_move）：
        # 带走内容改动的移动、以及 archive 里的删改，仍都要解释事件。
        if contract.is_archive_move(change, pol.changes_root):
            continue

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
            if by_invariant and status[:1] == "A":
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


def _report(base, head, changes, targets, findings) -> None:
    # flush：不 flush 的话 stdout 缓冲会让摘要排在 stderr 的失败明细后面。
    #
    # ⚠️ `N 个 change 目录` 这个**子串**被 `tests/test_check_contract.py` 钉着（`0 个 change 目录`），
    # 别改措辞；计数按**去重后的 id** 算（归档 id 也计入）。
    change_ids = sorted({target.change_id for target in targets})
    print(
        f"check：基线 {base}...{head}，{len(changes)} 个变更文件，"
        f"{len(change_ids)} 个 change 目录",
        flush=True,
    )
    if targets:
        shown = ", ".join(
            f"{target.change_id}（归档）" if target.archived else target.change_id
            for target in targets
        )
        print(f"  change：{shown}", flush=True)
    if not findings:
        print("check：通过 ✓")
        return
    print(f"check：未通过 ✗（{len(findings)} 项）", file=sys.stderr)
    for index, finding in enumerate(findings, 1):
        print(f"  {index}. {finding.path}：{finding.message}", file=sys.stderr)
