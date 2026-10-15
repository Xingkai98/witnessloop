"""change `confirm-gate-fail-closed` 的**文档计数守卫**（机械对账，不靠人每轮去数）。

**为什么有这条测试**：该 change 的文档里有三类**互相引用**的计数——
`design.md §8.1` 的**面清单行数**、`spec.md` 的**边界声明条数**、`design.md §8` 的 **Q4 类别数**
（外加 §5.3 否定用例的 `X` 上限）。它们会在每一轮对抗复审的整合里各动一次，
而「**文档声称的数字与实际结构不符**」在该 change 里**被独立审阅反复打回**
（R2-① / R3 / R4-② / R5-① / R6-② / R7-② / R8-③…，全是同一类：下游按字面读会得到错误的规模）。
⇒ 把这件事从「靠人记得同步」变成「**对不上就红**」。

**扫什么**：**只扫本 change 目录**（`openspec/changes/<id>/`，归档后自动落到 `archive/`）——
**不**扫别处的文档，所以**不会误伤**历史记述里的旧数字（例如别的 change 或本文件之外
那些「当时是 N 条」的记述）。四份文档里**当前时态**的计数断言**都**要对上；
**允许**历史记述里出现旧数字（在**同一行**里带 `当时` / `R<n>` / `已改` 之类的限定词即可绕过）。

**口径与 `design.md §8.1` 的自查段逐字一致**（那边写的 `grep` 命令与这里的正则相同）。

--------------------------------------------------------------------
**⚠️ 设计天花板（R7 §1.6 要求写清 —— 别把它的能力说过头）**

**它保证**：在本 change 的**四份文档内**，下列**写死模式**彼此一致 ——
① 面清单**行数** ↔ §8.1 自查行的三个数（断言行**恰好一条**）；
② 面行 id **集合** ↔ §8.1 自查段的**逐条枚举**（删任意一行、含**末位**，都红 —— R7-①）；
③ 边界声明**条数** ↔ design/proposal 的**当前时态**断言（历史记述按 `HISTORY_MARKERS` 豁免）；
④ 面行的 `Q4-N` / `声明 N` **落点存在**；
⑤ Q4 类别数 ↔ `**N类**` / `**N类全部**` / `**N类各自**` 三处措辞；
⑥ `X1–Xn` **连续**且三处上限断言一致；
⑦ §8.1 / §5.3 里**形似表行 / 用例行但不合口径**的写法（半角或**全角**竖线、列表 `-`、引用 `>`）
与 **Q4 缩进不是 4 空格**的编号项 ⇒ **报错**（不是忽略）；
⑧ 「严格 / 宽松」口径的**恒等式**（`宽松 = 严格 − B 行数 + 指纹表行数`）；
⑨ change 目录**找不到 ⇒ 红**（**不 skip** —— 静默绿比没守卫更坏）。

**它不保证**（写在这里，免得下一轮把它当 bug 或当万灵药）：

- **「该在的东西还在」**——它测**一致性**，不测**完备性**：把「一个面 + 它的声明 + 全部计数」
  **一起**删掉（完全自洽地改小）⇒ **照样绿**；**反过来，表 + 枚举 + 计数一起加一个面**（自洽地**加**）
  ⇒ **同样绿**（R8 实测两侧）。⇒ 它回答不了「16 个面是不是真的覆盖了所有已知面」，
  那仍**只能靠人逐条核 Q4 / 声明**。
- **四个模式之外的任何计数**：`tasks.md` 的 `passed` 数、§7.20 指纹表的行数 —— 结构变了它们不会自动报。
- **公式的「文本」**：`test_loose_caliber_identity` 钉的是**两个正则之间的算术关系**，
  **不读** §8.1 那段公式的散文（把公式里的 `+` 改成 `−` 它**不会**红，R8 实测）⇒
  公式文本的正确性**靠人**，别指望本文件。
- **`design.md` 的其余部分**：行内自相矛盾（例如自查行说「B 7 条」却又列着 `| **B8** |`）
  只有**逐条枚举**那一条断言能兜住，别的地方**不兜**。
- **别的 change / 别的仓**：按设计**只扫本 change 目录**（扩到别处会把「当时是 N 条」的
  历史记述拉成假阳性）。代价是**本仓其它 change 的同款计数完全不受保护**。
- **中文数字措辞 ≠ 语义**：`CN_NUM` 只到 20（超出会提示扩表）；它钉的是三个**字面串**。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = "confirm-gate-fail-closed"

#: §8.1 面清单里的**面行**：`| G1 | …` / `| R3 | …` / `| **B7** | …`。
#: ⚠️ 口径必须写这么严——宽松的 `^\| (G|R)[0-9] ` 会把 §7.20 指纹表的 `| R1 对抗 |` 也算进来。
FACE_ROW_RE = re.compile(r"^\| (G\d+|R\d+|\*\*B\d+\*\*) \|", re.M)
#: 边界声明：`## 边界声明` 段的编号项。
DECL_RE = re.compile(r"^(\d+)\. \*\*", re.M)
#: Q4 的类别：Q4 列表项下的**缩进四级**编号项。
CLASS_RE = re.compile(r"^    (\d+)\. \*\*", re.M)
#: §5.3 的否定用例。
NEG_CASE_RE = re.compile(r"^- \*\*X(\d+)", re.M)
#: 中文数字（只到「二十」，够用）。
CN_NUM = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八",
    9: "九", 10: "十", 11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五",
    16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十",
}
#: 历史记述的**豁免词**：同一行里出现任一个，就允许那一行出现旧数字。
HISTORY_MARKERS = (
    "当时", "已改", "历史", "原稿", "初版",
    # ⚠️ 两种**审阅行**写法都要认：`R5 的 N18`（带空格）与 `R8-③`（带连字符）。
    #    **不能**只写 `R{i}`（不带限定）——正文里的 `R4；` / `R5（` 会被误判成历史记述（R8 实测踩到）。
    *(f"R{i} " for i in range(1, 10)),
    *(f"R{i}-" for i in range(1, 10)),
)


def _change_dir() -> Path:
    """定位 change 目录：active 用原名；归档后是 `<date>-<id>` ⇒ 用 `*<id>` 兜住。

    （本仓归档约定见 `contract.py`：`changes/<id>/ → changes/archive/<date>-<id>/`。）

    ⚠️ **找不到就 `fail`，不是 `skip`**（R6 的 N23）：本守卫的价值在于「文档与结构对不上就红」，
    而 `skip` 在 CI 上表现为 `N skipped` + `rc=0`（**静默绿**）——**一个能静默消失的守卫
    比没有守卫更坏**（它会让人以为这类问题已经被守住了）。
    ⇒ 唯一**正当**的失败情形是「这个 change 目录真的不在本仓」，那也应当是**响亮的红**：
    要么是它被删了（不该发生），要么是本测试需要随 change 一起搬迁/删除。
    """
    active = REPO_ROOT / "openspec" / "changes" / CHANGE_ID
    if active.is_dir():
        return active
    for candidate in sorted((REPO_ROOT / "openspec" / "changes").rglob(f"*{CHANGE_ID}")):
        if candidate.is_dir():
            return candidate
    pytest.fail(
        f"在本仓找不到 change 目录 `{CHANGE_ID}`（active 或 archive 都没有）。\n"
        "本守卫**不 skip**——静默跳过等于没有守卫。若该 change 已被删除或已不再需要这份对账，"
        "请**连同本测试文件一起**处理（删除或搬迁），别让它悄悄变绿。"
    )


@pytest.fixture(scope="module")
def docs() -> dict[str, str]:
    # ⚠️ `_change_dir()` 找不到时**直接 fail**（不是 skip）——见它的 docstring。
    directory = _change_dir()
    return {
        rel: (directory / rel).read_text(encoding="utf-8")
        for rel in ("design.md", "proposal.md", "tasks.md", "specs/open-questions-gate/spec.md")
    }


def _face_counts(design: str) -> tuple[int, int, int]:
    """(A 块面数, B 块面数, 总数) —— 按**行**数，不按声明里的数。"""
    a = len([m for m in FACE_ROW_RE.finditer(design) if m.group(1).startswith("G")])
    b = len([m for m in FACE_ROW_RE.finditer(design) if not m.group(1).startswith("G")])
    return a, b, a + b


def _declarations(spec: str) -> list[int]:
    """`## 边界声明` 段内的编号（按出现顺序）。"""
    section = spec.split("## 边界声明", 1)
    assert len(section) == 2, "spec.md 里找不到 `## 边界声明` 段"
    return [int(n) for n in DECL_RE.findall(section[1])]


def _q4_classes(design: str) -> list[int]:
    """Q4 列表项之下的类别编号。"""
    _, _, tail = design.partition("- **Q4**:")
    assert tail, "design.md 里找不到 `- **Q4**:` 这条停轮项"
    # 到下一个二级标题为止（Q4 是 §8 唯一一条）
    tail = tail.split("\n## ", 1)[0]
    return [int(n) for n in CLASS_RE.findall(tail)]


def _neg_cases(design: str) -> list[int]:
    _, _, tail = design.partition("### 5.3 否定用例")
    assert tail, "design.md 里找不到 `### 5.3 否定用例`"
    tail = tail.split("\n### ", 1)[0]
    return [int(n) for n in NEG_CASE_RE.findall(tail)]


def _assert_contiguous(numbers: list[int], what: str) -> None:
    assert numbers, f"{what}：一个都没解析到（正则或文档结构变了）"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"{what}：编号必须从 1 起连续，实测 {numbers}"
    )


def _current_claims(text: str, pattern: str) -> list[str]:
    """抓出**当前时态**的断言行：命中 `pattern` 且**不含**历史豁免词的行。"""
    return [
        line for line in text.splitlines()
        if re.search(pattern, line) and not any(m in line for m in HISTORY_MARKERS)
    ]


def test_face_table_counts_match_the_self_check(docs):
    """§8.1 的面清单行数 ↔ 它自己写的自查数（A/B/总）。"""
    design = docs["design.md"]
    a, b, total = _face_counts(design)
    claims = _current_claims(design, r"面 = A \d+ 条 \+ B \d+ 条 = \d+ 条")
    assert len(claims) == 1, f"§8.1 的自查行应恰好 1 条，实测 {len(claims)}：{claims}"
    # 只取断言句本身的三个数（该行后面还有一句解释口径的括注，里面也有数字）
    got = [int(n) for n in re.findall(r"\d+", claims[0])][:3]
    assert got == [a, b, total], (
        f"§8.1 自查写的是 A={got[0]} / B={got[1]} / 总={got[2]}，"
        f"而面清单实际是 A={a} / B={b} / 总={total} —— 别手改数字，去核表"
    )


def test_declaration_count_matches_its_claims(docs):
    """`spec.md` 的边界声明条数 ↔ 三份文档里对它当前值的断言。"""
    decls = _declarations(docs["specs/open-questions-gate/spec.md"])
    _assert_contiguous(decls, "边界声明编号")
    n = len(decls)

    design_claims = _current_claims(docs["design.md"], r"spec 声明总数 = \*\*\d+\*\*")
    assert len(design_claims) == 1, f"`spec 声明总数` 应恰好 1 条，实测 {design_claims}"
    assert f"spec 声明总数 = **{n}**" in design_claims[0], (
        f"§8.1 写 `{design_claims[0].strip()}`，而声明实际 **{n}** 条"
    )

    # design §6 与 proposal 里各有一处「N 条边界声明」的当前时态断言
    assert _current_claims(docs["design.md"], r"与 \*\*\d+ 条\*\*边界声明"), (
        "design.md 里 `与 **N 条**边界声明` 那句不见了"
    )
    design_n = [int(x) for x in re.findall(r"与 \*\*(\d+) 条\*\*边界声明", docs["design.md"])]
    assert design_n and all(x == n for x in design_n), (
        f"design.md 的「N 条边界声明」实测 {design_n}，应为 {n}"
    )

    # ⚠️ N25：这三处原先走 raw `findall`，**合法的历史记述**会被假红 ⇒ 一并走 `_current_claims`
    for rel, pattern, what in (
        ("design.md", r"与 \*\*\d+ 条\*\*边界声明", "design.md 的「与 N 条边界声明」"),
        ("proposal.md", r"\*\*\d+ 条\*\*边界声明", "proposal.md 的「N 条边界声明」"),
    ):
        got = [int(x) for x in re.findall(r"(\d+) 条\*\*边界声明", "\n".join(
            _current_claims(docs[rel], pattern)))]
        assert got, f"{what}：当前时态的断言一条都没解析到（别把它删了，也别只留历史记述）"
        assert all(x == n for x in got), f"{what} 实测 {got}，应为 {n}"


def test_face_count_matches_proposal_claim(docs):
    """`proposal.md` 里对 **面数** 的当前时态断言。"""
    _, _, total = _face_counts(docs["design.md"])
    claims = [int(x) for x in re.findall(
        r"\*\*(\d+) 面\*\*清单",
        "\n".join(_current_claims(docs["proposal.md"], r"\*\*\d+ 面\*\*清单")),
    )]
    assert claims, "proposal.md 里当前时态的 `**N 面**清单` 那句不见了"
    assert all(x == total for x in claims), (
        f"proposal.md 写 `**{claims} 面**清单`，而 §8.1 实际 {total} 个面"
    )


def test_face_declarations_and_totals_are_consistent(docs):
    """R8 ③：§8.1 自查段里**「落在 N 条」与「N 面 ≠ M 条声明」**这两行也要对账。

    变异证据（R8 实测）：把 `落在 **13** 条` 改成 `9`、把 `≠` 改成 `=` ⇒ 原先**都是 11 passed**。
    这里按结构算：**面行引用的不同声明号个数**、**面数**、**声明总数**，并断言
    ① 文中那个「落在 N 条」= 实际不同声明号数；② 文中「N 面 ≠ M 条声明」的两个数 =
    实际面数 / 实际声明数，且关系确实是 `≠`。
    """
    design = docs["design.md"]
    decls = _declarations(docs["specs/open-questions-gate/spec.md"])
    _, _, total_faces = _face_counts(design)

    _, _, tail = design.partition("### 8.1")
    tail = tail.split("\n**自查口径**", 1)[0]
    cited: set[int] = set()
    for line in tail.splitlines():
        if FACE_ROW_RE.match(line):
            cited.update(int(x) for x in re.findall(r"声明 \*\*(\d+)\*\*", line))
    assert cited, "§8.1 的面行里一条 `声明 **N**` 都没解析到"

    claims = _current_claims(design, r"\*\*落在 \d+ 条\*\*不同的声明上")
    assert len(claims) == 1, f"「落在 N 条不同的声明上」应恰好 1 条，实测 {claims}"
    got = int(re.search(r"落在 (\d+) 条", claims[0]).group(1))
    assert got == len(cited), (
        f"§8.1 写「落在 {got} 条不同的声明上」，而面行**实际**引用 **{len(cited)}** 条"
        f"（{sorted(cited)}）"
    )

    ineq = _current_claims(design, r"\d+ 个面 ≠ \d+ 条声明")
    assert len(ineq) == 1, f"「N 面 ≠ M 条声明」应恰好 1 条，实测 {ineq}"
    a, b = (int(x) for x in re.findall(r"(\d+) 个面 ≠ (\d+) 条声明", ineq[0])[0])
    assert (a, b) == (total_faces, len(decls)), (
        f"§8.1 写「{a} 个面 ≠ {b} 条声明」，而实际是 **{total_faces} 面 / {len(decls)} 条声明**"
    )
    assert a != b, f"实际面数 {a} 与声明数 {b} 相等 ⇒ 「≠」这个关系句为假"


def test_face_rows_point_at_existing_q4_classes(docs):
    """①（R6-① 缺口 a）面行里的 `Q4-N` 落点必须**存在**。

    变异证据（R6 §5.3a）：把 `| Q4-**8** / 声明 **6** |` 改成 `| Q4-**99** |` ⇒ 原先**绿**。
    """
    design = docs["design.md"]
    classes = set(_q4_classes(design))
    assert classes, "Q4 的类别一条都没解析到"
    _, _, tail = design.partition("### 8.1")
    tail = tail.split("\n**自查口径**", 1)[0]
    cited: set[int] = set()
    for line in tail.splitlines():
        if FACE_ROW_RE.match(line):
            cited.update(int(x) for x in re.findall(r"Q4-\*{0,2}(\d+)", line))
    assert cited, "§8.1 的面行里一条 `Q4-N` 落点都没解析到"
    dangling = sorted(cited - classes)
    assert not dangling, (
        f"§8.1 的面行指向**不存在**的 Q4 类：{dangling}（Q4 实际只有 {sorted(classes)} 类）—— "
        "面清单的指针过期了，去核 `design.md §8` 的 Q4"
    )


def _enumerated_face_ids(design: str) -> set[str]:
    """§8.1 自查段里那串**逐条枚举**（`G1→2、…、B8→6、…`）列出的面 id。

    ⚠️ **按短语切会切错**：`逐条枚举` 在别的小节（§7.15 的整合记录）出现过，且在 §8.1 **自己**的
    开场句「⚠️ **逐条枚举，不凭印象**」里也出现过 ⇒ 定位方式是「**§8.1 的 `**自查口径**` 段**」
    ＋「**带箭头**的 id」（那段里只有逐条枚举带箭头，表格行与自查句都不带）。
    """
    section = design.partition("### 8.1")[2]
    assert section, "design.md 里找不到 `### 8.1`"
    self_check = section.split("**自查口径**", 1)[1]
    assert self_check, "§8.1 里找不到 `**自查口径**` 段"
    return {f"{a}{n}" for a, n in re.findall(r"\b([GRB])(\d+)→", self_check)}


def test_face_rows_match_the_enumeration_line(docs):
    """②（R6-① 缺口 b / R7-①）面行 id 集合 **必须等于** 逐条枚举列出的 id 集合。

    **为什么不是「组内连续」**（R7-① 的必改）：原实现只断言连续 + B 组起点 = 7，
    而 **B8 是末位** ⇒ 删它**不产生跳号**（`[7,8] → [7]` 自己就连续）⇒ 静默绿。
    ⇒ 换成**结构性**断言：面清单（表）与自查段的**逐条枚举**必须**互为子集**。
    删任意一行（含末位）⇒ 枚举里还留着它 ⇒ 集合不等 ⇒ **红**。

    变异证据（都必须红）：删 **B8**（末位）/ 删 **B7** / 删 **R5**（中间位）/ 删 **G8**。
    """
    design = docs["design.md"]
    table_ids = set()
    for m in FACE_ROW_RE.finditer(design):
        raw = m.group(1)
        table_ids.add(raw.strip("*"))
    enum_ids = _enumerated_face_ids(design)
    assert table_ids, "§8.1 的面行一行都没解析到"
    assert enum_ids, "§8.1 的逐条枚举一个 id 都没解析到"
    missing_in_table = sorted(enum_ids - table_ids)
    missing_in_enum = sorted(table_ids - enum_ids)
    assert not missing_in_table, (
        f"§8.1 的**逐条枚举**列了这些面，但**面清单里没有对应的行**：{missing_in_table}\n"
        "⇒ 有一行面被删了（**末位也算**），或枚举与表脱钩了"
    )
    assert not missing_in_enum, (
        f"§8.1 的面清单有这些行，但**逐条枚举没列**：{missing_in_enum}\n"
        "⇒ 加了面却没进枚举（枚举是给下一轮照着核的，必须逐条齐）"
    )


def test_loose_caliber_identity(docs):
    """R7-②：§8.1 旁注讲的「严格 / 宽松」口径关系做成**恒等式**，别再手写那两个数。

    旁注里的数**被订正过三次**（18/四行 → 17/四行 → 19/五行；实测是 20/六行），
    每次都是「同一段落的另一处也变了」。⇒ 文档**不再写死**这两个数（改指本测试），
    而这条测试把那条**公式**钉住：宽松 = 严格 − `**Bxx**` 行数 + §7.20 指纹表行数。
    """
    design = docs["design.md"]
    strict = len(FACE_ROW_RE.findall(design))
    loose = len(re.findall(r"^\| (G|R)[0-9] ", design, re.M))
    b_rows = len(re.findall(r"^\| \*\*B\d+\*\* \|", design, re.M))
    fingerprint_rows = len(re.findall(r"^\| R\d+ (?:对抗|复审) ", design, re.M))
    assert fingerprint_rows, "§7.20 指纹表一行都没解析到"
    assert loose == strict - b_rows + fingerprint_rows, (
        f"宽松口径恒等式不成立：strict={strict} − B行{b_rows} + 指纹表{fingerprint_rows} "
        f"= {strict - b_rows + fingerprint_rows}，而实测 loose={loose}\n"
        "⇒ §8.1 旁注那条公式（或文档结构）变了，去核"
    )


def test_q4_class_count_matches_its_wording(docs):
    """Q4 的类别数 ↔ 它自己的中文数字措辞（`**N类**`）。"""
    design = docs["design.md"]
    classes = _q4_classes(design)
    _assert_contiguous(classes, "Q4 的类别编号")
    n = len(classes)
    word = CN_NUM.get(n)
    assert word, f"Q4 有 {n} 类，中文数字表没覆盖到——请扩 CN_NUM"
    for stub in (f"**{word}类**", f"**{word}类全部**", f"**{word}类各自**"):
        assert stub in design, f"Q4 有 {n} 类，但 design.md 里找不到 `{stub}`"


def test_no_approximate_face_or_case_markup(docs):
    """③（R6-① 缺口 c）**非抽取格式的新增项**不得成为逃生门。

    变异证据（R6 §1.2 B 组）：`|  **B8b**  |`（多空格）与 `* **X16**`（星号 bullet）原先**绿**
    ——它们没被抽取正则命中，于是「加了一项却没进计数」。
    ⇒ 在 §8.1 与 §5.3 两段里，**任何**看起来像面行 / 用例行但**不合口径**的写法都直接报错
    （而不是被忽略）。
    """
    design = docs["design.md"]
    face_section = design.partition("### 8.1")[2].split("\n**自查口径**", 1)[0]
    loose_face = re.compile(r"^\|\s+\S*\*{0,2}[GRB]\d+", re.M)
    bad = [
        line for line in face_section.splitlines()
        if loose_face.match(line) and not FACE_ROW_RE.match(line)
    ]
    assert not bad, (
        "§8.1 里出现了**像面行但不合口径**的写法（抽取正则抓不到它 ⇒ 计数会漏）：\n  "
        + "\n  ".join(bad)
        + "\n⇒ 要么按 `| G8 | …` / `| R1 | …` / `| **B8** | …` 的格式写，要么别放在这一节"
    )

    # ⚠️ N29：③ 原先只认**半角 `|` 开头**的形态 ⇒ 换成行首标记（`-` / `>`）或**全角竖线**就绕过。
    #    放宽成「行首可选标记 + 行内 ≥2 个竖线（半角或全角）」⇒ 表形态一律要合口径。
    # 「像表行」的判据 = **≥2 个竖线（半角或全角）** ＋ **含一个 `G/R/B` + 数字的 token**
    # （表头 `| # | 面 | … |` 与分隔行 `|---|---|` 因此不受影响）。
    pipe = re.compile(r"[|｜]")
    token = re.compile(r"\b[GRB]\d+\b")
    loose_rows = [
        line for line in face_section.splitlines()
        if len(pipe.findall(line)) >= 2 and token.search(line) and not FACE_ROW_RE.match(line)
    ]
    assert not loose_rows, (
        "§8.1 里出现了**像表行但不合口径**的写法（抽取正则抓不到它 ⇒ 计数会漏）：\n  "
        + "\n  ".join(loose_rows)
        + "\n⇒ 表行必须以**行首半角竖线**写（`| G8 | …` / `| **B8** | …`）；"
        "列表 `-` / 引用 `>` / 全角 `｜` 都不算（R7 的 N29）"
    )

    # ⚠️ N29 的另一半：Q4 的类别抽取要求**恰好 4 空格**缩进 ⇒ 2 空格 / 0 缩进多写一类**不被看见**。
    q4_section = design.partition("- **Q4**:")[2].split("\n## ", 1)[0]
    odd_indent = [
        line for line in q4_section.splitlines()
        if re.match(r"^\s*\d+\. \*\*", line) and not CLASS_RE.match(line)
    ]
    assert not odd_indent, (
        "Q4 里出现了**缩进不是 4 空格**的编号项（类别抽取会漏掉它 ⇒ 「N类」措辞与结构脱钩）：\n  "
        + "\n  ".join(odd_indent)
        + "\n⇒ Q4 的类别一律用 **4 空格**缩进（与既有各条对齐）"
    )

    cases_section = design.partition("### 5.3 否定用例")[2].split("\n### ", 1)[0]
    loose_case = re.compile(r"^[-*]\s+\*{0,2}X\d+", re.M)
    bad_cases = [
        line for line in cases_section.splitlines()
        if loose_case.match(line) and not NEG_CASE_RE.match(line)
    ]
    assert not bad_cases, (
        "§5.3 里出现了**像用例行但不合口径**的写法（`X` 用例必须以 `- **X<n>` 开头）：\n  "
        + "\n  ".join(bad_cases)
    )


def test_task_g3_does_not_hardcode_the_class_count(docs):
    """⑤（R6-②）`tasks.md` 的 G3 **不得写死 Q4 的类数**——那个位置已过期两次。

    R4-② 与 R6-② 是**同一条、同一个位置**的两次过期（先「五类」后「七类」）。
    ⇒ 不是「改准这一次」，而是**禁止硬编码**：G3 里出现 `N类` 就报错。
    """
    tasks = docs["tasks.md"]
    # ⚠️ N30：原实现用 `next(...)` 只取**第一行**且**不走豁免** ⇒
    #    ① 在当前 G3 行**之前**插一行合法的历史记述 ⇒ **假阳性**；
    #    ② 把类数写在**第二行** `G3 … 停轮` 上 ⇒ **假阴性**（⑤ 形同虚设）。
    #    ⇒ 改成**扫全部** G3 行，并复用 `_current_claims` 的豁免口径（与 N25 一致）。
    lines = _current_claims(tasks, r"G3.*停轮")
    assert lines, "tasks.md 里找不到当前时态的 G3 停轮任务（别把它删了）"
    for line in lines:
        assert not re.search(r"[一二三四五六七八九十\d]+类", line), (
            f"G3 里**硬编码了 Q4 的类数**：{line.strip()}\n"
            "⇒ 那个位置已经过期两次（R4-② / R6-②）。请改成「各类残留全列」或不写数字。"
        )


def test_negative_case_prefix_is_contiguous_and_claimed(docs):
    """§5.3 的 `X` 用例编号连续，且上限与「X1–XN」的断言一致。"""
    design = docs["design.md"]
    cases = _neg_cases(design)
    _assert_contiguous(cases, "§5.3 的否定用例编号")
    n = len(cases)
    assert f"X1–X{n}" in design, (
        f"§5.3 有 {n} 条用例，但文档里找不到 `X1–X{n}` 这个上限断言"
    )
    # tasks 的抬头也声明了上限
    assert re.search(rf"一律 `X1…X{n}`", docs["tasks.md"]), (
        f"tasks.md 的抬头应写 `一律 `X1…X{n}``，实测没找到"
    )
    # proposal 的「否定用例」段也声明了上限（⚠️ 这一处**曾经**在 R5 被漏改，故一并钉）
    assert re.search(rf"`X1–X{n}`", docs["proposal.md"]), (
        f"proposal.md 的否定用例段应写 `X1–X{n}`，实测没找到"
    )


def test_every_face_has_a_declaration_or_is_flagged_non_face(docs):
    """每个面都指向一条**存在**的声明；缺口只在自陈为「非面」的两条上。"""
    design = docs["design.md"]
    decls = set(_declarations(docs["specs/open-questions-gate/spec.md"]))
    _, _, tail = design.partition("### 8.1")
    tail = tail.split("\n**自查口径**", 1)[0]
    cited: set[int] = set()
    for line in tail.splitlines():
        if FACE_ROW_RE.match(line):
            cited.update(int(x) for x in re.findall(r"声明 \*\*(\d+)\*\*", line))
    assert cited, "§8.1 的面行里一条 `声明 **N**` 都没解析到"
    missing = sorted(cited - decls)
    assert not missing, f"§8.1 引用了不存在的声明号：{missing}（spec 里只有 {sorted(decls)}）"
    unused = sorted(decls - cited)
    assert unused == [8, 9], (
        f"未被任何面引用的声明应为 [8, 9]（自陈的两条非面），实测 {unused} —— "
        "新增声明后要把它接进某个面，或更新本测试的非面名单"
    )
