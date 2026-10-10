"""``witnessloop manifest build``：产出 `check` 认的 review manifest。

证据回路要闭合——审阅跑完必须能落一份 manifest，而且**必须与 `check` 共用同一套
哈希实现**（``constants.HASHED_ARTIFACTS`` + ``hashing.sha256_tree``），
否则「产出的 manifest」和「校验的期望」会各走各的、悄悄漂移。

提交约定（docs/gate.md §3.1）：**先内容、后证据**。跑 build 时应停在内容提交上，
``head_sha`` 就取当时的 HEAD；随后把报告 + manifest 单独提交。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from witnessloop import agentenv
from witnessloop import constants as C
from witnessloop import contract
from witnessloop import gitutil, policy as policy_mod
from witnessloop import paths as pathutil
from witnessloop.hashing import sha256_bytes, sha256_tree

#: 报告必须落在 change 目录的这个子目录下（gate.md §1 的布局约定、§3 的边界）。
REPORT_PREFIX = "reviews/"


def _fail(message: str, code: int = C.EXIT_FAIL) -> int:
    print(f"manifest build：{message}", file=sys.stderr)
    return code


def run_build(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        return _fail(f"目标目录不存在：{root}")

    try:
        pol = policy_mod.load_policy(root)
    except policy_mod.PolicyError as exc:
        return _fail(f"policy 非法：{exc}")
    if pol is None:
        return _fail(
            "未接入 witnessloop（没有 "
            f"{C.POLICY_PATH}）——先运行 `witnessloop init`。",
            C.EXIT_NOT_ONBOARDED,
        )

    change_id = args.change
    changes_root = root / pol.changes_root
    directory = changes_root / change_id
    # 与 --report 同款守卫：change id 与 report path 是同一类 agent 输入，
    # 一个守一个不守就会留下「写到仓外」的口子（回归 M2 §4-1）。
    if not pathutil.is_within(directory, changes_root):
        return _fail(
            f"change={change_id!r} 逃逸出 {pol.changes_root.rstrip('/')}/"
            "——change id 必须落在 changes root 之内"
        )

    # 与 check 同一套契约判定：否则会出现「build 报成功、check 立刻拒」的自相矛盾
    # （回归 M2 §4-2）。
    contract_findings = contract.validate_change_dir(root, pol, change_id)
    if contract_findings:
        detail = "\n  ".join(f"{f.path}：{f.message}" for f in contract_findings)
        return _fail(f"change 目录不合契约（与 check 同一套判定）：\n  {detail}")

    # 与 `check` 的 hash 校验、孤儿绑定**共用同一个解析器**——口径分歧会让
    # 「build 说 OK、check 反手判孤儿」（回归审阅 §3.3）。
    report_file = contract.resolve_report_path(directory, args.report)
    if report_file is None:
        return _fail(f"report_path={args.report!r} 逃逸出 change 目录")
    # 落盘写**规范**路径：别把 `reviews/./x.md` 这种写法写进证据里。
    report_rel = report_file.relative_to(directory.resolve()).as_posix()
    if not pathutil.matches(report_rel, f"{REPORT_PREFIX}**"):
        # 在 build 时就拦下：报告放在 reviews/ 外虽然能算哈希，但 check 的 stale
        # 判定不把它当证据，会在 CI 里报一条像误报的「旧 revision」（gate.md §3）。
        return _fail(
            f"report_path={args.report!r} 必须落在 {REPORT_PREFIX} 下"
            f"（gate.md §3 的布局约定）"
        )
    if not report_file.is_file():
        return _fail(f"报告不存在：{args.report}")

    # 与 check 同一张表、同一个哈希函数——这是「两边不漂移」的结构性保证。
    hashes: dict[str, str] = {}
    for field, artifact in C.HASHED_ARTIFACTS:
        target = directory / artifact
        if not target.exists():
            return _fail(f"{artifact} 不存在，无法计算 {field}")
        hashes[field] = sha256_tree(target)
    hashes["report_hash"] = sha256_tree(report_file)

    head_sha = gitutil.rev_parse(root, "HEAD")
    if head_sha is None:
        return _fail("仓里还没有提交，无法确定 head_sha")
    base_ref = gitutil.resolve_base(root, args.base)
    base_sha = gitutil.rev_parse(root, base_ref)
    if base_sha is None:
        return _fail(f"无法解析 base ref：{base_ref}")

    # run id：环境优先、**确定性兜底**（#3）——锚取自 change + revision。
    # 幂等键的**完整**形式是 (change, stage, role, revision, base 的解析目标)：
    # 固定 base 与 revision 时，重复 build 得到同一个 id、**逐字节一致**的 manifest；
    # base 漂移会改 base_sha/diff_hash，字节也就不一样了（Q2）。
    anchor = agentenv.default_run_anchor(change_id, head_sha)
    reviewer_run_id = args.reviewer_run_id or agentenv.resolve_run_id(
        args.stage, "reviewer", anchor=anchor
    )
    author_run_id = args.author_run_id or agentenv.resolve_run_id(
        args.stage, "author", anchor=anchor
    )
    if reviewer_run_id == author_run_id:
        return _fail(
            "reviewer_run_id 与 author_run_id 相同：审阅者必须独立于作者"
            "（挡「忘了另开 run」）。没有写出任何文件。"
        )

    try:
        diff_hash = sha256_bytes(gitutil.diff_text(root, base_sha, head_sha).encode())
    except gitutil.GitError as exc:
        return _fail(str(exc))

    doc = {
        "schema": C.SCHEMA_REVIEW_MANIFEST,
        "change_id": change_id,
        "stage": args.stage,
        "reviewer_run_id": reviewer_run_id,
        "author_run_id": author_run_id,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "tasks_hash": hashes["tasks_hash"],
        "spec_hash": hashes["spec_hash"],
        "diff_hash": diff_hash,  # informational（check 不校验内容）
        "report_hash": hashes["report_hash"],
        "report_path": report_rel,
    }

    manifest_rel = f"{pol.changes_root.rstrip('/')}/{change_id}/reviews/{args.stage}.manifest.json"
    manifest_path = root / manifest_rel
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(policy_mod.dumps(doc), encoding="utf-8")

    print(f"manifest build：已写入 {manifest_rel}（未 commit）")
    print(f"  change={change_id} stage={args.stage}")
    print(f"  head_sha={head_sha}  base_sha={base_sha}")
    print(f"  reviewer_run_id={reviewer_run_id}  author_run_id={author_run_id}")
    return C.EXIT_PASS
