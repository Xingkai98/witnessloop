"""review loop 的 revision 锚点（P1）。

两种锚点：

* ``GitRevision``：commit sha + 祖先关系校验（复用 ``gitutil``，只读）。
* ``DigestRevision``：工作树的 ``sha256_tree``——稳定排序、排除 ``.git``、
  排除**自身输出目录**（``.witnessloop/review``，否则每写一轮 manifest 就会改掉
  自己的锚，永远对不上）。

``mode: auto`` 探测：有 ``.git`` 用 Git；否则用 Digest。Git 仓**没有提交**时
（``rev-parse HEAD`` 为空）也退回 Digest——没有 commit 就无从锚定 git revision。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from witnessloop import constants as C
from witnessloop import gitutil

#: Digest 计算时从工作树里**整体**排除的顶层路径（仓根相对、posix）。
#: ``.git`` 是 VCS 内部；``.witnessloop/review`` 是 review loop 自己的产物目录。
DIGEST_EXCLUDED_TOP = (".git", C.REVIEW_OUTPUT_DIR)


@dataclass(frozen=True)
class Revision:
    """一个 revision 锚点。``mode`` ∈ {``git``, ``digest``}，``value`` 是对应的 sha。

    对 ``git``：``value`` = HEAD 的 commit sha。对 ``digest``：``value`` = 工作树
    sha256（见 ``worktree_digest``）。digest 没有「祖先」概念，``is_ancestor``
    对它只支持相等比较——见该方法。
    """

    mode: str
    value: str

    def is_ancestor(self, root: str | Path, descendant: "Revision") -> bool:
        """``self`` 是否在 ``descendant`` 的历史里（git 用 merge-base；digest 只判相等）。"""
        if self.mode == "git" and descendant.mode == "git":
            return gitutil.is_ancestor(root, self.value, descendant.value)
        return self.value == descendant.value


def detect_mode(root: str | Path) -> str:
    """``mode: auto`` 的探测：有 ``.git`` 用 ``git``，否则 ``digest``。"""
    return "git" if gitutil.is_repo(root) else "digest"


def _excluded(rel: str, excludes) -> bool:
    """``rel`` 是否等于某个排除项、或落在它之下（排除项可能是多段路径）。"""
    return any(rel == ex or rel.startswith(ex + "/") for ex in excludes)


def worktree_digest(root: str | Path, *, excludes=DIGEST_EXCLUDED_TOP) -> str:
    """工作树的 sha256：对按 posix 相对路径排序的 ``(路径, 内容)`` 对做 sha256。

    排除 ``excludes`` 里的顶层路径（``.git`` 单段、``.witnessloop/review`` 多段都按
    **路径前缀**排除）。与 ``hashing.sha256_tree`` 同一条「稳定排序」约定，
    但多一个**排除**维度——review loop 的产物目录必须在锚之外，否则会自指。
    """
    root_path = Path(root)
    h = hashlib.sha256()
    for entry in sorted(f for f in root_path.rglob("*") if f.is_file()):
        rel = entry.relative_to(root_path).as_posix()
        if _excluded(rel, excludes):
            continue
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(entry.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def resolve_revision(
    root: str | Path, mode: str = "auto", *, excludes=DIGEST_EXCLUDED_TOP
) -> Revision:
    """按 ``mode`` 解析出当前 revision 锚点。

    ``mode="auto"`` → ``detect_mode``；显式 ``git`` / ``digest`` 时不猜测，直接走那一条。
    git 模式下取不到 HEAD（无提交）时退回 digest——**如实标注 mode**，不谎报 git。
    """
    root = Path(root)
    if mode not in ("auto", "git", "digest"):
        raise ValueError(f"未知 revision mode：{mode!r}（可选 auto/git/digest）")
    resolved_mode = detect_mode(root) if mode == "auto" else mode
    if resolved_mode == "git":
        head = gitutil.rev_parse(root, "HEAD")
        if head is not None:
            return Revision("git", head)
        # 有 .git 但没有提交：无 commit 可锚，退回 digest（诚实标注）。
        return Revision("digest", worktree_digest(root, excludes=excludes))
    return Revision("digest", worktree_digest(root, excludes=excludes))
