"""归档感知（change `archive-awareness` / issue #21）：归档 move 使该 change 进本次 diff 的 change 集合。

覆盖 `design.md` 的 A–E 节：契约层（D1/D2/D7/D8）、`check` 侧（D2/D3）、`manifest build`（D4/D5/D8）、
`events`（D6），以及**否定面**（§2.5 / R12）——本 change 的主要风险面。

⚠️ 两条不变量（写用例时最容易踩）：
1. **归档 move 不豁免任何东西**，它只是把那个 change「归属」回本次 diff（§2.5）；
2. **不要在同一个 diff 里 move + 改写被 move 的文件**（git 会报 `R<100`）——那会让 move 降级、
   被搬走的 active 目录以**幽灵 id** 回到集合（R12）。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C
from witnessloop import contract, gitutil, policy as policy_mod

from conftest import commit_all, git
from helpers import (
    VALID_GRILL_REPORT,
    change_dir,
    check,
    commit_content,
    commit_evidence,
    init_wired,
    write_artifact,
)

CHANGES = C.DEFAULT_CHANGES_ROOT
ARCHIVE_REL = f"{CHANGES}/{C.ARCHIVE_DIR_NAME}"
#: 一份**不合规**的 grill 决策记录（只有 2 条 Confirmed Decisions）——uniform 招牌场景要用它。
SHORT_GRILL = (
    "# Grill: add-retry 设计追问\n\n## Reviewer\n- run id: `grill-reviewer-1`\n\n"
    "## Confirmed Decisions\n\n"
    "- **决策（D1）**：甲。\n  理由：因为甲；来源: `grill-reviewer-1`\n\n"
    "- **决策（D2）**：乙。\n  理由：因为乙；来源: `grill-reviewer-1`\n\n"
    "## Open Questions\n\n- **Q1** 选甲还是乙？\n\n"
    "## User Confirmation\n\n- **Q1**: 用户答复：甲；确认时间: 2026-01-01\n"
)

CHANGE = "add-retry"
DAY = "2026-10-14"
ARCHIVED_NAME = f"{DAY}-{CHANGE}"


# --------------------------------------------------------------------------- 小工具

def _targets(root: Path, changes):
    """归档感知的「本次 diff 触及的 change」列表（出厂 policy）。"""
    return contract.change_targets(root, policy_mod.Policy.from_doc({}), changes)


def _move(path: str, old: str, status: str = "R100") -> gitutil.Change:
    return gitutil.Change(status, path, old)


def _archive_it(repo: Path, change: str = CHANGE, name: str = ARCHIVED_NAME) -> str:
    """把 active change 纯改名搬进 archive（R100）；返回归档目录名。"""
    (repo / ARCHIVE_REL).mkdir(parents=True, exist_ok=True)
    git(repo, "mv", f"{CHANGES}/{change}", f"{ARCHIVE_REL}/{name}")
    return name


def _on_main_evidenced(repo: Path, cli, change: str = CHANGE) -> Path:
    """main 上放一个完整、**有证据**的 change（manifest 的 change_id = 源 id），再切到 feature。"""
    init_wired(repo, cli)
    commit_content(repo, change)
    commit_evidence(repo, change)
    git(repo, "checkout", "-q", "-b", "feature")
    return repo


def _build(repo: Path, cli, change: str, report: str, stage: str):
    return cli(
        "manifest", "build", "--root", str(repo), "--change", change, "--stage", stage,
        "--report", report, "--reviewer-run-id", "run-r", "--author-run-id", "run-a",
    )


def _tracked_review_placeholder(repo: Path, change: str = CHANGE) -> None:
    """让 `reviews/` **进 git 树**。

    ⚠️ `write_change` 造的 `reviews/` 是空目录 ⇒ git 不跟踪 ⇒ head 树里没有它；
    而到达判定的判据 2 按**树**判「含全部必需件」（契约门按**工作树**的 `.exists()`）。
    两者只在「必需件是空目录」时分歧 ⇒ 测试里补一个被跟踪的占位文件，让两边一致。
    """
    (change_dir(repo, change) / "reviews" / ".gitkeep").write_text("", encoding="utf-8")


def _archive_dir(repo: Path, name: str = ARCHIVED_NAME) -> Path:
    return repo / ARCHIVE_REL / name


# --------------------------------------------------------------------------- A. 契约层
# ⚠️ 本节的四条纯函数用例（:87 / :101 / :109 / :134 / :471）已由 `tests/test_archive_arrival.py`
# 的 19 条用例**替代并扩展**（同一批函数：`archive_arrivals` / `change_targets` / `changed_change_ids`）。
# 其中 `test_grant_requires_the_target_name_to_recognize_the_source_id` 随名识别守卫的删除
# （用户 2026-10-15 裁定）**整体删除**——「名字认不得源 id」不再是拒绝面。

# --------------------------------------------------------------------------- B. check 侧

def test_archived_change_is_validated_at_the_archived_path(repo: Path, cli):
    """D2：归档 + 改代码 ⇒ 该 change 按**归档路径**走同一套门禁（零 manifest ⇒ 四条缺件全点名）。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)          # base：active change（件齐、零 manifest；已提交）
    # ⚠️ `write_change` 造的 `reviews/` 是**空目录** ⇒ git 不跟踪 ⇒ head 树里没有它，
    # 而到达判定按**树**判「含全部必需件」（契约门按工作树）⇒ 放一个被跟踪的文件让两边一致。
    _tracked_review_placeholder(repo, CHANGE)
    commit_all(repo, "让 reviews/ 进树")
    git(repo, "checkout", "-q", "-b", "feature")

    name = _archive_it(repo)
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "归档 + 改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "没有任何 change 目录" not in err  # D3：不再是「没有 change 目录」
    for needle in (
        "缺少 review manifest",
        "无 stage=grill 的 manifest",
        "无 stage=grill-adversarial 的 manifest",
        "无 stage=building 的 manifest",
    ):
        assert needle in err, err
    assert f"{ARCHIVE_REL}/{name}" in err  # 证据要求在**归档路径**上


