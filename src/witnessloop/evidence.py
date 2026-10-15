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

#: 空白字符的**一份**实现（口径与正则引擎的 `\s` 逐字一致）——见 `_is_tail_phrase`。
_WHITESPACE_RE = re.compile(r"\s")
#: 缺件诊断（D4）：与「缺 `## User Confirmation`」**同形**的通用文案 + 一档附加提示。
#: ⚠️ 提示里的字样是 **`Open Question`（单数）**——即 `_missing_open_questions_message`
#: 的实际**筛选口径**（`spec.md` 的 D4 Requirement 也写的单数）。写成复数会与判据错位：
#: 一个含 `Open Question` 而不含 `Open Questions` 的标题会被列出，而文案却声称它含的是后者。
_OPEN_QUESTIONS_MISSING = f"缺少 `## {OPEN_QUESTIONS_TITLE}` 小节"
_OPEN_QUESTIONS_HINT = (
    "检测到含 `Open Question` 字样的标题：{titles}"
    "——若其中之一就是你的 Open Questions 小节，请把标题改成逐字"
)

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


def _fence_run(line: str) -> tuple[str, int] | None:
    """该行是不是代码围栏标记 ⇒ `(字符, 连续个数)`；不是则 `None`。

    判定按 spec **写死**：去首尾空白后以 **≥3 个**连续的 `` ` `` 或 `~` 开头，info string 不限。
    ⚠️ 刻意**不**采用 CommonMark 的「最多 3 空格缩进」上限——一条 4 空格缩进的 `` ``` ``
    **同样**开围栏（收窄会与 spec 不符；方向 fail-closed）。
    """
    stripped = line.strip()
    for char in ("`", "~"):
        if stripped.startswith(char * 3):
            return char, len(stripped) - len(stripped.lstrip(char))
    return None


def _sections(text: str) -> dict[str, str]:
    """按 `## <标题>` 切小节 → {标题: 正文}（正文不含标题行）。

    **代码围栏内的行完全不参与切分**（change confirm-gate-fail-closed / D9）：
    既不创建小节，**也不进任何小节的正文**——即使围栏开在某个已有小节的**内部**。
    ⇒ 报告里**引用**一段含 `## User Confirmation` + `- **Q1**: …` 的示例不再被当成真确认
    （实测：跳围栏前 0 条、之后 2 条）。这是本函数**唯一**的新语义：签名、`setdefault`
    的合并语义、`^##\\s+(.*?)\\s*$` 的匹配一律不变（D6）。

    围栏判定见 `_fence_run`；**结束** = 同字符、**不短于**开始标记、**其后只剩空白**；
    **未闭合** ⇒ 从开始标记到文件末尾全算围栏内。
    """
    out: dict[str, list[str]] = {}
    current: str | None = None
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        marker = _fence_run(line)
        if fence is not None:
            char, length = fence
            if marker and marker[0] == char and marker[1] >= length and not stripped.strip(char):
                fence = None
            continue
        if marker:
            fence = marker
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            current = heading.group(1).strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return {title: "\n".join(lines) for title, lines in out.items()}


def _strip_trailing_qualifiers(title: str) -> str:
    """反复剥掉**尾部的括号限定语**（D2 的 (b) 前半）。

    一层 = 一对**配对**的括号（全角或半角）**紧贴末尾**、且其**内容不含任何括号**
    （⇒ 不接受嵌套）；**空括号也算**。⇒ 展开成一遍**反向**扫描：
    可剥的开括号必然是「末字符之外**最靠后**的那个括号」——否则它与闭括号之间就夹着括号。
    游标只向左走、每层的工作量正比于被剥掉的那一段 ⇒ **整体线性**。
    （若每层都从头 `search` 一遍，长串会退化成 O(n²)：实测 `（a）` × 20 000 ⇒ 19.3 s。）
    """
    end = len(title)
    while end and title[end - 1] in "）)":
        index = end - 2
        while index >= 0 and title[index] not in "（）()":
            index -= 1
        if index < 0 or title[index] not in "（(":
            break  # 没有配对的开括号（或它其实是闭括号）⇒ 不剥
        end = index
        while end and title[end - 1].isspace():
            end -= 1
    return title[:end]


