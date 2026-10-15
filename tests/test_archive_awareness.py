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


def _archive_dir(repo: Path, name: str = ARCHIVED_NAME) -> Path:
    return repo / ARCHIVE_REL / name


# --------------------------------------------------------------------------- A. 契约层

def test_change_targets_include_the_archived_change_with_its_own_id_and_alias():
    """D1/D2/D8：归档 move ⇒ 一个 target，id = **归档目录名**，接受集合 = {目录名, 源 id}。"""
    changes = [_move(f"{ARCHIVE_REL}/{ARCHIVED_NAME}/tasks.md", f"{CHANGES}/{CHANGE}/tasks.md")]

    targets = _targets(Path("/repo"), changes)

    assert len(targets) == 1
    target = targets[0]
    assert target.archived is True
    assert target.change_id == ARCHIVED_NAME
    assert target.label == f"{ARCHIVE_REL}/{ARCHIVED_NAME}"
    assert target.accepted_change_ids == frozenset({ARCHIVED_NAME, CHANGE})


def test_archive_is_never_a_change_id_and_the_moved_source_is_not_active():
    """既有性质不许被破坏：`archive` 永不作为 id；搬走的 active 源不再按 active 校验。"""
    changes = [_move(f"{ARCHIVE_REL}/{ARCHIVED_NAME}/tasks.md", f"{CHANGES}/{CHANGE}/tasks.md")]

    assert contract.changed_change_ids(changes, CHANGES) == []
    assert [t.change_id for t in _targets(Path("/repo"), changes)] == [ARCHIVED_NAME]


def test_grant_requires_the_target_name_to_recognize_the_source_id():
    """D2 第 2 条：等值 或 `-<源id>` 后缀都授予；不认得 ⇒ 不授予（第 6 面）。"""
    for name in (CHANGE, ARCHIVED_NAME):
        grant = contract.archive_grant(
            _move(f"{ARCHIVE_REL}/{name}/tasks.md", f"{CHANGES}/{CHANGE}/tasks.md"), CHANGES
        )
        assert grant == (CHANGE, name)

    # 名不认得源 id（把 z 的单个文件搬进已存在的归档目录 y）⇒ 不授予
    assert contract.archive_grant(
        _move(f"{ARCHIVE_REL}/y/notes.md", f"{CHANGES}/z/notes.md"), CHANGES
    ) is None
    # 源本来就在 archive（归档内改名）⇒ 不授予
    assert contract.archive_grant(
        _move(f"{ARCHIVE_REL}/y/notes.md", f"{ARCHIVE_REL}/x/notes.md"), CHANGES
    ) is None
    # 带走内容改动（R<100）⇒ 不授予
    assert contract.archive_grant(
        _move(f"{ARCHIVE_REL}/{ARCHIVED_NAME}/tasks.md", f"{CHANGES}/{CHANGE}/tasks.md", "R085"),
        CHANGES,
    ) is None
    # 新建（无 old_path）⇒ 不授予
    assert contract.archive_grant(gitutil.Change("A", f"{ARCHIVE_REL}/x/tasks.md"), CHANGES) is None


def test_tie_break_keeps_both_directories_for_the_same_id():
    """D7：映射以**目录**为键——同一个单段 id 同时来自 active 与归档授予时，两份都要在。"""
    changes = [
        gitutil.Change("A", f"{CHANGES}/x/extra.md"),
        _move(f"{ARCHIVE_REL}/x/notes.md", f"{CHANGES}/x/notes.md"),
    ]

    targets = _targets(Path("/repo"), changes)

    assert len(targets) == 2
    assert {t.change_id for t in targets} == {"x"}
    assert len({t.directory for t in targets}) == 2
    assert {t.label for t in targets} == {f"{CHANGES}/x", f"{ARCHIVE_REL}/x"}


# --------------------------------------------------------------------------- B. check 侧

def test_archived_change_is_validated_at_the_archived_path(repo: Path, cli):
    """D2：归档 + 改代码 ⇒ 该 change 按**归档路径**走同一套门禁（零 manifest ⇒ 四条缺件全点名）。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)          # base：active change（件齐、零 manifest；已提交）
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
    """R6 的回归护栏：`0 个 change 目录` 这个子串不许消失（既有测试按它断言）。"""
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


def test_rebuilding_a_moved_manifest_in_the_same_diff_is_rejected(repo: Path, cli):
    """R12 / N7：同一个 diff 里 move + 改写被 move 的文件 ⇒ `R<100` ⇒ 幽灵 active id（红）。"""
    _on_main_evidenced(repo, cli)

    name = _archive_it(repo)
    moved = _archive_dir(repo, name) / "reviews" / "building.manifest.json"
    moved.write_text(moved.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    commit_all(repo, "归档 + 改写被 move 的 manifest（禁止的形态）")

    code, _, err = check(repo, cli)

    assert code == C.EXIT_FAIL
    assert f"{CHANGES}/{CHANGE}：change 目录不存在" in err, err


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


def test_N6_partial_move_into_an_existing_archive_dir_grants_nothing(repo: Path, cli):
    """N6（第 6 面）：把 active change 的**单个文件**搬进**已存在的**归档目录 ⇒ 不授予。"""
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
    assert "没有任何 change 目录" in err, err