def test_implement_then_archive_in_one_pr_passes(repo: Path, cli):
    """§1.6 的正确顺序：① 内容 → ② 在 active 态产证据 → ③ 归档 move 放最后（纯 R100）⇒ 绿。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)          # base：提案态的 active change（已提交）
    git(repo, "checkout", "-q", "-b", "feature")

    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "① 内容（实现）")
    commit_evidence(repo, CHANGE)  # ② 证据（active 态，绑 ① 的 revision）
    name = _archive_it(repo)
    commit_all(repo, "③ 归档（纯 R100，放最后）")

    code, out, err = check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert f"{name}（归档）" in out  # B5：报告里标注归档
    assert "0 个 change 目录" not in out


def test_report_still_says_zero_change_dirs_for_a_docs_only_diff(repo: Path, cli):
    """R6 / I8 的回归护栏：`0 个 change 目录` 这个子串不许消失（既有测试按它断言）。

    它是 R2-2 那条计数钉子（撞车时报 2）的**另一半**：计数口径改了，但这个子串必须原样留着。
    """
    init_wired(repo, cli)
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    write_artifact(repo, "docs/notes.md", "# 笔记\n")
    commit_all(repo, "只改文档")

    code, out, err = check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert "0 个 change 目录" in out


# --------------------------------------------------------------------------- C. manifest build

def test_manifest_build_into_the_archive_and_back(repo: Path, cli):
    """D4：`--change <归档目录名>` 在**归档目录内**走完整过程，`check` 随后认它（往返）。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)          # base：active change（件齐、零 manifest；已提交）
    git(repo, "checkout", "-q", "-b", "feature")

    name = _archive_it(repo)
    commit_all(repo, "纯归档")
    archived = _archive_dir(repo, name)
    (archived / "reviews" / "grill-review.md").write_text(VALID_GRILL_REPORT, encoding="utf-8")
    (archived / "reviews" / "building-review.md").write_text("PASS\n", encoding="utf-8")

    code, _, err = _build(repo, cli, name, "reviews/grill-review.md", "grill")
    assert code == C.EXIT_PASS, err
    code, _, err = _build(repo, cli, name, "reviews/building-review.md", "building")
    assert code == C.EXIT_PASS, err

    manifest = archived / "reviews" / "building.manifest.json"
    assert manifest.is_file()
    assert '"change_id": "' + name + '"' in manifest.read_text(encoding="utf-8")
    commit_all(repo, "证据（在归档目录内产出）")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err


def test_pre_archive_manifest_still_passes_after_archiving(repo: Path, cli):
    """D8 的钉子：归档**之前**产的 manifest（`change_id=源id`）在归档之后**仍然**通过（不必重建）。"""
    _on_main_evidenced(repo, cli)

    _archive_it(repo)
    commit_all(repo, "纯归档（不重建）")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err


