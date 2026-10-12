"""grill 证据完备性判定（change grill-evidence-gate / D1）。

**一个** host-agnostic、**纯函数**的判定，被两处共用：`check`（事后 / CI）与
`guard`（事前 / 本地）。分两份实现必然漂移——本仓已因「两边各写一套」踩过坑
（故 `constants.HASHED_ARTIFACTS` 才共用一张表）。

判据**块级**：`来源:` 允许只出现在 bullet 的**续行**。对抗验证实测——本仓
`dogfood-bootstrap` 的 `来源:` **全在续行**，任何**行级**口径命中都是 **0**。

谓词移植自 asterwynd（`workflow_guard.py` / `check_openspec_artifacts.py`），但
**不照抄**其 `- **决策**：` 前缀匹配：那会把 `- **决策（D1）**：` 判成 0 条
（实测复现）——按「顶层 bullet + 块级 `来源:`」判才对。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from witnessloop import contract
from witnessloop.contract import Finding

CONFIRMED_TITLE = "Confirmed Decisions"
OPEN_QUESTIONS_TITLE = "Open Questions"
USER_CONFIRMATION_TITLE = "User Confirmation"

#: `## Confirmed Decisions` 的硬门槛（`templates/grill.md` 明写）。
MIN_CONFIRMED_DECISIONS = 3

_HEADING_RE = re.compile(r"^##\s+(.*?)\s*$")
_BULLET_RE = re.compile(r"^[-*]\s+")
_SOURCE_RE = re.compile(r"来源\s*[:：]")
_Q_RE = re.compile(r"\bQ(\d+)\b")
_CONF_LINE_RE = re.compile(r"^\s*[-*]\s*\*\*Q(\d+)\*\*\s*[:：]\s*(.*)$")
_ANSWER_RE = re.compile(r"用户答复\s*[:：]\s*(.*?)(?:[;；]?\s*确认时间|$)")

#: 占位确认字面表（照搬 asterwynd `check_openspec_artifacts.py:143-151`）。
_UNCONFIRMED_EXACT = {
    "todo", "tbd", "n/a", "na", "无", "none",
    "待确认", "未确认", "待定", "pending", "待补充", "占位", "未决",
}
_UNCONFIRMED_STRONG = {
    "待主 agent", "待主agent", "待用户", "placeholder", "tobeconfirmed",
    "待拍板", "未拍板",
}
#: 短答复（≤ 这个长度）才查「强占位」；长答复一律视为实质内容。
_UNCONFIRMED_MAX_ANSWER_LEN = 20
_UNCONFIRMED_STRIP = str.maketrans("", "", "。．.；;，,、 \t")


def _sections(text: str) -> dict[str, str]:
    """按 `## <标题>` 切小节 → {标题: 正文}（正文不含标题行）。"""
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            current = heading.group(1).strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return {title: "\n".join(lines) for title, lines in out.items()}


def _blocks(section_text: str) -> list[str]:
    """把小节正文切成**顶层 bullet 块**（bullet 行 + 其续行）。

    顶层 = 第 0 列的 `- `/`* `；缩进的子项（如 `  - ➡️ …`）算**续行**。
    """
    blocks: list[str] = []
    for line in section_text.splitlines():
        if _BULLET_RE.match(line):
            blocks.append(line)
        elif blocks and line.strip():
            blocks[-1] += "\n" + line
    return blocks


def _open_question_indexes(section_text: str) -> set[int]:
    return {int(n) for n in _Q_RE.findall(section_text)}


def _confirmations(section_text: str) -> dict[int, str]:
    """从 `## User Confirmation` 抽出 `{Qn: 答复正文}`。"""
    out: dict[int, str] = {}
    for line in section_text.splitlines():
        match = _CONF_LINE_RE.match(line)
        if not match:
            continue
        answer = _ANSWER_RE.search(match.group(2))
        out[int(match.group(1))] = answer.group(1) if answer else match.group(2)
    return out


def _is_unconfirmed(raw: str) -> bool:
    """答复是不是「写了占位但没真拍板」（启发式同 asterwynd）。"""
    normalized = raw.lower().strip().translate(_UNCONFIRMED_STRIP).strip()
    if not normalized:
        return True
    if normalized in _UNCONFIRMED_EXACT:
        return True
    return len(raw.strip()) <= _UNCONFIRMED_MAX_ANSWER_LEN and any(
        token in normalized for token in _UNCONFIRMED_STRONG
    )


def grill_evidence_findings(
    text: str, *, report_path: str = "reviews/grill-review.md"
) -> list[Finding]:
    """判一份 grill 决策记录是否完备（D1）。空列表 = 合格。

    **已知宽松面**（属「防漂移不防伪造」的既定边界，非缺陷）：`## Open Questions`
    为空时**无 Qn 可确认** ⇒ 该条判据**空真**通过；占位启发式是短答复子串匹配
    （`待确认（稍后）` 这类「短、非精确实例」会被当实质确认）。
    """
    sections = _sections(text)
    findings: list[Finding] = []

    confirmed = sections.get(CONFIRMED_TITLE)
    if confirmed is None:
        findings.append(Finding(report_path, f"缺少 `## {CONFIRMED_TITLE}` 小节"))
    else:
        blocks = _blocks(confirmed)
        if len(blocks) < MIN_CONFIRMED_DECISIONS:
            findings.append(
                Finding(
                    report_path,
                    f"`## {CONFIRMED_TITLE}` 只有 {len(blocks)} 条，"
                    f"少于硬门槛 {MIN_CONFIRMED_DECISIONS} 条",
                )
            )
        for index, block in enumerate(blocks, 1):
            if not _SOURCE_RE.search(block):
                findings.append(
                    Finding(report_path, f"第 {index} 条 Confirmed Decision 缺 `来源:`")
                )

    user_confirmation = sections.get(USER_CONFIRMATION_TITLE)
    if user_confirmation is None:
        findings.append(Finding(report_path, f"缺少 `## {USER_CONFIRMATION_TITLE}` 小节"))

    open_section = sections.get(OPEN_QUESTIONS_TITLE) or ""
    if open_section:
        confirmations = _confirmations(user_confirmation or "")
        for qnum in sorted(_open_question_indexes(open_section)):
            if qnum not in confirmations:
                findings.append(
                    Finding(
                        report_path,
                        f"Open Question Q{qnum} 未经用户确认"
                        f"（`## {USER_CONFIRMATION_TITLE}` 里没有 Q{qnum}）",
                    )
                )
            elif _is_unconfirmed(confirmations[qnum]):
                findings.append(
                    Finding(report_path, f"Open Question Q{qnum} 的确认是占位文本，不算真确认")
                )
    return findings


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # ValueError 涵盖 JSON 语法坏**与**非法 UTF-8 —— 两者必须**同归**（都当「这份 manifest 不可用」），
        # 否则「字节坏放行 / JSON 坏拦」自相矛盾（change guard-crash-exit / D4-2）。
        return None


def stage_manifest_findings_in_change(
    change_dir: Path,
    *,
    stage: str,
    reason: str,
    manifest_glob: str = "reviews/*.manifest.json",
    label: str | None = None,
    verify_body: bool = False,
) -> list[Finding]:
    """要求 change 目录里存在 `stage=<stage>` 的 manifest（+ 其绑定的报告）。

    **一处实现、两种深度**（change building-review-gate / D2）：
    - `verify_body=False`（`building` 等）：只要求「**存在**且报告解析得到」；
    - `verify_body=True`（`grill`）：再校验报告**正文**完备性（grill 专有判据，见 `grill_evidence_findings`）。

    `reason` 由调用方传入（各 stage 不同的那句诊断文案）——**参数 ≠ 第二份实现**：
    判定逻辑仍只有这一处，只是把文案参数化。找不到该 stage 时**点名现有 stage**（拼错可诊断）。
    """
    label = label or change_dir.name
    manifests: list[tuple[Path, dict]] = []
    for path in sorted(change_dir.glob(manifest_glob)):
        doc = _read_json(path)
        if isinstance(doc, dict):
            manifests.append((path, doc))

    matching = [
        (path, doc) for path, doc in manifests if str(doc.get("stage") or "") == stage
    ]
    if not matching:
        stages = sorted({str(doc.get("stage") or "?") for _, doc in manifests})
        return [
            Finding(
                label,
                f"无 stage={stage} 的 manifest（现有 stage："
                f"{', '.join(stages) or '（无）'}）——{reason}",
            )
        ]

    _, doc = matching[0]
    report = contract.resolve_report_path(change_dir, doc.get("report_path"))
    if report is None or not report.is_file():
        return [
            Finding(label, f"stage={stage} 的 manifest 的 report_path 解析不到报告")
        ]
    if not verify_body:
        return []

    try:
        rel_report = report.relative_to(change_dir.resolve()).as_posix()
    except ValueError:  # pragma: no cover - resolve_report_path 已保证在目录内
        rel_report = str(doc.get("report_path") or "report")
    try:
        text = report.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # 甲案（用户 Q1 裁定）：证据内容**读不出** ⇒ 不可核验 ⇒ 不完备（**拦/红**），而不是崩溃出栈。
        # 文案按成因分：解码失败 ≠ 文件读不到（权限等）——后者写「无法解码」会误导。
        why = "无法解码" if isinstance(exc, UnicodeDecodeError) else "无法读取"
        return [
            Finding(
                f"{label}/{rel_report}",
                f"报告{why}（{type(exc).__name__}）：无法核验该 stage 的证据",
            )
        ]
    return grill_evidence_findings(text, report_path=f"{label}/{rel_report}")


def grill_evidence_findings_in_change(
    change_dir: Path,
    *,
    grill_stage: str = "grill",
    manifest_glob: str = "reviews/*.manifest.json",
    label: str | None = None,
) -> list[Finding]:
    """grill 证据 = 存在 `stage=grill_stage` 的 manifest **且**其报告**正文**完备。

    薄封装（`verify_body=True`）——判定本体在 `stage_manifest_findings_in_change`，
    与 `building` 那条**共用同一实现**（分两份实现必然漂移）。
    """
    return stage_manifest_findings_in_change(
        change_dir,
        stage=grill_stage,
        manifest_glob=manifest_glob,
        label=label,
        reason="grill 决策记录必须有对应的审阅证据",
        verify_body=True,
    )
