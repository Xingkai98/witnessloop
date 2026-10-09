"""``witnessloop init``：把 witnessloop 接入目标仓。

契约（design §5.1 / grill Q10）：
幂等 · 只增不改 · 不 auto-commit · 支持 ``--dry-run``。
写入 ``.witnessloop/policy.json``、``.witnessloop/init-manifest.json``、
一个极薄 caller workflow。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import sys
from pathlib import Path

from witnessloop import __version__
from witnessloop import constants as C
from witnessloop import gitutil, policy
from witnessloop.hashing import sha256_bytes


def caller_workflow(gate_ref: str) -> str:
    """极薄的 GitHub caller workflow（design §5.1 / Q8）。"""
    return (
        "# 由 `witnessloop init` 生成，请勿手改——`witnessloop uninit` 依\n"
        "# .witnessloop/init-manifest.json 的 hash 台账回滚它。\n"
        "# 门禁本体住在 reusable workflow 里，本文件只是 caller。\n"
        "name: witnessloop\n"
        "\n"
        "on:\n"
        "  pull_request:\n"
        "\n"
        "permissions:\n"
        "  contents: read\n"
        "\n"
        "jobs:\n"
        "  gate:\n"
        f"    uses: {gate_ref}\n"
    )


def desired_files(gate_ref: str) -> dict[str, str]:
    return {
        C.POLICY_PATH: policy.dumps(policy.default_policy_doc()),
        C.GATE_WORKFLOW_PATH: caller_workflow(gate_ref),
    }


def base_ref(root: Path) -> tuple[str | None, str | None]:
    """init **前**的 base ref（设计要求写进 init 台账）。非 git 仓则为 (None, None)。"""
    if not gitutil.is_repo(root):
        return None, None
    return gitutil.current_branch(root), gitutil.rev_parse(root, "HEAD")


def build_manifest(root: Path, desired: dict[str, str], gate_ref: str) -> dict:
    branch, sha = base_ref(root)
    created = [
        {"path": rel, "sha256": sha256_bytes(content.encode("utf-8"))}
        for rel, content in desired.items()
    ]
    # 台账把自己也列进创建清单（自引用 hash 无法自洽，标 self）。
    created.append({"path": C.INIT_MANIFEST_PATH, "sha256": None, "self": True})
    return {
        "schema": C.SCHEMA_INIT_MANIFEST,
        "witnessloop_version": __version__,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "base_ref": branch,
        "base_sha": sha,
        "gate_ref": gate_ref,
        "created_files": created,
    }


def render_diff(rel: str, current: str, desired: str) -> str:
    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            desired.splitlines(keepends=True),
            fromfile=f"a/{rel}（当前）",
            tofile=f"b/{rel}（witnessloop init 将写入）",
        )
    )


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"init：目标目录不存在：{root}", file=sys.stderr)
        return C.EXIT_FAIL

    desired = desired_files(args.gate_ref)
    manifest_path = root / C.INIT_MANIFEST_PATH

    if manifest_path.is_file():
        return _already_initialized(root, desired, manifest_path)

    # 只增不改：目标文件已存在且内容不同 → 冲突，报 diff 并拒绝。
    conflicts = [
        (rel, (root / rel).read_text(encoding="utf-8"), content)
        for rel, content in desired.items()
        if (root / rel).exists()
        and (root / rel).read_text(encoding="utf-8") != content
    ]
    if conflicts:
        print("init：检测到冲突（只增不改，拒绝覆盖已有文件）：", file=sys.stderr)
        for rel, current, want in conflicts:
            print(render_diff(rel, current, want), file=sys.stderr)
        return C.EXIT_FAIL

    if args.dry_run:
        print("[dry-run] init 将创建（不落盘、不 commit）：")
        for rel in desired:
            print(f"  + {rel}")
        print(f"  + {C.INIT_MANIFEST_PATH}")
        return C.EXIT_PASS

    for rel, content in desired.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest_path.write_text(
        policy.dumps(build_manifest(root, desired, args.gate_ref)), encoding="utf-8"
    )

    print("init：已接入 witnessloop（文件未 commit，请人工审阅后提交）：")
    for rel in (*desired, C.INIT_MANIFEST_PATH):
        print(f"  + {rel}")
    return C.EXIT_PASS


def _already_initialized(
    root: Path, desired: dict[str, str], manifest_path: Path
) -> int:
    """幂等：已接入且台账未漂移 → 无改动退出 0；漂移 → 报 diff 退出 1。"""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"init：{C.INIT_MANIFEST_PATH} 无法解析：{exc}", file=sys.stderr)
        return C.EXIT_FAIL

    drift: list[tuple[str, str, str]] = []
    for entry in manifest.get("created_files", []):
        rel = entry.get("path")
        if not rel or entry.get("self") or rel == C.INIT_MANIFEST_PATH:
            continue
        path = root / rel
        if not path.exists():
            drift.append((rel, "", desired.get(rel, "") or ""))
            continue
        if entry.get("sha256") and sha256_bytes(path.read_bytes()) != entry["sha256"]:
            drift.append((rel, path.read_text(encoding="utf-8"), desired.get(rel, "")))

    if drift:
        print(
            "init：已接入，但 init 创建的文件被改动过（拒绝覆盖）：",
            file=sys.stderr,
        )
        for rel, current, want in drift:
            if current == "" and want:
                print(f"  ! {rel} 缺失（台账记录它应存在）", file=sys.stderr)
            elif want:
                print(render_diff(rel, current, want), file=sys.stderr)
            else:
                print(f"  ! {rel} 内容与台账 hash 不符", file=sys.stderr)
        return C.EXIT_FAIL

    print("init：已接入 witnessloop（幂等，无改动）。")
    return C.EXIT_PASS
