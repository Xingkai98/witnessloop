"""archive-arrival-recognition：到达判定 = 目录级事实（纯函数 + 注入树读取器）。

本文件只覆盖**纯函数层**（不碰真 git）：`contract.archive_arrivals` / `change_targets` /
`changed_change_ids` 的五条判据（编号 1 / 2 / 3 / 5——原第 4 条「名识别守卫」由用户 2026-10-15 裁定删除，
编号保留以免全文引用失效）。端到端面在 `tests/test_archive_awareness.py`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from witnessloop import constants as C
from witnessloop import contract, gitutil, policy as policy_mod

CHANGES = C.DEFAULT_CHANGES_ROOT
ARCHIVE = f"{CHANGES}/{C.ARCHIVE_DIR_NAME}"
REQUIRED = C.DEFAULT_REQUIRED_ARTIFACTS
EMPTY = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


@dataclass
class Entry:
    mode: str
    type: str
    sha: str
    path: str


@dataclass
class FakeTree:
    """假树：`{rev: {path: (mode, type, sha)}}`；`children`/`walk` 由路径前缀推导。

    `texts` 给 `read()` 用（manifest 正文 = report_path 的来源）。
    """

    trees: dict[str, dict[str, tuple[str, str, str]]] = field(default_factory=dict)
    texts: dict[tuple[str, str], str] = field(default_factory=dict)

    def _dirs(self, rev: str) -> set[str]:
        """由已存路径**推导**出目录（真 git 里目录是 tree 条目；这里现算）。"""
        out: set[str] = set()
        for p in self.trees.get(rev, {}):
            parts = p.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                out.add("/".join(parts[:i]))
        return out

    def entry(self, rev: str, path: str):
        row = self.trees.get(rev, {}).get(path)
        if row is not None:
            return gitutil.TreeEntry(row[0], row[1], row[2], path)
        if path.rstrip("/") in self._dirs(rev):
            return gitutil.TreeEntry("040000", "tree", "", path.rstrip("/"))
        return None

    def children(self, rev: str, path: str):
        prefix = path.rstrip("/") + "/"
        out: dict[str, gitutil.TreeEntry] = {}
        for p, (mode, typ, sha) in self.trees.get(rev, {}).items():
            if not p.startswith(prefix):
                continue
            rest = p[len(prefix):]
            if "/" in rest:
                head = prefix + rest.split("/", 1)[0]
                out[head] = gitutil.TreeEntry("040000", "tree", "", head)
            else:
                out[p] = gitutil.TreeEntry(mode, typ, sha, p)
        return [out[k] for k in sorted(out)]

    def walk(self, rev: str, path: str):
        prefix = path.rstrip("/") + "/"
        return sorted(
            (Entry(m, t, s, p) for p, (m, t, s) in self.trees.get(rev, {}).items() if p.startswith(prefix)),
            key=lambda e: e.path,
        )

    def read(self, rev: str, path: str):
        return self.texts.get((rev, path))


def _dir(tree: dict, path: str, *, files: dict[str, str] | None = None, mode: str = "100644"):
    """往假树里塞一个目录：`files` 映射相对路径 → blob sha（缺省给个唯一 sha）。"""
    for rel, sha in (files or {}).items():
        tree[f"{path}/{rel}"] = (mode, "blob", sha)


def _full_change(tree: dict, path: str, *, prefix: str = "") -> None:
    """一个「件齐」的 change 目录：5 件必需件 + 一份报告。"""
    _dir(tree, path, files={
        "proposal.md": f"{prefix}p",
        "design.md": f"{prefix}d",
        "tasks.md": f"{prefix}t",
        "specs/s.md": f"{prefix}s",
        "reviews/grill-review.md": f"{prefix}r",
    })


def _policy() -> policy_mod.Policy:
    return policy_mod.Policy.from_doc({})


def _arrivals(changes, base_tree: dict, head_tree: dict, *, texts=None):
    view = FakeTree(trees={"mb": base_tree, "head": head_tree}, texts=texts or {})
    return contract.archive_arrivals(changes, _policy(), view, "mb", "head")


def _move(path: str, old: str, status: str = "R100") -> gitutil.Change:
    return gitutil.Change(status, path, old)


# --------------------------------------------------------------- 判据 1 / 2
def test_condition1_a_pre_existing_archive_dir_is_never_an_arrival():
    """判据 1：基准树里该路径**有** entry（这里是 tree）⇒ 不授予。"""
    base = {}
    _full_change(base, f"{ARCHIVE}/2026-10-15-z", prefix="old-")
    head = dict(base)
    assert _arrivals([], base, head) == []


def test_condition1_base_blob_at_the_same_path_also_blocks():
    """判据 1：base 同路径是**普通文件**（blob）也算「有 entry」⇒ 不授予（R2 的 M-C1）。"""
    base = {f"{ARCHIVE}/foo": ("100644", "blob", "b1")}
    head = {f"{ARCHIVE}/foo/proposal.md": ("100644", "blob", "p")}
    assert _arrivals([], base, head) == []


def test_condition2_requires_the_full_artifact_set():
    """判据 2：缺任一必需件 ⇒ 不是 change 目录 ⇒ 不是到达（含「只含 reviews/ 子目录」的组织型目录）。"""
    head = {f"{ARCHIVE}/notes/sub/workflow-events.jsonl": ("100644", "blob", "e")}
    assert _arrivals([], {}, head) == []

    head2 = {f"{ARCHIVE}/notes/reviews/x.md": ("100644", "blob", "x")}
    assert _arrivals([], {}, head2) == []


def test_condition2_org_dir_with_only_a_subdir_is_not_a_candidate():
    """`archive/2026/10-15-foo/`：`archive/2026/` 不含必需件 ⇒ 不是 target（R1 的 F2）。"""
    head = {}
    _full_change(head, f"{ARCHIVE}/2026/10-15-foo", prefix="n-")
    assert _arrivals([], {}, head) == []


def test_born_archived_is_an_arrival():
    """出生即归档：基准树里没有 entry、head 件齐、文件全新 ⇒ 到达（**本 change 的核心目的**）。"""
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="new-")
    arrivals = _arrivals([], {}, head)
    assert [a.name for a in arrivals] == ["2026-10-15-z"]


# --------------------------------------------------------------- 判据 3
def test_condition3_renamed_from_another_archive_dir_is_not_an_arrival():
    """判据 3：到达组里有一条 `old_path` 落在 `archive/**` ⇒ 不授予（不许白捡现成证据）。"""
    base = {}
    _full_change(base, f"{ARCHIVE}/2026-09-30-old", prefix="v-")
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-new", prefix="v-")
    changes = [_move(f"{ARCHIVE}/2026-10-15-new/tasks.md", f"{ARCHIVE}/2026-09-30-old/tasks.md")]
    assert _arrivals(changes, base, head) == []


# --------------------------------------------------------------- 判据 5（内容来源）
def test_condition5_plain_copy_is_rejected():
    """判据 5：整份 `cp`（源不动 ⇒ 无 rename 记录）⇒ A 的证据全是基准树里的旧 blob ⇒ 不授予。"""
    base = {}
    _full_change(base, f"{ARCHIVE}/2026-09-30-old", prefix="v-")
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-new", prefix="v-")   # 逐字节相同
    assert _arrivals([], base, head) == []


def test_condition5_copy_with_one_byte_touch_is_still_rejected():
    """判据 5：只改**一处**（其余证据仍是旧 blob）⇒ 仍不授予。"""
    base = {}
    _full_change(base, f"{ARCHIVE}/2026-09-30-old", prefix="v-")
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-new", prefix="v-")
    head[f"{ARCHIVE}/2026-10-15-new/reviews/grill-review.md"] = ("100644", "blob", "touched")
    assert _arrivals([], base, head) == []


def test_condition5_report_moved_out_of_reviews_is_rejected():
    """判据 5（R3 的 A1）：把报告挪到 change 目录根、用 `report_path` 指过去 ⇒ 仍要被抓。"""
    base = {}
    _full_change(base, f"{ARCHIVE}/2026-09-30-old", prefix="v-")
    head = {}
    # 新目录：tasks/specs 全新，但报告是搬来的（放在**根**，不在 reviews/ 下）
    _dir(head, f"{ARCHIVE}/2026-10-15-new", files={
        "proposal.md": "np", "design.md": "nd", "tasks.md": "nt",
        "specs/s.md": "ns", "grill-review.md": "v-r", "reviews/m.manifest.json": "nm",
    })
    texts = {("head", f"{ARCHIVE}/2026-10-15-new/reviews/m.manifest.json"):
             '{"report_path": "grill-review.md"}'}
    assert _arrivals([], base, head, texts=texts) == []


def test_condition5_symlink_pointing_outside_is_rejected():
    """判据 5：符号链接指向基准树里现成 change ⇒ 按**解析后内容**比对 ⇒ 不授予。"""
    base = {}
    _full_change(base, f"{ARCHIVE}/2026-09-30-old", prefix="v-")
    head = {}
    _dir(head, f"{ARCHIVE}/2026-10-15-new", files={
        "proposal.md": "np", "design.md": "nd", "specs/s.md": "ns", "reviews/r.md": "nr",
    })
    head[f"{ARCHIVE}/2026-10-15-new/tasks.md"] = ("120000", "blob", "link")
    target = f"{ARCHIVE}/2026-09-30-old/tasks.md"
    texts = {("head", f"{ARCHIVE}/2026-10-15-new/tasks.md"): f"../../2026-09-30-old/tasks.md"}
    head[target] = ("100644", "blob", "v-t")          # 目标在 base/head 里都在
    base[target] = ("100644", "blob", "v-t")
    assert _arrivals([], base, head, texts=texts) == []


def test_condition5_symlink_inside_a_to_a_renamed_file_is_green():
    """判据 5：链接指向 `A` **之内**、且目标是本次改名落点 ⇒ 绿（本仓既有钉绿布局）。"""
    base = {}
    _full_change(base, f"{CHANGES}/z", prefix="v-")
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="v-")
    head[f"{ARCHIVE}/2026-10-15-z/reviews/alias.md"] = ("120000", "blob", "link")
    texts = {("head", f"{ARCHIVE}/2026-10-15-z/reviews/alias.md"): "grill-review.md"}
    changes = [_move(f"{ARCHIVE}/2026-10-15-z/{rel}", f"{CHANGES}/z/{rel}")
               for rel in ("proposal.md", "design.md", "tasks.md", "specs/s.md", "reviews/grill-review.md")]
    assert [a.name for a in _arrivals(changes, base, head, texts=texts)] == ["2026-10-15-z"]


def test_condition5_gitlink_is_rejected():
    """判据 5：`<A>` 下出现 gitlink（`160000`）⇒ fail-closed。"""
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="n-")
    head[f"{ARCHIVE}/2026-10-15-z/reviews/mod"] = ("160000", "commit", "deadbeef")
    assert _arrivals([], {}, head) == []


def test_condition5_empty_file_is_exempt():
    """判据 5：空文件（0 字节）豁免。"""
    base = {}
    _dir(base, f"{ARCHIVE}/2026-09-30-old", files={"reviews/.gitkeep": EMPTY})
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="n-")
    head[f"{ARCHIVE}/2026-10-15-z/reviews/.gitkeep"] = ("100644", "blob", EMPTY)
    assert [a.name for a in _arrivals([], base, head)] == ["2026-10-15-z"]


def test_condition5_shared_proposal_design_stub_is_not_a_reason_to_refuse():
    """判据 5：`proposal.md`/`design.md` 逐字节撞车**不**触发（不在 `Ev(A)` 内）。"""
    base = {}
    _dir(base, f"{ARCHIVE}/2026-09-30-old", files={"proposal.md": "stub", "design.md": "stub-d"})
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="n-")
    head[f"{ARCHIVE}/2026-10-15-z/proposal.md"] = ("100644", "blob", "stub")
    head[f"{ARCHIVE}/2026-10-15-z/design.md"] = ("100644", "blob", "stub-d")
    assert [a.name for a in _arrivals([], base, head)] == ["2026-10-15-z"]


def test_condition5_copied_spec_is_a_documented_false_positive():
    """判据 5 的**明写误伤面**：原样复制兄弟 change 的 `specs/**` ⇒ 拒绝（finding 点名该文件）。"""
    base = {}
    _dir(base, f"{ARCHIVE}/2026-09-30-old", files={"specs/limits.md": "shared"})
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="n-")
    head[f"{ARCHIVE}/2026-10-15-z/specs/limits.md"] = ("100644", "blob", "shared")
    assert _arrivals([], base, head) == []


# --------------------------------------------------------------- 目标与 id
def test_change_targets_include_arrival_with_the_directory_name_and_all_source_ids():
    """到达 target：id = 归档目录名；别名集合 = {目录名} ∪ **全部**源 id（名识别守卫已删除）。"""
    base = {}
    _full_change(base, f"{CHANGES}/z", prefix="v-")
    head = {}
    _full_change(head, f"{ARCHIVE}/misc", prefix="v-")      # 整目录搬过来 ⇒ 逐字节相同、但都是改名落点
    head[f"{ARCHIVE}/misc/notes.md"] = ("100644", "blob", "n")
    changes = [
        _move(f"{ARCHIVE}/misc/{rel}", f"{CHANGES}/z/{rel}")
        for rel in ("proposal.md", "design.md", "tasks.md", "specs/s.md", "reviews/grill-review.md")
    ] + [_move(f"{ARCHIVE}/misc/notes.md", f"{CHANGES}/unrelated/notes.md")]
    view = FakeTree(trees={"mb": base, "head": head})
    targets = contract.change_targets(
        Path("/repo"), _policy(), changes, view, "mb", "head"
    )
    assert len(targets) == 1
    assert targets[0].change_id == "misc"
    assert targets[0].archived is True
    assert targets[0].accepted_change_ids == frozenset({"misc", "z", "unrelated"})


def test_changed_change_ids_excludes_the_moved_source_and_keeps_others():
    """D4：源目录在 head 里**已不存在** ⇒ 排除它的路径；仍在 head 里 ⇒ 不排除（L：`source_ids`）。"""
    base = {}
    _full_change(base, f"{CHANGES}/z", prefix="v-")
    _full_change(base, f"{CHANGES}/other", prefix="o-")
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="v-")
    _full_change(head, f"{CHANGES}/other", prefix="o-2")     # other 仍在
    head[f"{ARCHIVE}/2026-10-15-z/notes.md"] = ("100644", "blob", "n")
    changes = [
        _move(f"{ARCHIVE}/2026-10-15-z/{rel}", f"{CHANGES}/z/{rel}")
        for rel in ("proposal.md", "design.md", "tasks.md", "specs/s.md", "reviews/grill-review.md")
    ] + [_move(f"{ARCHIVE}/2026-10-15-z/notes.md", f"{CHANGES}/other/notes.md")]
    view = FakeTree(trees={"mb": base, "head": head})
    arrivals = contract.archive_arrivals(changes, _policy(), view, "mb", "head")
    ids = contract.changed_change_ids(changes, _policy(), arrivals, view, "head")
    assert ids == ["other"]        # z 搬走了 ⇒ 排除；other 仍在 ⇒ 保留


def test_changed_change_ids_covers_d_side_paths_when_the_file_was_rewritten():
    """D4：`D` 侧记录（无 `old_path`）在「整体重写」形态下也要被排除（R3 的 A4）。"""
    base = {}
    _full_change(base, f"{CHANGES}/z", prefix="v-")
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="v-2")
    changes = (
        # 未改动的 4 份：仍是 R100（源目录 = z ⇒ 到达组的源可知）
        [_move(f"{ARCHIVE}/2026-10-15-z/{rel}", f"{CHANGES}/z/{rel}")
         for rel in ("design.md", "proposal.md", "specs/s.md", "reviews/grill-review.md")]
        # 被**整体重写**的 tasks.md：git 配不成改名 ⇒ `D`（无 old_path）+ `A`
        + [gitutil.Change("D", f"{CHANGES}/z/tasks.md"),
           gitutil.Change("A", f"{ARCHIVE}/2026-10-15-z/tasks.md")]
    )
    view = FakeTree(trees={"mb": base, "head": head})
    arrivals = contract.archive_arrivals(changes, _policy(), view, "mb", "head")
    assert contract.changed_change_ids(changes, _policy(), arrivals, view, "head") == []


def test_archive_is_never_a_change_id():
    head = {}
    _full_change(head, f"{ARCHIVE}/2026-10-15-z", prefix="n-")
    changes = [gitutil.Change("A", f"{ARCHIVE}/2026-10-15-z/tasks.md")]
    view = FakeTree(trees={"mb": {}, "head": head})
    arrivals = contract.archive_arrivals(changes, _policy(), view, "mb", "head")
    assert contract.changed_change_ids(changes, _policy(), arrivals, view, "head") == []