def test_manifest_build_unknown_and_archive_root_and_candidate_hint(repo: Path, cli):
    """D4/C4：找不到就报错、不写文件；`archive` 根目录要说清；名字对不上的候选只**提示**不自动认。"""
    _on_main_evidenced(repo, cli)
    name = _archive_it(repo)
    commit_all(repo, "纯归档")

    code, _, err = _build(repo, cli, "no-such-change", "reviews/grill-review.md", "grill")
    assert code == C.EXIT_FAIL
    assert "no-such-change" in err
    assert not (repo / CHANGES / "no-such-change").exists()

    code, _, err = _build(repo, cli, C.ARCHIVE_DIR_NAME, "reviews/grill-review.md", "grill")
    assert code == C.EXIT_FAIL
    assert "archive" in err  # 提示这是归档根目录，不是 change id

    # 源 id 不是归档目录名 ⇒ 不自动认，但要把候选提示出来
    code, _, err = _build(repo, cli, CHANGE, "reviews/grill-review.md", "grill")
    assert code == C.EXIT_FAIL
    assert name in err, err
    assert "没有写出任何文件" in err


def test_rebuilding_a_moved_manifest_in_the_same_diff_is_accepted(repo: Path, cli):
    """**语义反转**（R12 / N7 曾被判红）：同一个 diff 里 move + 改写被 move 的 manifest ⇒ 绿。

    这就是接入方的**真实形态 ii**（先在最终内容 head 上重建 manifest、再做 move ⇒ `R<100`）——
    `archive-arrival-recognition` 正是为它而来：到达判定看**目录级事实**（`archive/<name>/` 在基准树里
    没有 entry、在 head 里件齐、内容不是搬运来的），**不看**逐文件改名分 ⇒ 不再有幽灵 active id。
    """
    _on_main_evidenced(repo, cli)

    name = _archive_it(repo)
    moved = _archive_dir(repo, name) / "reviews" / "building.manifest.json"
    moved.write_text(moved.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    commit_all(repo, "归档 + 改写被 move 的 manifest（禁止的形态）")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert f"{CHANGES}/{CHANGE}：change 目录不存在" not in err   # 无幽灵 active id


def test_rebuilding_an_already_archived_manifest_needs_one_event_each(repo: Path, cli):
    """§1.5 第 3 条：归档**已在 base** 时重建（`M`）⇒ 每条 manifest 各要一条解释事件。"""
    _on_main_evidenced(repo, cli)
    git(repo, "checkout", "-q", "main")            # 归档 + 收尾都落在 base 上
    name = _archive_it(repo)
    commit_all(repo, "纯归档")
    write_artifact(repo, "docs/notes.md", "# 收尾\n")  # 换一个 revision（不改代码 ⇒ 不触发 stage 门）
    commit_all(repo, "收尾")
    git(repo, "checkout", "-q", "-b", "rebuild")

    archived = _archive_dir(repo, name)
    for report, stage in (
        ("reviews/grill-review.md", "grill"),
        ("reviews/grill-adversarial.md", "grill-adversarial"),
        ("reviews/building-review.md", "building"),
    ):
        code, _, err = _build(repo, cli, name, report, stage)
        assert code == C.EXIT_PASS, err
    commit_all(repo, "重建归档态证据（未写事件）")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    missing = [line for line in err.splitlines() if "受保护路径被写入" in line]
    assert len(missing) == 3, err

    events = archived / C.DEFAULT_EVENTS_FILE
    for stage in ("grill", "grill-adversarial", "building"):
        line = (
            '{"schema": "witnessloop/event@v1", "event_type": "protected_path_write",'
            f' "change_id": "{name}",'
            f' "artifact_path": "{ARCHIVE_REL}/{name}/reviews/{stage}.manifest.json",'
            ' "reason": "重建归档态证据", "approved_by": "user:kai"}\n'
        )
        with events.open("a", encoding="utf-8") as handle:
            handle.write(line)
    commit_all(repo, "三条解释事件")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err


# --------------------------------------------------------------------------- D. events

def _archived_change_with_a_protected_write(repo: Path, cli, *, with_event: bool) -> None:
    """§1.6 的顺序 + 一份受保护写入（事件可选地放进**归档目录**）。

    ① 收尾（受保护写入）→ ② 在 active 态产证据（绑 ①）→ ③ 归档放最后、纯 R100。
    ⚠️ 受保护写入必须排在**证据之前**——它是非证据改动，落在证据之后会（按既有规则）判 stale。
    """
    init_wired(repo, cli)
    commit_content(repo, CHANGE)          # base：active change（件齐、零 manifest）
    git(repo, "checkout", "-q", "-b", "feature")

    write_artifact(repo, "openspec/specs/specs-merge.md", "# 并入的规格\n")
    commit_all(repo, "① 收尾：把增量并入 specs（受保护写入）")
    commit_evidence(repo, CHANGE)         # ② 证据（active 态，绑 ① 的 revision）
    name = _archive_it(repo)              # ③ 归档
    if with_event:
        events = _archive_dir(repo, name) / C.DEFAULT_EVENTS_FILE
        events.write_text(
            '{"schema": "witnessloop/event@v1", "event_type": "protected_path_write",'
            f' "change_id": "{name}", "artifact_path": "openspec/specs/specs-merge.md",'
            ' "reason": "归档收尾：把增量并入 specs", "approved_by": "user:kai"}\n',
            encoding="utf-8",
        )
    commit_all(repo, "③ 归档" + ("+ 解释事件（在归档目录里）" if with_event else "（无事件）"))


def test_events_in_the_archive_cover_protected_writes(repo: Path, cli):
    """D6：**归档目录里**的合法事件重新生效 ⇒ 受保护写入不再被报（修复前红）。"""
    _archived_change_with_a_protected_write(repo, cli, with_event=True)

    code, _, err = check(repo, cli)

    assert "受保护路径被写入" not in err, err
    assert code == C.EXIT_PASS, err


def test_the_same_diff_without_the_archived_event_is_red(repo: Path, cli):
    """D6 的对照：同一 diff、事件**不**在归档目录里 ⇒ 受保护写入仍被报（证明上一条不是空真）。"""
    _archived_change_with_a_protected_write(repo, cli, with_event=False)

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "openspec/specs/specs-merge.md" in err and "没有结构化解释事件" in err


def test_deeper_events_file_is_not_read(repo: Path, cli):
    """N5（订正后的否定面）：**再深一层**的 events 文件不被读。"""
    init_wired(repo, cli)
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    deeper = repo / ARCHIVE_REL / "notes" / "sub" / C.DEFAULT_EVENTS_FILE
    deeper.parent.mkdir(parents=True, exist_ok=True)
    deeper.write_text(
        '{"schema": "witnessloop/event@v1", "event_type": "protected_path_write",'
        ' "change_id": "x", "artifact_path": "openspec/specs/deep.md",'
        ' "reason": "深一层", "approved_by": "user:kai"}\n',
        encoding="utf-8",
    )
    write_artifact(repo, "openspec/specs/deep.md", "# 深一层的受保护写入\n")
    commit_all(repo, "深一层的 events 文件 + 一份受保护写入")

    code, _, err = check(repo, cli)

    # 深一层的文件**不算数** ⇒ 那份受保护写入仍被报「没有结构化解释事件」
    assert code == C.EXIT_FAIL
    assert "openspec/specs/deep.md" in err and "没有结构化解释事件" in err


# ----------------------------------------------------------------- I. 审阅补钉（building-review 的 I2/I3/I4）

def test_uniform_validates_a_pure_archive_pr_like_active(repo: Path, cli):
    """**Q1 裁定的招牌场景**（`spec.md` §12 的 Scenario 2）：纯归档 PR 也按同一套规则校验。

    只做 `git mv`、一行代码都不改；被归档 change 的证据是归档**前**用**源 id** 产的，
    且它的 grill 报告 `## Confirmed Decisions` 只有 2 条 ⇒ uniform 下**红恰好 1 项**
    （别名那 3 项 `change_id` 已被 D8 吸收——这正是对抗轮对 Q1 例子「4 项 → 1 项」的校准）。
    """
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE, report_body=SHORT_GRILL)  # 证据齐、但 grill 报告不合规
    git(repo, "checkout", "-q", "-b", "feature")

    name = _archive_it(repo)
    commit_all(repo, "只做归档（一行代码都不改）")

    code, _, err = check(repo, cli)

    findings = [
        line for line in err.splitlines()
        if line.strip()[:2] in tuple(f"{i}." for i in range(1, 10))
    ]
    assert code == C.EXIT_FAIL
    assert len(findings) == 1, err  # ⚠️ 数数断言：uniform 只点出 grill 正文那一条
    assert "少于硬门槛 3 条" in err
    assert f"{ARCHIVE_REL}/{name}/reviews/grill-review.md" in err


