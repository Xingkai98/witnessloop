"""git 读取封装。只读——witnessloop 从不写 git（init 不 auto-commit）。"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Change:
    """一条 diff 记录。

    ``status`` 是**完整**状态下标（``"A"`` / ``"M"`` / ``"D"`` / ``"R100"`` /
    ``"C075"`` …）——保留相似度分数，归档识别要判「是不是纯改名」。
    只关心字母时用 ``status[:1]``。
    """

    status: str
    path: str
    old_path: str | None = None


def _run(root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
    )


def is_repo(root: str | Path) -> bool:
    return _run(root, "rev-parse", "--git-dir").returncode == 0


def rev_parse(root: str | Path, ref: str) -> str | None:
    proc = _run(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def current_branch(root: str | Path) -> str | None:
    """当前分支名；detached HEAD 或无提交时返回 None。"""
    proc = _run(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else None


def resolve_base(root: str | Path, explicit: str | None) -> str:
    """base ref 解析：显式参数 → WITNESSLOOP_BASE_REF → GITHUB_BASE_REF → 主干。

    `check` 与 `manifest build` 共用——两边的「base 是什么」必须是同一个答案，
    否则 build 写下的 base_sha 会与 check 的 diff 基线对不上。
    """
    if explicit:
        return explicit
    env = os.environ.get("WITNESSLOOP_BASE_REF")
    if env:
        return env
    gh_base = os.environ.get("GITHUB_BASE_REF")
    if gh_base:
        return f"origin/{gh_base}"
    for candidate in ("origin/main", "main", "origin/master", "master"):
        if rev_parse(root, candidate):
            return candidate
    return "main"


def diff_text(root: str | Path, base: str, head: str) -> str:
    """``base..head`` 的统一 diff 文本（`manifest build` 的 diff_hash 用）。"""
    proc = _run(root, "diff", "--no-color", f"{base}..{head}")
    if proc.returncode != 0:
        raise GitError(
            f"无法对 {base}..{head} 求 diff：{proc.stderr.strip() or '未知错误'}"
        )
    return proc.stdout


def is_ancestor(root: str | Path, ancestor: str, descendant: str) -> bool:
    """``ancestor`` 是否在 ``descendant`` 的历史里（含相等）。"""
    return _run(root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def diff_names(root: str | Path, base: str, head: str) -> list[str]:
    """``base..head``（两点）之间被改动的文件路径（仓根相对，posix）。"""
    proc = _run(root, "diff", "--name-only", "-z", f"{base}..{head}")
    if proc.returncode != 0:
        raise GitError(
            f"无法对 {base}..{head} 求 diff：{proc.stderr.strip() or '未知错误'}"
        )
    return [path for path in proc.stdout.split("\0") if path]


def changed_files(root: str | Path, base: str, head: str) -> list[Change]:
    """``base...head``（三点，merge-base）之间的变更文件。

    merge-base 求不出来（如互不相关的历史）时抛 GitError——check 侧 fail-closed。
    """
    proc = _run(
        root, "diff", "--name-status", "-z", "--find-renames", f"{base}...{head}"
    )
    if proc.returncode != 0:
        raise GitError(
            f"无法对 {base}...{head} 求 diff：{proc.stderr.strip() or '未知错误'}"
        )
    return _parse_name_status(proc.stdout)


@dataclass(frozen=True)
class TreeEntry:
    """树里的一条 entry。``mode`` 里 `120000` = 符号链接、`160000` = gitlink（子模块）。"""

    mode: str
    type: str          # blob / tree / commit（gitlink）
    sha: str
    path: str          # 仓根相对（posix）

    @property
    def is_symlink(self) -> bool:
        return self.mode == "120000"

    @property
    def is_gitlink(self) -> bool:
        return self.type == "commit" or self.mode == "160000"


def _parse_ls_tree(out: str) -> list[TreeEntry]:
    entries: list[TreeEntry] = []
    for line in out.split("\n"):
        if not line:
            continue
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) != 3:
            continue
        mode, type_, sha = parts
        entries.append(TreeEntry(mode, type_, sha, path))
    return entries


def _ls_tree(root: str | Path, rev: str, path: str, *flags: str) -> list[TreeEntry]:
    proc = _run(root, "ls-tree", *flags, rev, "--", path)
    if proc.returncode != 0:
        raise GitError(
            f"无法读取 {rev} 的树（{path}）：{proc.stderr.strip() or '未知错误'}"
        )
    return _parse_ls_tree(proc.stdout)


def tree_entry(root: str | Path, rev: str, path: str) -> TreeEntry | None:
    """``path`` **自身**在 ``rev`` 的树里的 entry（blob / tree 都算存在）；不存在 ⇒ None。

    ⚠️ 用**不带尾斜杠**的写法：带尾斜杠时 git 只列该目录的**子项**
    ⇒ 「base 同路径是一个 blob」会被看成「不存在」（到达判定会因此放行，实测过）。
    """
    entries = _ls_tree(root, rev, path)
    return entries[0] if entries else None


def tree_children(root: str | Path, rev: str, path: str) -> list[TreeEntry]:
    """``path`` 的**直接子项**（带尾斜杠、非递归）。"""
    return _ls_tree(root, rev, path.rstrip("/") + "/")


def tree_walk(root: str | Path, rev: str, path: str) -> list[TreeEntry]:
    """``path`` **其下全部非 tree 条目**（递归）——含 blob、符号链接（`120000`）与
    gitlink（`160000 commit`）；**不含** tree 行。"""
    return _ls_tree(root, rev, path, "-r")


def show_blob(root: str | Path, rev: str, path: str) -> str | None:
    """``rev:path`` 的正文（UTF-8，替换非法字节）；读不出 ⇒ None。"""
    proc = _run(root, "show", f"{rev}:{path}")
    if proc.returncode != 0:
        return None
    return proc.stdout


def merge_base(root: str | Path, a: str, b: str) -> str | None:
    """``git merge-base a b``；求不出（互不相关历史 / 浅克隆）⇒ None（调用方 fail-closed）。"""
    proc = _run(root, "merge-base", a, b)
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and sha else None


class GitTree:
    """`contract.TreeView` 的**真 git** 实现（只读）。"""

    def __init__(self, root: str | Path) -> None:
        self.root = root

    def entry(self, rev: str, path: str) -> TreeEntry | None:
        return tree_entry(self.root, rev, path)

    def children(self, rev: str, path: str) -> list[TreeEntry]:
        return tree_children(self.root, rev, path)

    def walk(self, rev: str, path: str) -> list[TreeEntry]:
        return tree_walk(self.root, rev, path)

    def read(self, rev: str, path: str) -> str | None:
        return show_blob(self.root, rev, path)


def _parse_name_status(out: str) -> list[Change]:
    fields = out.split("\0")
    changes: list[Change] = []
    i = 0
    while i < len(fields):
        raw = fields[i]
        if not raw:
            i += 1
            continue
        # raw 形如 "A" / "M" / "R100" / "C075"——整段留作 status。
        if raw[:1] in ("R", "C"):
            changes.append(Change(raw, fields[i + 2], fields[i + 1]))
            i += 3
        else:
            changes.append(Change(raw, fields[i + 1]))
            i += 2
    return changes