def _is_tail_phrase(remaining: str) -> bool:
    """`Open Questions` 是不是 `remaining` 的**结尾短语**（D2 的 (b)）。

    spec 里的**规范形态**是 `^(?:\\S+[- ])*Open Questions$`（`spec.md:38-39`）。本函数与它
    **逐输入等价**（由 `tests/test_evidence.py::test_candidate_judgement_matches_the_spec_regex`
    拿那条正则当 oracle 核对），但**一遍扫描、不回溯**——那条正则不能直接用：`\\S+` 与 `[- ]`
    的**字符集相交**（`-` 既是词内合法字符、又是分隔符）⇒ 每个连字符都给出一条新的切分路径
    ⇒ **2^(连字符数)** 条回溯路径（实测：45 字标题 0.34 s、53 字 6.5 s）。候选判定对
    **每个** H2 标题都跑，且与 Open Questions 无关的标题同样触发 ⇒ `check`（CI）与 `guard`
    （本地、写代码路径前）共用的这条路径会被一份报告**挂住**（同 `guard-crash-exit` 的类别）。

    **等价形式的来历**：把 `^(?:\\S+[- ])*$` 的语言展开（词 = 非空白串，分隔符 ∈ {`-`, 空格}），
    前缀 P 要么为空，要么满足「`P[0]` 非空白；`P[-1]` ∈ {`-`, 空格}；`P[-2]` 非空白
    （末位分隔符前**必须有一个词**——`\\S+` 非空 ⇒ 单独一个 `-` 不是合法前缀）；
    P 里的空白**只能是半角空格**、且**没有两个相邻空白**」。
    空白口径跟**正则引擎的 `\\s`** 走（`_WHITESPACE_RE`）：
    `str.isspace()` 与 `\\s` **并不完全一致**（如 `\\x1c`），而这个判定的规范是正则。
    """
    if not remaining.endswith(OPEN_QUESTIONS_TITLE):
        return False
    prefix = remaining[: -len(OPEN_QUESTIONS_TITLE)]
    if not prefix:
        return True
    # 末位必须是分隔符，且它**前面必须有一个词**（`\S+` 非空 ⇒ 单独一个 `-` 不算）。
    if prefix[-1] not in "- ":
        return False
    if len(prefix) < 2 or _WHITESPACE_RE.match(prefix[-2]):
        return False
    if _WHITESPACE_RE.match(prefix[0]):
        return False
    if "  " in prefix:
        return False
    return all(char == " " for char in _WHITESPACE_RE.findall(prefix))


def _is_open_questions_title(title: str) -> bool:
    """标题（已去首尾空白）是不是候选 Open Questions 小节（D2）。

    候选 ⇔ **(a) 逐字**等于 `Open Questions`，**或 (b) 反复剥掉尾部的括号限定语后**，
    `Open Questions` 是其**结尾短语**——即其前只允许空格 / 连字符分隔的词。

    (b) 是**启发式**：它收敛已知的真实写法，不穷尽所有写法。两侧都**写死**：
    - 落空（`Open  Questions` 双空格 / `Open Questions：` 尾冒号 / 大小写不符 / 嵌套括号
      / 标题行带反引号）⇒ 非候选 ⇒ **红**（作者写了个认不出的标题）；
    - 多收（`Non-Open Questions` / `未解决 Open Questions`）⇒ 候选 ⇒ 多要一条确认
      （前缀词比直觉宽，方向仍是 fail-closed）。

    括号自身的口径（M-E）：全角半角都剥、**连续多个尾括号全部剥**、**空括号同样剥**、
    内容**含嵌套括号则不剥**（`Open Questions（a（b）c）` ⇒ 非候选）。
    """
    if title == OPEN_QUESTIONS_TITLE:
        return True
    return _is_tail_phrase(_strip_trailing_qualifiers(title))


def _open_question_sections(sections: dict[str, str]) -> list[str]:
    """候选小节标题——**排序后**返回。

    候选来自 `dict` 的 key ⇒ 不排序就会依赖插入序（同一输入的两次调用可能给出不同顺序）。
    """
    return sorted(title for title in sections if _is_open_questions_title(title))