def test_alias_does_not_loosen_the_change_id_check(repo: Path, cli):
    """`spec.md` §116 的 Scenario 3：别名只接受 `{归档目录名, 源 id}`——**别的** id 仍被拒。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE, doc_overrides={"change_id": "other"})  # 归档前产出的名字是别人的
    git(repo, "checkout", "-q", "-b", "feature")

    _archive_it(repo)
    commit_all(repo, "纯归档")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "manifest.change_id='other' 与目录不符" in err, err


def test_manifest_build_prefers_the_active_directory_when_both_exist(repo: Path, cli):
    """D4 的解析顺序（**回归护栏**，改前也绿）：同名 active 与 archive 并存 ⇒ 解析到 **active**。

    ⚠️ 这条**不是**「先红」用例（改前 `resolve_change_dir` 不存在，行为恰好相同）——
    它守的是「别把顺序改成 archive 优先」（那样会静默写到另一个目录）。
    """
    init_wired(repo, cli)
    commit_content(repo, "dup")                       # active 的 dup（件齐）
    (change_dir(repo, "dup") / "reviews" / "building-review.md").write_text("PASS\n", encoding="utf-8")
    commit_all(repo, "active dup")
    archived = repo / ARCHIVE_REL / "dup"             # 同名的一个**归档**目录（件齐，手工造）
    (archived / "reviews").mkdir(parents=True)
    for artifact in ("proposal.md", "design.md", "tasks.md"):
        (archived / artifact).write_text("f\n", encoding="utf-8")
    (archived / "specs").mkdir()
    commit_all(repo, "同名 archive/dup")
    git(repo, "checkout", "-q", "-b", "feature")

    code, _, err = _build(repo, cli, "dup", "reviews/building-review.md", "building")

    assert code == C.EXIT_PASS, err
    assert (repo / CHANGES / "dup/reviews/building.manifest.json").is_file()
    assert not (archived / "reviews/building.manifest.json").exists()


def _removed_alias_order_case():   # noqa: D401 - 占位：见下方注释
    """（已删除）别名取并集、与 diff 顺序无关：覆盖已迁到 `tests/test_archive_arrival.py`。

    ⚠️ 语义也变了：名识别守卫删除后，**名不认得的源**不再让整个到达被拒，而是**进别名集合**
    （源 id 侧不再按名字过滤）⇒ 旧断言「`unrelated` 不进集合」不再成立。
    """


def _disabled_alias_order_case():
    """I6 的钉子（审阅 R2-1）：同一归档目录被**两条** move 指向 ⇒ 别名取**两源的并集**、与 diff 顺序无关。

    ⚠️ 改前是「取 diff 里**先出现**的那个源」⇒ **换个顺序就换一套别名**（审阅实测过 0 项/3 项翻转）。
    本用例把**两种顺序各跑一次**并要求结果相同 ⇒ 「退回单个源」的变异必被杀死。
    """
    target = f"{ARCHIVE_REL}/2026-foo-z"
    # z 与 foo-z 都满足「`-<源id>` 后缀」；unrelated 的名不认得 ⇒ 不该进别名集合
    records = [
        _move(f"{target}/notes.md", f"{CHANGES}/z/notes.md"),
        _move(f"{target}/keep.md", f"{CHANGES}/foo-z/keep.md"),
        _move(f"{target}/other.md", f"{CHANGES}/unrelated/other.md"),
    ]
    expected = frozenset({"2026-foo-z", "z", "foo-z"})

    forward = _targets(Path("/repo"), records)
    backward = _targets(Path("/repo"), list(reversed(records)))

    assert len(forward) == 1 and len(backward) == 1
    assert forward[0].accepted_change_ids == expected
    assert backward[0].accepted_change_ids == expected  # ⚠️ 顺序无关（改前这里会漂）


def test_the_summary_counts_directories_not_deduped_ids_on_a_tie(repo: Path, cli):
    """I8 的钉子（审阅 R2-2）：同名单段 id 撞两个目录时，摘要按 **target（目录）数**算 ⇒ **报 2**。

    构造（审阅给的配方）：base 上 active `x`；feature 上「新增 `changes/x/extra.md`」
    **且**「`git mv changes/x/notes.md → archive/x/notes.md`」（`name == 源 id` ⇒ 授予）⇒
    同一个 id `x` 同时来自 active 目录与归档。
    ⚠️ 改前按**去重 id** 算 ⇒ 报 1，把两个目录说成一个（findings 一条不少，纯诊断口径）。
    `0 个 change 目录` 那个子串由 `test_report_still_says_zero_change_dirs_for_a_docs_only_diff` 守着（仍绿）。
    """
    init_wired(repo, cli)
    commit_content(repo, "x")                     # base：active x（件齐）
    (change_dir(repo, "x") / "notes.md").write_text("notes\n", encoding="utf-8")
    commit_all(repo, "base：x 带 notes.md")
    git(repo, "checkout", "-q", "-b", "feature")

    # ⚠️ **配方订正**（R3 的 B1）：原配方（「整份 move `changes/x` → `archive/x` + 新建 `changes/x`」）
    # 产出的 `archive/x/` **不是** target——新 active change 占着同一路径 ⇒ git 报 `M` 而非 `D`
    # ⇒ 改名配不成 ⇒ 内容来源判据命中。改用：`archive/x` 走**出生即归档**（要件全新）+
    # 在 base 已有、head 仍存在的 `changes/x` 上改一个文件（`M`）⇒ 同 id 撞两个目录、两份都校验。
    archived = repo / ARCHIVE_REL / "x"
    (archived / "specs" / "retry").mkdir(parents=True, exist_ok=True)
    (archived / "reviews").mkdir(parents=True, exist_ok=True)
    for rel, body in (
        ("proposal.md", "# proposal\n\nx。\n"),
        ("design.md", "# design\n\nx。\n"),
        ("tasks.md", "# tasks\n\n- [ ] x\n"),
        ("specs/retry/spec.md", "# spec: x\n"),
        ("reviews/notes.md", "占位：空目录不被 git 跟踪。\n"),
    ):
        (archived / rel).write_text(body, encoding="utf-8")
    (change_dir(repo, "x") / "notes.md").write_text("notes-2\n", encoding="utf-8")
    commit_all(repo, "出生即归档的 archive/x + 改 active x")

    code, out, err = check(repo, cli)

    assert "2 个 change 目录" in out, out      # ⚠️ 报 2（去重 id 的实现会报 1）
    assert "x, x（归档）" in out, out          # 两个 target 都要列出来
    assert code == C.EXIT_FAIL
    # 两侧**各出** finding（撞车时两份都校验，与 D7 一致）
    assert f"{CHANGES}/x：" in err, err
    assert f"{ARCHIVE_REL}/x：" in err, err


# --------------------------------------------------------------------------- E. 否定面

def test_N1_code_only_without_any_change_dir_is_still_rejected(repo: Path, cli):
    init_wired(repo, cli)
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "只改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "src/app.py" in err and "require_change_for" in err
    # I1：文案要**真的**提到归档 move（`[x]` 的那半不能落空）
    assert "归档 move" in err and "git mv" in err


def test_N2_a_forged_archive_grants_nothing(repo: Path, cli):
    """N2：**新建** `archive/<name>/…`（无 active 源）+ 改代码 ⇒ 不生效。"""
    init_wired(repo, cli)
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")
    fake = repo / ARCHIVE_REL / f"{DAY}-fake"
    fake.mkdir(parents=True)
    for name in ("proposal.md", "design.md", "tasks.md"):
        (fake / name).write_text("f\n", encoding="utf-8")
    (fake / "specs").mkdir()
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "伪造归档 + 改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    # ⚠️ 该假目录**缺 `reviews/`**（且 specs/ 是空目录、不进树）⇒ 判据 2 不成立 ⇒ **不是到达**
    # ⇒ 落到「没有任何 change 目录」这条既有文案上（与改动前一致；见 design §5.3 N7/N2 的说明）。
    assert "没有任何 change 目录" in err, err


def test_N3_deleting_a_change_dir_is_not_an_archive(repo: Path, cli):
    """N3：删除（`D`，非 rename）仍报「change 目录不存在」。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)      # 这两步各自提交 ⇒ 不再额外 commit
    git(repo, "checkout", "-q", "-b", "feature")
    import shutil

    shutil.rmtree(change_dir(repo, CHANGE))
    commit_all(repo, "删掉 change 目录")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "change 目录不存在" in err


