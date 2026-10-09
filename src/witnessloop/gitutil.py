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
