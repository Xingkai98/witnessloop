"""测试脚手架：构造 OpenSpec 形状的 change 目录、审阅证据与解释事件。"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_tree

CHANGES_ROOT = C.DEFAULT_CHANGES_ROOT


def change_dir(repo: str | Path, change_id: str) -> Path:
    return Path(repo) / CHANGES_ROOT / change_id


def write_change(
    repo: str | Path,
    change_id: str,
    *,
    artifacts: tuple[str, ...] = ("proposal.md", "design.md", "tasks.md"),
    specs: bool = True,
    reviews: bool = True,
    tasks_body: str = "# tasks\n\n- [ ] 做点什么\n",
) -> Path:
    """写一个 change 目录；``artifacts`` 用来故意缺件。"""
    directory = change_dir(repo, change_id)
    directory.mkdir(parents=True, exist_ok=True)
    bodies = {
        "proposal.md": "# proposal\n\n为什么做这个改动。\n",
        "design.md": "# design\n\n怎么做。\n",
        "tasks.md": tasks_body,
    }
    for name in artifacts:
        (directory / name).write_text(bodies[name], encoding="utf-8")
    if specs:
        (directory / "specs" / "retry").mkdir(parents=True, exist_ok=True)
        (directory / "specs" / "retry" / "spec.md").write_text(
            "# spec: retry\n\n能力增量。\n", encoding="utf-8"
        )
    if reviews:
        (directory / "reviews").mkdir(parents=True, exist_ok=True)
    return directory


def _hash_or_placeholder(path: Path) -> str:
    """缺件时给个占位 hash，让「缺件」的负例也能造出 manifest。"""
    try:
        return sha256_tree(path)
    except FileNotFoundError:
        return "placeholder-artifact-missing"


def write_review(
    repo: str | Path,
    change_id: str,
    *,
    stage: str = "building",
    report_body: str = "PASS\n\n审阅通过。\n",
    doc_overrides: dict | None = None,
    **overrides,
) -> Path:
    """写「报告 + manifest」成对证据；``overrides`` / ``doc_overrides`` 注入错误字段。"""
    directory = change_dir(repo, change_id)
    (directory / "reviews").mkdir(parents=True, exist_ok=True)
    report_rel = f"reviews/{stage}-review.md"
    (directory / report_rel).write_text(report_body, encoding="utf-8")

    doc = {
        "schema": C.SCHEMA_REVIEW_MANIFEST,
        "change_id": change_id,
        "stage": stage,
        "reviewer_run_id": "run-reviewer-1",
        "author_run_id": "run-author-1",
        "base_sha": "0" * 40,
        "head_sha": "1" * 40,
        "tasks_hash": _hash_or_placeholder(directory / "tasks.md"),
        "spec_hash": _hash_or_placeholder(directory / "specs"),
        "diff_hash": "informational-not-verified",
        "report_hash": sha256_tree(directory / report_rel),
        "report_path": report_rel,
    }
    doc.update(overrides)
    doc.update(doc_overrides or {})
    path = directory / "reviews" / f"{stage}.manifest.json"
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def write_event(
    repo: str | Path,
    change_id: str,
    artifact_path: str,
    *,
    event_type: str = "protected_path_write",
    reason: str = "受保护 spec 同步，人类已确认",
    approved_by: str = "user:kai",
) -> None:
    directory = change_dir(repo, change_id)
    directory.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "schema": C.SCHEMA_EVENT,
            "event_type": event_type,
            "change_id": change_id,
            "artifact_path": artifact_path,
            "reason": reason,
            "approved_by": approved_by,
        },
        ensure_ascii=False,
    )
    with (directory / C.DEFAULT_EVENTS_FILE).open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def check(repo: str | Path, cli, *extra: str):
    """对照 main 跑 check（feature 分支已 checkout）。"""
    return cli(
        "check", "--root", str(repo), "--base", "main", "--head", "HEAD", *extra
    )