def test_N4_touching_a_file_inside_the_archive_grants_nothing(repo: Path, cli):
    """N4：只改归档目录里**已存在**的文件（`M`）+ 改代码 ⇒ 该 change 不进集合。

    ⚠️ 归档本身必须**已在 base**（否则那条改动会与 move 撞成 `R<100`，落到 R12 那条红上，
    测不出本条的语义）。
    """
    _on_main_evidenced(repo, cli)
    git(repo, "checkout", "-q", "main")           # 归档要落在 base 上
    name = _archive_it(repo)
    commit_all(repo, "纯归档（落在 base 上）")
    git(repo, "checkout", "-q", "-b", "touching")

    touched = _archive_dir(repo, name) / "reviews" / "building-review.md"
    touched.write_text(touched.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "碰归档 + 改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "没有任何 change 目录" in err, err


def test_N6_partial_move_into_an_existing_archive_dir_keeps_the_source_validated(repo: Path, cli):
    """**语义反转**（N6 曾被判「不授予」）：目标目录在基准树里存在 ⇒ **不是到达**（判据 1），
    但源 change `another-change` **仍在 head 里** ⇒ 它照旧按 **active** 契约被校验 ⇒ 依旧红。

    ⚠️ 与旧口径的差别：旧实现在这里报「没有任何 change 目录」（源被 `archived_sources` 静默排除），
    新口径**不排除仍在 head 的源目录**（「源 change 不得静默逃检」）——所以报的是**缺件/缺 manifest**。
    """
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)
    name = _archive_it(repo)
    commit_all(repo, "把它归档")
    # 另造一个 active change，只搬它的一个文件进**已存在的** archive/<name>/
    other = "another-change"
    commit_content(repo, other)
    (change_dir(repo, other) / "notes.md").write_text("notes\n", encoding="utf-8")
    commit_all(repo, "再造一个 active change（带 notes.md）")
    git(repo, "checkout", "-q", "-b", "feature")

    git(repo, "mv", f"{CHANGES}/{other}/notes.md", f"{ARCHIVE_REL}/{name}/notes.md")
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "把别人的文件搬进已存在的归档目录 + 改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert f"{CHANGES}/{other}：缺少 review manifest" in err, err   # 源仍被按 active 契约校验
    assert "没有任何 change 目录" not in err