def _missing_open_questions_message(sections: dict[str, str]) -> str:
    """候选为空时的诊断（D4）：报告里有含该字样的标题就**列出来**。

    列出「**全部、去重、排序**」的含 `Open Question` 字样（大小写敏感）的二级标题，
    使修法（改名）一步可达——而不是只给一句「缺少小节」让作者去猜。

    ⚠️ 提示只陈述**观察到的事实**（「你的报告里有这些含该字样的标题」），
    **不**断言其中某个「就是你的 Open Questions 小节」：含该字样的标题里既有真正的
    近义标题（`## Open Questions 汇总`——改名即可），也有**语义无关**的
    （`## 逐条对抗（… / Open Questions）`）。列全部而不只列最像的那个，同样是不替作者猜。
    """
    near = sorted(title for title in sections if "Open Question" in title)
    if not near:
        return _OPEN_QUESTIONS_MISSING
    listed = "、".join(f"`{title}`" for title in near)
    return f"{_OPEN_QUESTIONS_MISSING}；" + _OPEN_QUESTIONS_HINT.format(titles=listed)


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

    `## Open Questions` 那条判据**与 `## User Confirmation` 对称的 fail-closed**
    （change confirm-gate-fail-closed / D1）：**候选小节一个都不存在 ⇒ 红**，
    **内容 = 全部候选小节正文的并集**（D3——不许只取第一个、也不许只取逐字那个）。
    ⇒ 「改个标题」绕不过去，且「留个空壳、把真问题搬到旁边的近义标题下」也绕不过去。

    **已知宽松面**（属「防漂移不防伪造」的既定边界，非缺陷）：候选小节**存在但为空**时
    **无 Qn 可确认** ⇒ 该条判据**空真**通过；占位启发式是短答复子串匹配
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

    # ① 存在性必填（与上一条**同一种** finding）——`or ""` 那手防御性写法正是缺陷本体：
    #    它把「小节缺失」与「小节存在但为空」合并成同一个状态，而那个状态被当成「无 Q 可确认」静默通过。
    open_sections = _open_question_sections(sections)
    if open_sections:
        # ② 内容 = **全部候选小节的并集**（同名小节已由 `_sections` 的 `setdefault` 合并——
        #    那条语义本 change 不改，方向 fail-closed）。「只取逐字那个」会让要求变少。
        body = "\n".join(sections[title] for title in open_sections)
        confirmations = _confirmations(user_confirmation or "")
        for qnum in sorted(_open_question_indexes(body)):
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
    else:
        findings.append(Finding(report_path, _missing_open_questions_message(sections)))
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
    - `verify_body=True`（`grill`）：再校验报告**正文**完备性（grill 专有判据，见 `grill_evidence_findings`），
      且对同 stage 的**每一份** manifest 各跑一次（change confirm-gate-fail-closed / D8）。

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

    if not verify_body:
        _, doc = matching[0]
        report = contract.resolve_report_path(change_dir, doc.get("report_path"))
        if report is None or not report.is_file():
            return [
                Finding(label, f"stage={stage} 的 manifest 的 report_path 解析不到报告")
            ]
        return []

    # D8：正文判据对**每一份** `stage=<stage>` 的 manifest 各跑一次。只校验**排序第一份**
    # （原 `matching[0]`）时，放一份排序在前、绑着合规短报告的**诱饵** manifest 就能让
    # 整段正文判据失效（实测：诱饵不在 4 条、诱饵在场 0 条）——那是**作者**自己就能造的自伤面。
    # `label` 仍带**那份 manifest 绑定的相对路径**，以便定位是哪一份不合格；一份读不出
    # 只影响它自己（报「无法核验」），不改变其余份的判定。
    findings: list[Finding] = []
    for _, doc in matching:
        report = contract.resolve_report_path(change_dir, doc.get("report_path"))
        if report is None or not report.is_file():
            findings.append(
                Finding(label, f"stage={stage} 的 manifest 的 report_path 解析不到报告")
            )
            continue
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
            findings.append(
                Finding(
                    f"{label}/{rel_report}",
                    f"报告{why}（{type(exc).__name__}）：无法核验该 stage 的证据",
                )
            )
            continue
        findings.extend(grill_evidence_findings(text, report_path=f"{label}/{rel_report}"))
    return findings


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
