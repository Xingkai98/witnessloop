"""``witnessloop uninit``：依 ``init-manifest.json`` 精确回滚接入。

契约（design §5.1 / grill Q10）：按台账逐文件核对 hash 后删除；
**任一文件被改过 → 整批拒绝删除并报 diff**（避免留下半删状态）；
重复执行安全（幂等）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from witnessloop import constants as C
from witnessloop import initcmd, paths as pathutil
from witnessloop.hashing import sha256_bytes


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    manifest_path = root / C.INIT_MANIFEST_PATH

    if not manifest_path.is_file():
        # 幂等：没接入 / 已回滚过 / 台账被删 —— 都无改动。
        print("uninit：未接入（或已回滚），无改动。")
        return C.EXIT_PASS

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"uninit：{C.INIT_MANIFEST_PATH} 无法解析：{exc}", file=sys.stderr)
        return C.EXIT_FAIL

    # init 写入的内容是 gate_ref 的纯函数 → 可以给出**真实**的内容 diff。
    gate_ref = manifest.get("gate_ref") or C.DEFAULT_GATE_REF
    desired = initcmd.desired_files(gate_ref)

    conflicts: list[tuple[str, Path]] = []
    doomed: list[Path] = []
    escapes: list[str] = []
    for entry in manifest.get("created_files", []):
        rel = entry.get("path")
        if not rel:
            continue
        path = root / rel
        # 台账可以被 agent 提交，所以每个待删路径都必须先过 containment：
        # 否则 `path:"../secret.txt"` 会真删仓外文件，绝对路径还会让
        # `relative_to(root)` 抛未捕获 ValueError。
        if not pathutil.is_within(path, root):
            escapes.append(rel)
            continue
        if entry.get("self") or rel == C.INIT_MANIFEST_PATH:
            doomed.append(path)  # 台账自己最后删
            continue
        if not path.exists():
            continue  # 已被人工删除：无可删，放行
        expected = entry.get("sha256")
        if expected and sha256_bytes(path.read_bytes()) != expected:
            conflicts.append((rel, path))
            continue
        doomed.append(path)

    if escapes:
        print("uninit：台账里有越界路径（仓根之外），拒绝执行：", file=sys.stderr)
        for rel in escapes:
            print(f"  ! {rel} 不在仓根 {root} 之内", file=sys.stderr)
        print("uninit：整批未删除。台账可能被篡改，请人工核对。", file=sys.stderr)
        return C.EXIT_FAIL

    if conflicts:
        print("uninit：以下文件被改动过，拒绝删除：", file=sys.stderr)
        for rel, path in conflicts:
            if rel in desired:
                print(
                    initcmd.render_diff(
                        rel, path.read_text(encoding="utf-8"), desired[rel]
                    ),
                    file=sys.stderr,
                )
            else:
                print(f"  ! {rel} 内容与 init 台账的 sha256 不符", file=sys.stderr)
        print(
            "uninit：整批未删除。请人工确认这些改动后重试。",
            file=sys.stderr,
        )
        return C.EXIT_FAIL

    print("uninit：已回滚 witnessloop 接入：")
    for path in doomed:
        rel = path.relative_to(root).as_posix()
        path.unlink()
        print(f"  - {rel}")

    _prune_empty_dirs(root, [p.parent for p in doomed])
    return C.EXIT_PASS


def _prune_empty_dirs(root: Path, dirs) -> None:
    """删掉因回滚而变空的目录，但只删到仓根为止、且只在空的时候。

    再次做 containment 检查是纵深防御：越界条目已在上面整批拒绝，
    这里不该再有机会上溯到仓外。
    """
    root = root.resolve()
    for directory in sorted({d.resolve() for d in dirs}, key=lambda d: -len(d.parts)):
        if not pathutil.is_within(directory, root):
            continue
        current = directory
        while current != root and current.is_dir() and not any(current.iterdir()):
            current.rmdir()
            current = current.parent