# --------------------------------------------- F. 到达判定（archive-arrival-recognition / issue #26）
# 判据本身（五条里的 1 / 2 / 3 / 5）在 `tests/test_archive_arrival.py`（纯函数、假树）里覆盖；
# 这里只钉**接线**与**行为变化**（改动前红 / 改动后绿 或反过来）。

def _born_archived_artifacts(repo: Path, name: str) -> None:
    """出生即归档的**内容**面：件齐（含 `reviews/` 里一个被跟踪的文件——空目录不进树）。"""
    for rel, body in (
        ("proposal.md", "# proposal\n\n出生即归档。\n"),
        ("design.md", "# design\n\n同 PR 内产生。\n"),
        ("tasks.md", "# tasks\n\n- [x] 做完\n"),
        ("specs/retry/spec.md", "# spec: retry\n\n能力增量。\n"),
        ("reviews/grill-review.md", VALID_GRILL_REPORT),
        ("reviews/grill-adversarial.md", "# Grill-ADVERSARIAL\n\n证伪失败 N 条。\n"),
        ("reviews/building-review.md", "PASS\n"),
    ):
        write_artifact(repo, f"{ARCHIVE_REL}/{name}/{rel}", body)


def _born_archived_evidence(
    repo: Path, cli, name: str, stages: tuple[str, ...] = ("grill", "grill-adversarial", "building")
) -> None:
    """出生即归档的**证据**面（必须晚于内容提交：manifest 绑当时的 HEAD）。"""
    reports = {
        "grill": "reviews/grill-review.md",
        "grill-adversarial": "reviews/grill-adversarial.md",
        "building": "reviews/building-review.md",
    }
    for stage in stages:
        code, _, err = _build(repo, cli, name, reports[stage], stage)
        assert code == C.EXIT_PASS, err


