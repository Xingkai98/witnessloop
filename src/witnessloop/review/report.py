"""``witnessloop review report --md``：读回 loop 产物，生成 Markdown 报告 + 负样本验证。

读 ``config.resolved.json`` + ``rounds/*.json``（+ 可选 ``summary.json``），
生成人可读的 Markdown，并跑**四条机械验证**（对应验收的 4 条负样本，任一命中 ⇒
退出码 1 = 红）：

1. **篡改 manifest**：某轮 manifest 的 ``config_hash`` ≠ 盘上 ``config.resolved.json``
   的 sha256 ⇒ 证据被改过。
2. **证据缺件**：``config.resolved.json`` 缺失 / 一轮 manifest 都没有 / 某轮文件
   读不出 ⇒ 证据不齐。
3. **两路同一 actor**：某轮 reviewerA 与 reviewerB 的 ``run_id`` 相同 ⇒ 双审退化。
4. **正控漏报**：config 声明了 ``positive_control.where``，且 loop 以 ``PASS`` 收口，
   但该 ``where`` 从未出现在任何一轮的 merged findings 里 ⇒ 已知缺陷被漏报。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from witnessloop import constants as C
from witnessloop.review import roles as roles_mod


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_rounds(root: Path) -> tuple[list[dict], list[str]]:
    """读 ``rounds/*.json``（按 round 字段排序）；``(rounds, errors)``。"""
    rounds_dir = Path(root) / C.REVIEW_OUTPUT_DIR / C.REVIEW_ROUNDS_SUBDIR
    if not rounds_dir.is_dir():
        return [], [f"缺产物目录：{C.REVIEW_OUTPUT_DIR}/{C.REVIEW_ROUNDS_SUBDIR}"]
    rounds: list[dict] = []
    errors: list[str] = []
    for path in sorted(rounds_dir.glob("round-*.json")):
        doc = _load_json(path)
        if not isinstance(doc, dict):
            errors.append(f"round manifest 读不出：{path.name}")
            continue
        if not isinstance(doc.get("round"), int):
            errors.append(f"round manifest 的 round 字段不是整数：{path.name}")
            continue
        rounds.append(doc)
    rounds.sort(key=lambda d: d["round"])
    return rounds, errors


def verify(root: Path) -> tuple[list[str], dict]:
    """四条负样本验证。返回 ``(findings, summary)``。

    ``summary`` 含读到的关键事实（供 markdown 渲染复用），避免重复读盘。
    """
    out_dir = Path(root) / C.REVIEW_OUTPUT_DIR
    config_path = out_dir / C.REVIEW_CONFIG_FILENAME
    config = _load_json(config_path)
    rounds, errors = _read_rounds(root)

    findings: list[str] = list(errors)

    # 2. 证据缺件（缺失 / 不可解析 / 合法 JSON 但不是对象）
    if not isinstance(config, dict):
        findings.append(
            f"证据缺件：{C.REVIEW_OUTPUT_DIR}/{C.REVIEW_CONFIG_FILENAME} "
            "缺失、不可解析或不是 JSON 对象"
        )
    if not rounds:
        findings.append("证据缺件：没有任何 round manifest（loop 未产出证据）")

    config_digest = (
        roles_mod.config_hash(config) if isinstance(config, dict) else None
    )

    # 1. 篡改 manifest
    for doc in rounds:
        recorded = doc.get("config_hash")
        if config_digest is not None and recorded != config_digest:
            findings.append(
                f"篡改 manifest：round {doc.get('round')} 的 config_hash 与 "
                f"{C.REVIEW_CONFIG_FILENAME} 不符"
            )

    # 3. 两路同一 actor + findings 类型校验
    all_findings: list[dict] = []
    for doc in rounds:
        actors = doc.get("actors")
        if not isinstance(actors, list) or any(
            not isinstance(actor, dict) for actor in actors
        ):
            findings.append(
                f"manifest actors 类型非法：round {doc.get('round')}（应为对象数组）"
            )
            actors = []
        by_role = {
            str(actor.get("role")): actor
            for actor in actors
            if isinstance(actor, dict)
        }
        missing_roles = [
            role for role in ("reviewerA", "reviewerB") if role not in by_role
        ]
        if missing_roles:
            findings.append(
                f"证据缺件：round {doc.get('round')} 缺少 "
                f"{', '.join(missing_roles)} 的 actor"
            )
        else:
            run_ids = [by_role[role].get("run_id") for role in ("reviewerA", "reviewerB")]
            if not all(isinstance(value, str) and value.strip() for value in run_ids):
                findings.append(
                    f"证据缺件：round {doc.get('round')} 的 reviewerA/reviewerB 缺少 run_id"
                )
            elif run_ids[0] == run_ids[1]:
                findings.append(
                    f"两路同一 actor：round {doc.get('round')} 的 reviewerA 与 reviewerB "
                    f"run_id 相同（{run_ids[0]}）"
                )
        for field in ("fixer", "judge"):
            value = doc.get(field)
            if value is not None and not isinstance(value, dict):
                findings.append(
                    f"manifest {field} 类型非法：round {doc.get('round')}（应为对象或 null）"
                )
        round_findings = doc.get("findings")
        if not isinstance(round_findings, list) or any(
            not isinstance(finding, dict) for finding in round_findings
        ):
            findings.append(
                f"manifest findings 类型非法：round {doc.get('round')}（应为对象数组）"
            )
            continue
        all_findings.extend(round_findings)

    # 4. 正控漏报
    positive = None
    if isinstance(config, dict):
        pc = config.get("positive_control") or {}
        if isinstance(pc, dict) and pc.get("where"):
            positive = str(pc["where"])
    final_verdict = None
    for doc in rounds:
        # summary.json 若在，取它的 final_verdict；否则取最后一轮的 verdict。
        final_verdict = doc.get("verdict")
    summary_path = out_dir / "summary.json"
    summary_doc = _load_json(summary_path)
    if isinstance(summary_doc, dict) and summary_doc.get("final_verdict"):
        final_verdict = summary_doc["final_verdict"]
    if positive:
        seen = any(str(f.get("where")) == positive for f in all_findings)
        if final_verdict == "PASS" and not seen:
            findings.append(f"正控漏报：positive_control.where={positive} 未在任何一轮被报出")

    summary = {
        "config": config,
        "config_digest": config_digest,
        "rounds": rounds,
        "final_verdict": final_verdict,
        # 两路都回落时 orchestrator 在 summary.json 里写「本轮为同源双审」；
        # Markdown 报告也要显示它，不能只留在 JSON 里。
        "degraded_note": (
            summary_doc.get("degraded_note") if isinstance(summary_doc, dict) else None
        ),
    }
    return findings, summary


def _render_markdown(summary: dict) -> str:
    rounds = summary["rounds"]
    config = summary["config"]
    if not isinstance(config, dict):
        # verify() 已把非对象 config 记为证据缺件；渲染仍要受控，不能 .get 崩溃。
        config = {}
    lines: list[str] = ["# review loop 报告", ""]
    roles = config.get("roles")
    if not isinstance(roles, dict):
        roles = {}
    lines.append("## 配置")
    for name in ("reviewerA", "reviewerB", "fixer", "judge"):
        role = roles.get(name) or {}
        degraded = "（auth 未解析）" if not role.get("auth_resolved") else ""
        lines.append(
            f"- **{name}**：adapter={role.get('adapter')} model={role.get('model')} "
            f"base_url={role.get('base_url')}{degraded}"
        )
    lines.append(f"- pass_rule={config.get('pass_rule')}")
    lines.append(f"- stall_rounds={config.get('stall_rounds')}")
    lines.append(f"- budget={config.get('budget')}")
    lines.append(f"- config_hash={summary.get('config_digest')}")
    lines.append("")

    lines.append("## 各轮")
    for doc in rounds:
        actor_items = doc.get("actors")
        if not isinstance(actor_items, list):
            actor_items = []
        actors = ", ".join(
            f"{a.get('role')}/{a.get('adapter')}/{a.get('model')}"
            + (f"（degraded_from {a.get('degraded_from')}）" if a.get("degraded_from") else "")
            for a in actor_items
            if isinstance(a, dict)
        )
        lines.append(f"### round {doc.get('round')} — verdict={doc.get('verdict')}")
        lines.append(f"- actors：{actors}")
        lines.append(f"- cost_usd={doc.get('cost_usd')}")
        if doc.get("note"):
            lines.append(f"- note：{doc.get('note')}")
        finding_items = doc.get("findings")
        if not isinstance(finding_items, list):
            finding_items = []
        for f in finding_items:
            if not isinstance(f, dict):
                continue
            lines.append(
                f"- [{f.get('severity')}] {f.get('where')} — {f.get('what')}"
            )
        fixer = doc.get("fixer")
        if isinstance(fixer, dict) and fixer.get("error"):
            lines.append(f"- fixer 错误：{fixer.get('error')}")
        judge = doc.get("judge")
        if isinstance(judge, dict):
            lines.append(f"- judge：{judge.get('verdict')}")
            if judge.get("error"):
                lines.append(f"- judge 错误：{judge.get('error')}")
        lines.append("")
    lines.append(f"## 最终判定：{summary.get('final_verdict')}")
    if summary.get("degraded_note"):
        lines.append(f"- degraded_note：{summary['degraded_note']}")
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    findings, summary = verify(root)

    markdown = _render_markdown(summary)
    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(f"review report：已写 {args.out}")
    else:
        sys.stdout.write(markdown)

    if findings:
        print(f"review report：验证未通过（{len(findings)} 项）：", file=sys.stderr)
        for index, finding in enumerate(findings, 1):
            print(f"  {index}. {finding}", file=sys.stderr)
        return C.EXIT_FAIL
    print("review report：验证通过 ✓", file=sys.stderr)
    return C.EXIT_PASS
