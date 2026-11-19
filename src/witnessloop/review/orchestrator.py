"""``witnessloop review run``：多模型复审闭环（P4）。

一轮 = 两路 reviewer 并发审 → 合并去重（**只按 ``where``，取 severity 高的那条**）
→ fixer 按 findings 出修复方案 → 收敛判断（``pass_rule``）/ 停滞升级（``stall_rounds``
内同一 finding 连续重报 ⇒ 升级 judge 单点复核）/ 成本止损（``budget.max_cost_usd``）。

每轮写一份 manifest 到 ``.reviewloop/rounds/round-<n>.json``，绑：

* ``actors[]``：每个出场的角色 = {role, adapter, model, run_id, degraded_from}；
* ``config_hash``：``config.resolved.json`` 的 sha256。

回落规则（**机械执行，不静默**）：任一 reviewer 通路返回 auth / balance /
model_not_found（或 auth 一开始就没解析到）⇒ 该角色当场回落 ``deepseek-flash``，
manifest 与报告里标 ``degraded_from``。两路都回落时，``final.degraded_note`` 写
「本轮为同源双审」。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from witnessloop import constants as C
from witnessloop import gitutil
from witnessloop import policy as policy_mod
from witnessloop.review import adapters as A
from witnessloop.review import revision as R
from witnessloop.review import roles as roles_mod

#: 收敛看这些 severity（pass_rule=medium_plus_zero）。
BLOCKING_SEVERITIES = ("blocker", "high", "medium")

#: 回落目标：deepseek-flash（经 claude 通路）。
FALLBACK_ADAPTER = "claude"
FALLBACK_MODEL = C.REVIEW_FALLBACK_MODEL

#: 审阅上下文里 diff 的字符上限。代码/测试路径优先；超出后截断并明确标注。
#: 20k 太小：真实 change 的 diff 会先被 docs/change 文档吃掉，reviewer 看不到实现。
DIFF_CONTEXT_LIMIT = 120_000
#: diff 里优先展示的路径前缀（代码/测试/模板/插件/脚本）。
_CODE_DIFF_PREFIXES = ("src/", "tests/", "templates/", "plugin/", "scripts/")


REVIEWER_PROMPT = (
    "你是一个**零记忆的独立代码审阅者**。只根据下面给你的上下文审阅，不要假设上下文之外的信息。\n"
    "逐条核对 tasks.md 声称完成的工作是否真实存在于代码里；检查正确性、spec 对齐、"
    "测试覆盖、安全性、可维护性。\n"
    "只输出一个 JSON 对象，不要任何其它文字：\n"
    '{"verdict": "PASS" | "CHANGES_REQUESTED", "findings": ['
    '{"where": "文件:行号或符号", "severity": "blocker|high|medium|low|nit", '
    '"what": "问题是什么", "suggestion": "怎么修"}]}\n'
    "只报你**有把握**的 medium 及以上问题；没有就把 findings 留空、verdict 用 PASS。"
)


FIXER_PROMPT = (
    "你是一个**修复执行者**。下面是审阅者报出的 findings（已合并去重）。"
    "对每一条给一个**具体**的修复方案（文件、位置、改成什么样）。\n"
    "只输出一个 JSON 对象，不要任何其它文字：\n"
    '{"fixes": [{"where": "…", "action": "改成什么样的具体描述"}]}'
)


JUDGE_PROMPT = (
    "你是一个**单点复核 judge**。两路 reviewer 在下面这些 findings 上连续多轮未能收敛，"
    "请你独立裁定每一条是否**属实**（real / false-positive / uncertain），并给最终 verdict。\n"
    "只输出一个 JSON 对象，不要任何其它文字：\n"
    '{"verdict": "PASS" | "CHANGES_REQUESTED" | "BLOCKED", '
    '"rulings": [{"where": "…", "ruling": "real|false-positive|uncertain", "reason": "…"}]}'
)


@dataclass
class Actor:
    role: str
    adapter: str
    model: str
    run_id: str
    degraded_from: str | None = None


@dataclass
class RoundRecord:
    round: int
    revision: R.Revision
    config_hash: str
    actors: list[dict]
    findings: list[dict]
    verdict: str
    cost_usd: float
    fixer: dict | None = None
    judge: dict | None = None
    note: str | None = None


def _parse_mock_scenario(raw: str | None) -> dict:
    """``--mock-scenario`` 是 JSON 字符串（如 ``{"1": [{...}], "2": []}``）⇒ 解析成 dict。

    键是**字符串**形式的轮号，MockAdapter 用 ``scenario.get(round, [])`` 取——
    键必须是 int，所以这里把数字键转成 int。坏输入 ⇒ 抛 ValueError（用法错误）。
    """
    if not raw:
        return {}
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"--mock-scenario 不是合法 JSON：{exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("--mock-scenario 必须是 JSON 对象")
    allowed = {"blocker", "high", "medium", "low", "nit"}
    out: dict = {}
    for key, value in doc.items():
        try:
            round_no = int(key)
        except (TypeError, ValueError):
            raise ValueError(f"--mock-scenario 的轮号必须是数字：{key!r}") from None
        if not isinstance(value, list):
            raise ValueError(f"--mock-scenario 的 round {key!r} 必须是 findings 数组")
        clean: list[dict] = []
        for index, finding in enumerate(value):
            if not isinstance(finding, dict):
                raise ValueError(
                    f"--mock-scenario 的 round {key!r} findings[{index}] 必须是对象"
                )
            severity = str(finding.get("severity") or "").strip().lower()
            if severity not in allowed:
                raise ValueError(
                    f"--mock-scenario 的 round {key!r} findings[{index}] "
                    f"severity 非法：{finding.get('severity')!r}"
                )
            clean.append(dict(finding, severity=severity))
        out[round_no] = clean
    return out


def _merge_findings(batches: list[list[dict]]) -> list[dict]:
    """合并去重：**只按 ``where``**，同 ``where`` 取 severity 高的那条。

    两条 finding 的 ``where`` 逐字相同才算同一条；severity 用 ``adapters.severity_rank``
    比较，保留高的一条（等价时保留先出现的那条）。**没有 ``where`` 的 finding 不再
    丢弃**——用合成 ``where`` 保留，避免真实 blocker 因模型漏写定位而静默变成 PASS。
    """
    best: dict[str, dict] = {}
    order: list[str] = []
    for batch_index, batch in enumerate(batches):
        for item_index, finding in enumerate(batch):
            if not isinstance(finding, dict):
                continue
            where = str(finding.get("where") or "").strip()
            if not where:
                # 没有 where 的 medium+ 绝不能静默丢成 PASS：用合成 where 保留，
                # 让它继续参与收敛判定并出现在报告里（不去重——没有共同键）。
                where = f"<missing-where>:batch{batch_index}:item{item_index}"
                finding = dict(finding, where=where)
            current = best.get(where)
            if current is None:
                best[where] = dict(finding)
                order.append(where)
            elif A.severity_rank(str(finding.get("severity"))) > A.severity_rank(
                str(current.get("severity"))
            ):
                best[where] = dict(finding)
    return [best[where] for where in order]


def _pass_rule_satisfied(findings: list[dict], pass_rule: str) -> bool:
    """收敛判据。当前只实现默认 ``medium_plus_zero``。"""
    if pass_rule != C.DEFAULT_PASS_RULE:
        raise ValueError(f"未知 pass_rule：{pass_rule!r}")
    return not any(
        str(f.get("severity", "")).strip().lower() in BLOCKING_SEVERITIES
        for f in findings
    )


def _prioritize_diff(diff: str, limit: int = DIFF_CONTEXT_LIMIT) -> str:
    """把 diff 按「代码/测试优先」排序后截断。

    直接 `diff[:20000]` 会让 docs / change 文档先吃掉预算，reviewer 根本看不到
    `src/**`——实测因此把「没看到代码」误报成「代码不存在」。这里按 `diff --git`
    分节，代码/测试节先出，超出 `limit` 才截断并显式标注。
    """
    if len(diff) <= limit:
        return diff
    sections = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)

    def _is_code(section: str) -> bool:
        first = section.splitlines()[0] if section else ""
        return any(f"a/{prefix}" in first for prefix in _CODE_DIFF_PREFIXES)

    ordered = [s for s in sections if _is_code(s)] + [
        s for s in sections if not _is_code(s)
    ]
    out: list[str] = []
    used = 0
    for section in ordered:
        if used >= limit:
            break
        remaining = limit - used
        if len(section) > remaining:
            out.append(
                section[:remaining]
                + "\n…（diff 已截断；完整内容用 `git diff` 查看）\n"
            )
            break
        out.append(section)
        used += len(section)
    return "".join(out)


def _build_context(
    root: Path, change: str, revision: R.Revision, policy, base_ref: str | None = None
) -> str:
    """审阅素材：change 的 tasks / design + 实际 diff（git 模式）或工作树说明（digest）。"""
    pieces: list[str] = []
    directory = root / policy.changes_root / change
    for name in ("tasks.md", "design.md", "proposal.md"):
        path = directory / name
        if path.is_file():
            pieces.append(f"== {name} ==\n{path.read_text(encoding='utf-8')[:8000]}")
    if revision.mode == "git":
        base = gitutil.resolve_base(root, base_ref)
        head = revision.value
        try:
            names = gitutil.diff_names(root, base, head)
        except gitutil.GitError:
            names = []
        if names:
            pieces.append("== 变更文件 ==\n" + "\n".join(names))
        try:
            diff = gitutil.diff_text(root, base, head)
        except gitutil.GitError as exc:
            # 没有 diff 就没有代码审阅素材；不能带着「无法取 diff」继续跑并可能
            # 产出绑定当前提交的 PASS 产物。
            raise gitutil.GitError(
                f"无法取 diff（review 不能在没有代码变更的情况下继续）：{exc}"
            ) from exc
        pieces.append(
            f"== diff（{base}..{head}；代码/测试优先，上限 {DIFF_CONTEXT_LIMIT} 字符）==\n"
            + _prioritize_diff(diff)
        )
    else:
        pieces.append(
            "== 工作树 ==\n"
            "（digest 模式，无 git 历史/diff；**不要因为看不到代码就报「代码不存在」**。"
            "本模式只能审 change 文档与下面列出的文件清单；要审实现请用 git 模式。）"
        )
        skip = {".git", "__pycache__", ".reviewloop", ".pytest_cache", ".venv"}
        tree: list[str] = []
        for base in ("src", "tests", "templates", "plugin"):
            directory = root / base
            if not directory.is_dir():
                continue
            for path in sorted(directory.rglob("*")):
                if path.is_file() and not (set(path.parts) & skip):
                    tree.append(str(path.relative_to(root)))
        if tree:
            pieces.append("== 工作树文件（前 500 个）==\n" + "\n".join(tree[:500]))
    return "\n\n".join(pieces)


def _actor_run_id(role: str, adapter: str, revision: R.Revision) -> str:
    """一个确定性 run id（role + adapter + revision 短摘要）——「两路同一 actor」负样本
    据此可判定：reviewerA 与 reviewerB 的 run_id 相同 ⇒ 同一 actor。"""
    return f"{role}-{adapter}-{revision.value[:12]}"


def _resolve_auth_token(role: dict) -> str:
    """读一个角色的 auth token——**委托 adapters 的同一实现**。

    历史教训：这里曾有一套带 ``ANTHROPIC_*`` 兜底的解析，而 ``build_adapter``
    只认 ``auth_token`` / ``auth_env``；当 key 只住在 ``ANTHROPIC_AUTH_TOKEN`` 时，
    预检说「有 key」、适配器却拿到空串，回落路径还会重复打一次空 key 的请求。
    两处必须共用 ``adapters.resolve_auth_token``；``ANTHROPIC_*`` 兜底现在只有
    角色显式 ``allow_host_auth_fallback: true`` 才生效。
    """
    return A.resolve_auth_token(role)


#: 回落目标（deepseek-flash via claude）的固定通路。key 经 `_resolve_auth_token` 的链式兜底找。
FALLBACK_ROLE = {
    "adapter": FALLBACK_ADAPTER,
    "model": FALLBACK_MODEL,
    "base_url": "https://api.deepseek.com/anthropic",
    "auth_env": "WITNESSLOOP_DEEPSEEK_KEY",
    # **不**默认启用 allow_host_auth_fallback：宿主 ANTHROPIC_* token 不应被
    # 默认发往 deepseek 端点。需要宿主兜底时显式设 WITNESSLOOP_DEEPSEEK_KEY
    # （或以后加显式 opt-in），否则按「回落 key 缺失」判 BLOCKED。
}

#: 连 deepseek 回落 key 都没有时的错误——**不再用 mock 冒充审阅**。
#: 显式 `--adapter mock` 的烟测路径不受影响（那条路不会进入回落分支）。
_NO_FALLBACK_ERROR = (
    "reviewer 通路不可用，且 deepseek 回落 key 也未解析；"
    "拒绝用 mock 冒充审阅（确需无网络烟测请显式 --adapter mock）"
)


def _degrade_to_fallback(role: dict) -> tuple[str, dict, bool]:
    """构造回落角色配置（deepseek-flash via claude）；deepseek key 也不可用 ⇒ mock。

    返回 ``(adapter, role_cfg, still_down)``：``still_down=True`` 表示连 deepseek 都没有。
    调用方**不得**把 mock 当真实审阅继续跑——应返回 ``_NO_FALLBACK_ERROR``，
    由 round 级 `reviewer_errors` 判 BLOCKED。
    """
    if _resolve_auth_token(FALLBACK_ROLE):
        return FALLBACK_ADAPTER, dict(FALLBACK_ROLE), False
    return "mock", {"adapter": "mock", "model": "mock"}, True


def _call_reviewer(
    role_name: str,
    role_cfg: dict,
    request: A.ReviewRequest,
    *,
    scenario: dict | None,
    adapter_override: str | None,
    revision: R.Revision,
) -> tuple[Actor, A.ReviewResult, float]:
    """跑一个 reviewer（含回落）。返回 ``(Actor, ReviewResult, cost)``。"""
    adapter_name = adapter_override or role_cfg.get("adapter") or "mock"
    model = role_cfg.get("model") or FALLBACK_MODEL
    degraded_from: str | None = None
    used_adapter = adapter_name
    is_fallback = False

    if adapter_name != "mock" and not _resolve_auth_token(role_cfg):
        # auth 一开始就缺 ⇒ 直接回落，不白打一次网络。
        degraded_from = model
        is_fallback = True
        used_adapter, role_cfg, still_down = _degrade_to_fallback(role_cfg)
        if still_down:
            # 回落 key 也没有：不跑 mock、不产生「零 findings 的 PASS」。
            actor = Actor(
                role=role_name,
                adapter="mock",
                model="mock",
                run_id=_actor_run_id(role_name, "mock", revision),
                degraded_from=degraded_from,
            )
            result = A.ReviewResult(
                model="mock", error=_NO_FALLBACK_ERROR, error_kind="auth"
            )
            return actor, result, 0.0
        model = FALLBACK_MODEL

    adapter = A.build_adapter(used_adapter, role=role_cfg, scenario=scenario)
    result = adapter.run(request, model=model)
    cost = A.cost_usd(model, result.usage)

    if (
        result.error_kind in ("auth", "balance", "model_not_found", "parse", "other")
        and not is_fallback
    ):
        # 运行期失败 ⇒ 按回落规则当场回落 deepseek-flash（**只回落一次**）。
        # 保留原始 model：先「缺 key 回落」再失败时，不要把 degraded_from 改成回落目标。
        if degraded_from is None:
            degraded_from = model
        used_adapter, fallback_cfg, still_down = _degrade_to_fallback(role_cfg)
        if still_down:
            used_adapter = "mock"
            result = A.ReviewResult(
                model="mock", error=_NO_FALLBACK_ERROR, error_kind="auth"
            )
            model = "mock"
        else:
            adapter = A.build_adapter(used_adapter, role=fallback_cfg, scenario=scenario)
            result = adapter.run(request, model=FALLBACK_MODEL)
            model = FALLBACK_MODEL
            cost += A.cost_usd(model, result.usage)

    actor = Actor(
        role=role_name,
        adapter=used_adapter,
        model=result.model or model,
        run_id=_actor_run_id(role_name, used_adapter, revision),
        degraded_from=degraded_from,
    )
    return actor, result, cost


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    change = args.change
    if not change or "/" in change or "\\" in change:
        print(f"review run：change={change!r} 必须是单段 change id", file=sys.stderr)
        return C.EXIT_USAGE

    try:
        pol = policy_mod.load_policy(root)
    except policy_mod.PolicyError as exc:
        print(f"review run：policy 非法：{exc}", file=sys.stderr)
        return C.EXIT_FAIL
    if pol is None:
        print(
            f"review run：未接入 witnessloop（没有 {C.POLICY_PATH}）——先 `witnessloop init`。",
            file=sys.stderr,
        )
        return C.EXIT_NOT_ONBOARDED

    directory = root / pol.changes_root / change
    if not directory.is_dir():
        print(
            f"review run：change 目录不存在：{pol.changes_root}/{change}", file=sys.stderr
        )
        return C.EXIT_FAIL

    # 用法错误在落盘前判掉：坏 pass_rule / 坏 mock-scenario 不应以 traceback 收场。
    if args.pass_rule != C.DEFAULT_PASS_RULE:
        print(
            f"review run：不支持的 pass_rule={args.pass_rule!r}"
            f"（当前只支持 {C.DEFAULT_PASS_RULE}）",
            file=sys.stderr,
        )
        return C.EXIT_USAGE
    try:
        scenario = _parse_mock_scenario(getattr(args, "mock_scenario", None))
    except ValueError as exc:
        print(f"review run：{exc}", file=sys.stderr)
        return C.EXIT_USAGE

    # 上一次 run 的 round 文件不能混进本次报告（report 会读整个 rounds/ 目录）。
    _reset_rounds(root)

    revision = R.resolve_revision(root, args.mode)

    try:
        roles_doc = roles_mod.load_roles(root)
        resolved, warnings = roles_mod.resolve_config(
            root,
            roles_doc=roles_doc,
            mode=args.mode,
            pass_rule=args.pass_rule,
            stall_rounds=args.stall_rounds,
            budget_max_cost_usd=args.budget_max_cost_usd,
            adapter=args.adapter,
        )
    except ValueError as exc:
        print(f"review run：{exc}", file=sys.stderr)
        return C.EXIT_FAIL

    if args.positive_control:
        resolved["positive_control"] = {"where": args.positive_control}
    roles_mod.write_config(root, resolved)
    config_hash = roles_mod.config_hash(resolved)

    # 实际调用用**未脱敏**的运行时角色表（保留内联 auth_token）；写盘的
    # config.resolved.json 仍是脱敏版本。
    role_cfgs = roles_mod.runtime_roles(roles_doc, adapter=args.adapter)
    try:
        context = _build_context(root, change, revision, pol, getattr(args, "base", None))
    except gitutil.GitError as exc:
        print(f"review run：{exc}", file=sys.stderr)
        return C.EXIT_FAIL

    round_manifests: list[dict] = []
    merged_history: list[dict] = []  # 每轮的 merged findings（用于停滞判定）
    cumulative_cost = 0.0
    budget = float(args.budget_max_cost_usd)
    final_verdict = "BLOCKED"
    final_note = None

    for round_no in range(1, args.max_rounds + 1):
        # fixer 成本可能把累计值推过预算；下一轮开始前再检查一次，避免继续发
        # 两路 reviewer 请求后才发现超支。
        if round_no > 1 and cumulative_cost > budget:
            final_verdict = "BLOCKED"
            final_note = (
                f"成本止损（进入第 {round_no} 轮前累计 ${cumulative_cost:.4f} "
                f"> budget ${budget:.2f}）"
            )
            break
        request = A.ReviewRequest(
            prompt=REVIEWER_PROMPT, context=context, round=round_no
        )
        # 两路 reviewer 并发审。
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(
                    _call_reviewer,
                    role_name,
                    role_cfgs[role_name],
                    request,
                    scenario=scenario,
                    adapter_override=args.adapter,
                    revision=revision,
                ): role_name
                for role_name in roles_mod.REVIEWER_ROLES
            }
            reviewer_results: dict[str, tuple[Actor, A.ReviewResult, float]] = {}
            for fut in futures:
                role_name = futures[fut]
                reviewer_results[role_name] = fut.result()

        actors = [reviewer_results[r][0] for r in roles_mod.REVIEWER_ROLES]
        batches = [reviewer_results[r][1].findings for r in roles_mod.REVIEWER_ROLES]
        round_cost = sum(reviewer_results[r][2] for r in roles_mod.REVIEWER_ROLES)
        cumulative_cost += round_cost

        merged = _merge_findings(batches)
        # reviewer 通路失败（含输出无法解析）时 findings 为空——绝不能因此判 PASS。
        # 回落已由 `_call_reviewer` 机械执行；这里是**最后一次**失败的结果。
        reviewer_errors = {
            role: str(res.error)
            for role, (_, res, _) in reviewer_results.items()
            if res.error
        }
        verdict = (
            "PASS" if _pass_rule_satisfied(merged, args.pass_rule) else "CHANGES_REQUESTED"
        )
        if reviewer_errors:
            verdict = "BLOCKED"

        # 停滞判定：同一 where 连续 stall_rounds 轮都在 merged 里。
        stalled = _stalled_findings(merged, merged_history, args.stall_rounds)

        fixer_record: dict | None = None
        judge_record: dict | None = None
        note = None
        stop = False

        if reviewer_errors:
            final_verdict = "BLOCKED"
            note = "reviewer 失败（不把空 findings 判 PASS）：" + "; ".join(
                f"{role}={err}" for role, err in sorted(reviewer_errors.items())
            )
            stop = True
        elif verdict == "PASS":
            final_verdict = "PASS"
            note = "收敛：medium+ 为零"
            stop = True
        elif cumulative_cost > budget:
            # 预算检查在 judge / fixer 之前：超预算就不再发起额外付费调用。
            # （单次调用本身可能把累计值推过上限——预算是软止损，不做事前额度预留。）
            final_verdict = "BLOCKED"
            note = f"成本止损（累计 ${cumulative_cost:.4f} > budget ${budget:.2f}）"
            stop = True
        elif stalled:
            # 升级 judge 单点复核，不继续磨。
            judge_record, judge_cost = _run_judge(
                stalled, role_cfgs["judge"], request, scenario, args.adapter, revision
            )
            cumulative_cost += judge_cost
            judge_verdict = str(judge_record.get("verdict", "BLOCKED")).upper()
            stalled_set = set(stalled)
            uncovered = [
                finding
                for finding in merged
                if str(finding.get("where")) not in stalled_set
                and str(finding.get("severity", "")).lower() in BLOCKING_SEVERITIES
            ]
            if judge_verdict == "PASS" and uncovered:
                # judge 只看到 stalled 子集；它的 PASS 不能替未送审的 blocking finding 背书。
                final_verdict = "BLOCKED"
                note = (
                    f"停滞升级 judge（stall_rounds={args.stall_rounds}）："
                    f"{', '.join(stalled)}；judge 只复核了停滞子集，仍有未复核的 "
                    f"medium+：{', '.join(str(f.get('where')) for f in uncovered)}"
                )
            else:
                final_verdict = judge_verdict
                note = (
                    f"停滞升级 judge（stall_rounds={args.stall_rounds}）："
                    f"{', '.join(stalled)}"
                )
            if judge_record.get("error"):
                note = f"{note}；judge 失败：{judge_record['error']}"
            stop = True
        else:
            # 未收敛：跑 fixer（记录修复方案；不自动改代码，见 docs/merge-report）。
            fixer_record, fixer_cost = _run_fixer(
                merged, role_cfgs["fixer"], request, scenario, args.adapter, revision
            )
            cumulative_cost += fixer_cost
            if fixer_record.get("error"):
                note = f"fixer 失败：{fixer_record['error']}"

        record = RoundRecord(
            round=round_no,
            revision=revision,
            config_hash=config_hash,
            actors=[_actor_dict(a) for a in actors],
            findings=merged,
            verdict=verdict,
            cost_usd=round_cost,
            fixer=fixer_record,
            judge=judge_record,
            note=note,
        )
        manifest = _round_manifest(record)
        round_manifests.append(manifest)
        _write_round_manifest(root, round_no, manifest)
        merged_history.append(merged)

        if stop:
            final_note = note
            break
        # 未收敛且未停滞/未超预算：进入下一轮（fixer 的修复方案已记录在上一轮 manifest）。

    if final_note is None:
        final_note = f"达到最大轮数 {args.max_rounds} 仍未收敛"

    # 收尾：写最终 summary.json（final verdict / 轮数 / 累计成本等元数据）。
    _write_final_report(
        root,
        revision=revision,
        config_hash=config_hash,
        resolved=resolved,
        warnings=warnings,
        round_manifests=round_manifests,
        final_verdict=final_verdict,
        final_note=final_note,
        cumulative_cost=cumulative_cost,
    )

    print(
        f"review run：完成 change={change} mode={revision.mode} "
        f"rounds={len(round_manifests)} verdict={final_verdict} "
        f"cost=${cumulative_cost:.4f}",
        flush=True,
    )
    if final_verdict == "PASS":
        return C.EXIT_PASS
    return C.EXIT_FAIL


def _stalled_findings(
    merged: list[dict], history: list[dict], stall_rounds: int
) -> list[str]:
    """当前 merged 里、连续出现在最近 ``stall_rounds`` 轮的 where 列表。"""
    if stall_rounds < 1 or not merged:
        return []
    current = {str(f.get("where")) for f in merged}
    out: list[str] = []
    for where in sorted(current):
        count = 1
        for past in reversed(history):
            if where in {str(f.get("where")) for f in past}:
                count += 1
            else:
                break
        if count >= stall_rounds:
            out.append(where)
    return out


def _run_fixer(merged, fixer_cfg, request, scenario, adapter_override, revision):
    adapter_name = adapter_override or fixer_cfg.get("adapter") or "mock"
    if adapter_name == "mock":
        return {"fixes": [{"where": f.get("where"), "action": "mock 修复（已登记）"} for f in merged]}, 0.0
    fix_request = A.ReviewRequest(
        prompt=FIXER_PROMPT,
        context=json.dumps(merged, ensure_ascii=False, indent=2),
        round=request.round,
    )
    adapter = A.build_adapter(adapter_name, role=fixer_cfg, scenario=scenario)
    result = adapter.run(fix_request, model=fixer_cfg.get("model") or FALLBACK_MODEL)
    doc = A._extract_json(result.raw) if result.raw else None
    fixes = (doc or {}).get("fixes") if isinstance(doc, dict) else None
    record = {
        "fixes": fixes if isinstance(fixes, list) else [],
        "raw": result.raw,
    }
    # reviewer 解析器要求 findings 数组；fixer 的合法输出是 fixes，会被它误标
    # parse 失败。只有 **fixes 也解析不出来** 时才算 fixer 失败。
    if result.error and not isinstance(fixes, list):
        # fixer 失败不能静默：错误进 manifest，loop 继续但产物里必须看得到。
        record["error"] = result.error
        record["error_kind"] = result.error_kind
    return record, A.cost_usd(result.model, result.usage)


def _run_judge(stalled, judge_cfg, request, scenario, adapter_override, revision):
    adapter_name = adapter_override or judge_cfg.get("adapter") or "mock"
    if adapter_name == "mock":
        return {"verdict": "BLOCKED", "rulings": [{"where": w, "ruling": "uncertain"} for w in stalled]}, 0.0
    judge_request = A.ReviewRequest(
        prompt=JUDGE_PROMPT,
        context=json.dumps({"stalled": stalled}, ensure_ascii=False, indent=2),
        round=request.round,
    )
    adapter = A.build_adapter(adapter_name, role=judge_cfg, scenario=scenario)
    result = adapter.run(judge_request, model=judge_cfg.get("model") or FALLBACK_MODEL)
    doc = A._extract_json(result.raw) if result.raw else None
    if not isinstance(doc, dict):
        doc = {}
    rulings = doc.get("rulings") if isinstance(doc.get("rulings"), list) else []
    guessed_verdict = str(doc.get("verdict") or "BLOCKED").upper()
    record = {
        "verdict": guessed_verdict,
        "rulings": rulings,
        "raw": result.raw,
    }
    # 同 fixer：judge 的合法输出是 rulings，不是 findings；解析器误标 parse 失败
    # 不应盖过 raw 里形状正确的裁决。真正的失败由 ruling 覆盖检查兜底。
    shape_ok = bool(rulings) and guessed_verdict in (
        "PASS",
        "CHANGES_REQUESTED",
        "BLOCKED",
    )
    problem: str | None = None
    if result.error and not shape_ok:
        problem = result.error
    if guessed_verdict == "PASS":
        # PASS 必须逐条覆盖送审的 stalled 项，且每条都是 false-positive；
        # 只凭一个 verdict 字段不足以放行。
        # 同一个 where 可能被裁多次；保守处理：只要出现任何非 false-positive
        # 裁决就不得 PASS（后一条不能覆盖前一条 real/uncertain）。
        by_where: dict[str, set[str]] = {}
        for ruling in rulings:
            if not isinstance(ruling, dict):
                continue
            where = str(ruling.get("where"))
            by_where.setdefault(where, set()).add(
                str(ruling.get("ruling") or "").strip().lower()
            )
        missing = [where for where in stalled if where not in by_where]
        not_cleared = [
            where
            for where, ruling_set in by_where.items()
            if ruling_set != {"false-positive"}
        ]
        if not rulings:
            problem = "judge 返回 PASS 但没有 rulings"
        elif missing:
            problem = f"judge 返回 PASS 但未覆盖 stalled 项：{', '.join(missing)}"
        elif not_cleared:
            problem = (
                "judge 返回 PASS 但存在非 false-positive 裁决："
                + ", ".join(not_cleared)
            )
    if problem:
        record["verdict"] = "BLOCKED"
        record["error"] = problem
        record["error_kind"] = result.error_kind or "judge"
    return record, A.cost_usd(result.model, result.usage)


def _actor_dict(actor: Actor) -> dict:
    out = {
        "role": actor.role,
        "adapter": actor.adapter,
        "model": actor.model,
        "run_id": actor.run_id,
    }
    if actor.degraded_from:
        out["degraded_from"] = actor.degraded_from
    return out


def _round_manifest(record: RoundRecord) -> dict:
    doc = {
        "schema": C.REVIEW_ROUND_SCHEMA,
        "round": record.round,
        "revision": {"mode": record.revision.mode, "value": record.revision.value},
        "config_hash": record.config_hash,
        "actors": record.actors,
        "verdict": record.verdict,
        "findings": record.findings,
        "cost_usd": round(record.cost_usd, 6),
        "fixer": record.fixer,
        "judge": record.judge,
        "note": record.note,
    }
    return doc


def _reset_rounds(root: Path) -> None:
    """清掉上一次 run 的 round/summary，避免 report 把两次 run 混读。

    `.reviewloop/` 是本地审计目录，不是跨 run 的持久账本；一次 `review run`
    的输出必须只包含本次的轮次。旧 round 若残留，report 会照读并可能把两次
    run 的 config_hash 差异误报成「篡改 manifest」。
    """
    out_dir = Path(root) / C.REVIEW_OUTPUT_DIR
    rounds_dir = out_dir / C.REVIEW_ROUNDS_SUBDIR
    if rounds_dir.is_dir():
        for path in rounds_dir.glob("round-*.json"):
            path.unlink()
    summary = out_dir / "summary.json"
    if summary.is_file():
        summary.unlink()


def _write_round_manifest(root: Path, round_no: int, doc: dict) -> Path:
    out_dir = Path(root) / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"round-{round_no:04d}.json"
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _write_final_report(
    root: Path,
    *,
    revision: R.Revision,
    config_hash: str,
    resolved: dict,
    warnings: list[str],
    round_manifests: list[dict],
    final_verdict: str,
    final_note: str | None,
    cumulative_cost: float,
) -> Path:
    degraded_note = None
    if round_manifests:
        last = round_manifests[-1]
        reviewers = [a for a in last.get("actors", []) if a.get("role", "").startswith("reviewer")]
        if reviewers and all(a.get("degraded_from") for a in reviewers):
            if any(str(a.get("model") or "") == "mock" for a in reviewers):
                # 连回落 key 都没有的 mock 降级不是「同源双审」，不能误导成
                # 「两路真实模型都回落到了同一个模型」。
                degraded_note = "本轮存在 mock 降级（不代表真实双审）"
            else:
                degraded_note = "本轮为同源双审"
    doc = {
        "schema": C.REVIEW_ROUND_SCHEMA,
        "final_verdict": final_verdict,
        "final_note": final_note,
        "degraded_note": degraded_note,
        "revision": {"mode": revision.mode, "value": revision.value},
        "config_hash": config_hash,
        "cumulative_cost_usd": round(cumulative_cost, 6),
        "warnings": warnings,
        "rounds": round_manifests,
    }
    out_dir = Path(root) / C.REVIEW_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.json"
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