def _implement_then_evidence_then_move(repo: Path, cli, target_name: str, change: str = CHANGE) -> None:
    """接入方的正确时序：① 改代码 → ② 在 active 态重建证据（绑 ①）→ ③ `git mv` 归档（放最后）。"""
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "① 内容")
    commit_evidence(repo, change)
    (repo / ARCHIVE_REL).mkdir(parents=True, exist_ok=True)
    git(repo, "mv", f"{CHANGES}/{change}", f"{ARCHIVE_REL}/{target_name}")
    commit_all(repo, f"③ 归档到 {target_name}")


def test_F1_born_archived_with_evidence_passes(repo: Path, cli):
    """症状 1（出生即归档）：change 与实现同一 PR 内产生、**全部记录是 `A`** ⇒ 退出码 0。"""
    init_wired(repo, cli)
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")

    _born_archived_artifacts(repo, "2026-10-15-born")
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "① 内容（出生即归档的要件 + 改代码）")
    _born_archived_evidence(repo, cli, "2026-10-15-born")   # ② 证据（绑 ① 的 revision）

    code, out, err = check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert "没有任何 change 目录" not in err
    assert "2026-10-15-born（归档）" in out


def test_F2_name_no_longer_needs_to_recognize_the_source_id(repo: Path, cli):
    """**行为变化**（用户 2026-10-15 裁定删掉名识别守卫）：`archive/misc` 不认得源 id 也授予。"""
    _on_main_evidenced(repo, cli)
    _implement_then_evidence_then_move(repo, cli, "misc")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err                      # 改动前：红（名识别不满足）


def test_F3_renaming_the_change_id_while_archiving_is_accepted(repo: Path, cli):
    """**行为变化**：归档时**顺带改 change id**（`changes/old-id → archive/<date>-new-id`）不再被拒。"""
    _on_main_evidenced(repo, cli)
    _implement_then_evidence_then_move(repo, cli, "2026-10-15-renamed")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err                      # 改动前：红


