"""确定性哈希：证据绑定的原子操作。

manifest 的 ``tasks_hash`` / ``spec_hash`` / ``report_hash`` 都走这里。
目录（如 ``specs/``）的哈希 = 对「按 posix 相对路径排序的 (路径, 内容) 对」
做 sha256——与文件系统遍历顺序无关，跨平台可复现。
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_tree(path: str | Path) -> str:
    """文件 → 其字节的 sha256；目录 → 排序后逐文件的 sha256。"""
    p = Path(path)
    if p.is_file():
        return sha256_file(p)
    if not p.is_dir():
        raise FileNotFoundError(f"没有这个文件或目录：{p}")

    h = hashlib.sha256()
    for entry in sorted(f for f in p.rglob("*") if f.is_file()):
        rel = entry.relative_to(p).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(entry.read_bytes())
        h.update(b"\0")
    return h.hexdigest()