def test_F4_copied_evidence_is_not_granted(repo: Path, cli):
    """判据 5（真 git）：把既有归档目录**整份 `cp`** 到新名（源不动）+ 改 manifest 字段 ⇒ 不授予。"""
    _on_main_evidenced(repo, cli)
    git(repo, "checkout", "-q", "main")
    _archive_it(repo)                                   # base 上有一份证据齐全的归档 change
    commit_all(repo, "base 上的归档")
    git(repo, "checkout", "-q", "-b", "copy-attack")

    import shutil

    source = _archive_dir(repo)
    target = repo / ARCHIVE_REL / "2026-10-15-copied"
    shutil.copytree(source, target)
    for manifest in (target / "reviews").glob("*.manifest.json"):
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(ARCHIVED_NAME, "2026-10-15-copied"),
            encoding="utf-8",
        )
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "整份复制现成证据 + 改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "没有任何 change 目录" in err, err            # 到达被拒 ⇒ 报的是「没有 change 目录」


def test_F5_protected_file_moved_into_the_arrival_still_needs_an_event(repo: Path, cli):
    """D5（旧侧条件）：把**受保护文件**搬进到达目录 ⇒ 仍要解释事件（豁免不得只看新侧）。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)
    write_artifact(repo, "openspec/specs/moved.md", "# 受保护内容\n")
    commit_all(repo, "main：受保护文件")
    git(repo, "checkout", "-q", "-b", "feature")

    name = _archive_it(repo)
    git(repo, "mv", "openspec/specs/moved.md", f"{ARCHIVE_REL}/{name}/moved.md")
    commit_all(repo, "把 base 里的受保护文件搬进到达目录")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "openspec/specs/moved.md" in err and "没有结构化解释事件" in err, err


def test_F6_partial_move_into_a_fresh_arrival_keeps_the_source_validated(repo: Path, cli):
    """D4 收窄：到达目录 + 把**另一个仍在 head 的** active change 的文件搬进去 ⇒ 源仍被校验。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_content(repo, "another-change")
    (change_dir(repo, "another-change") / "notes.md").write_text("n\n", encoding="utf-8")
    commit_all(repo, "base：两个 active change")
    git(repo, "checkout", "-q", "-b", "feature")

    _born_archived_artifacts(repo, "2026-10-15-fresh")
    git(repo, "mv", f"{CHANGES}/another-change/notes.md",
        f"{ARCHIVE_REL}/2026-10-15-fresh/notes.md")
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "① 内容")
    _born_archived_evidence(repo, cli, "2026-10-15-fresh", stages=("grill", "building"))

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL, err
    assert f"{CHANGES}/another-change" in err, err       # 源仍在 head ⇒ 仍按 active 契约被问话


def test_F7_empty_file_in_the_arrival_is_exempt(repo: Path, cli):
    """判据 5 的空文件豁免：到达目录里放一个**空**文件（base 里也有空文件）⇒ 不被拒。"""
    init_wired(repo, cli)
    write_artifact(repo, "openspec/changes/placeholder/.keep", "")
    commit_all(repo, "base：一个空文件")
    git(repo, "checkout", "-q", "-b", "feature")

    _born_archived_artifacts(repo, "2026-10-15-with-empty")
    write_artifact(repo, f"{ARCHIVE_REL}/2026-10-15-with-empty/reviews/.gitkeep", "")
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "① 内容（含一个空文件）")
    _born_archived_evidence(repo, cli, "2026-10-15-with-empty")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_PASS, err


def test_F8_near_miss_archive_dir_is_named_in_the_message(repo: Path, cli):
    """判据 2 收紧后的**近失文案**（R3 的 E-2）：件不齐的 `archive/<name>/` 不是 target ⇒
    `require_change_for` 命中，但文案要**点名它缺了哪一件**（否则「没有任何 change 目录」会误导
    「已经建了归档目录、只是少写一件」的接入方）。"""
    init_wired(repo, cli)
    commit_all(repo, "接入 witnessloop")
    git(repo, "checkout", "-q", "-b", "feature")

    for rel, body in (
        ("proposal.md", "# proposal\n\n缺 design.md 与 specs/。\n"),
        ("tasks.md", "# tasks\n\n- [ ] 做点什么\n"),
        ("reviews/notes.md", "占位\n"),
    ):
        write_artifact(repo, f"{ARCHIVE_REL}/2026-10-15-half/{rel}", body)
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "半成品归档目录 + 改代码")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "没有任何 change 目录" in err
    assert "2026-10-15-half" in err and "缺 design.md" in err, err
