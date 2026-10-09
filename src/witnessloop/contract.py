"""change 目录契约（OpenSpec 形状）+ review manifest 校验。

D2：change 目录必须满足 proposal/design/tasks/specs + reviews/。
D3：review manifest 存在，且 hash **绑定真实 artifact 字节**
    （base/head sha + tasks/spec/report hash）。
D4：``reviewer_run_id != author_run_id``。

能力边界（design §5.3）：hash 绑定证明「证据之间没漂移」；身份字段是自由文本，
v1 不做语义绑定——**防漂移，不防伪造**。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_tree
from witnessloop.policy import Policy


@dataclass(frozen=True)
class Finding:
    """一条校验失败。``path`` 是**仓根相对**路径，方便 CI 里点回去。"""

    path: str
    message: str


def change_dir(root: Path, policy: Policy, change_id: str) -> Path:
    return root / policy.changes_root / change_id


def changed_change_ids(changes, changes_root: str) -> list[str]:
    """从 diff 里挑出被触碰的 change id（changes_root 下的一级目录名）。"""
    prefix = changes_root.rstrip("/") + "/"
    ids: set[str] = set()
    for change in changes:
        for path in (change.path, change.old_path):
            if path and path.startswith(prefix):
                head = path[len(prefix) :].split("/", 1)[0]
                if head:
                    ids.add(head)
    return sorted(ids)


def validate_change_dir(root: Path, policy: Policy, change_id: str) -> list[Finding]:
    """D2：OpenSpec 形状的 change 目录契约。"""
    directory = change_dir(root, policy, change_id)
    rel = f"{policy.changes_root.rstrip('/')}/{change_id}"
    if not directory.is_dir():
        return [Finding(rel, "change 目录不存在（diff 里出现了它的文件，但目录不在工作树中）")]

    findings: list[Finding] = []
    for artifact in policy.required_artifacts:
        if not (directory / artifact).exists():
            findings.append(Finding(rel, f"缺少必需件 {artifact}"))
    return findings


def validate_review_manifests(
    root: Path, policy: Policy, change_id: str
) -> list[Finding]:
    """D3 + D4：review manifest 存在且 hash 绑定；reviewer ≠ author。"""
    directory = change_dir(root, policy, change_id)
    rel = f"{policy.changes_root.rstrip('/')}/{change_id}"
    manifests = sorted(directory.glob(policy.review_manifest_glob))
    if not manifests:
        return [
            Finding(
                rel,
                "缺少 review manifest（审阅证据必须「报告 + manifest」成对，"
                f"glob={policy.review_manifest_glob}）",
            )
        ]

    findings: list[Finding] = []
    for manifest_path in manifests:
        findings.extend(_validate_one(directory, rel, manifest_path))
    return findings


def _validate_one(directory: Path, rel_change: str, manifest_path: Path) -> list[Finding]:
    manifest_rel = f"{rel_change}/{manifest_path.relative_to(directory).as_posix()}"
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [Finding(manifest_rel, f"manifest 无法解析：{exc}")]
    if not isinstance(doc, dict):
        return [Finding(manifest_rel, "manifest 根必须是 JSON 对象")]

    findings: list[Finding] = []

    missing = [
        field
        for field in C.REVIEW_MANIFEST_REQUIRED_FIELDS
        if not str(doc.get(field) or "").strip()
    ]
    if missing:
        findings.append(Finding(manifest_rel, f"manifest 缺字段：{', '.join(missing)}"))
        # 缺字段时后面没法可靠比对，直接返回。
        return findings

    if doc.get("change_id") and doc["change_id"] != rel_change.rsplit("/", 1)[-1]:
        findings.append(
            Finding(manifest_rel, f"manifest.change_id={doc['change_id']!r} 与目录不符")
        )

    # D4：强制 reviewer ≠ author（挡「忘了另开 run」，不挡蓄意伪造）。
    if doc["reviewer_run_id"] == doc["author_run_id"]:
        findings.append(
            Finding(
                manifest_rel,
                "reviewer_run_id == author_run_id：审阅者必须独立于作者",
            )
        )

    # D3：hash 绑定真实 artifact 字节。
    findings.extend(_check_hashes(directory, manifest_rel, doc))
    return findings


def _check_hashes(directory: Path, manifest_rel: str, doc: dict) -> list[Finding]:
    findings: list[Finding] = []

    report_path = (directory / str(doc["report_path"])).resolve()
    if not _is_within(report_path, directory.resolve()):
        findings.append(
            Finding(
                manifest_rel,
                f"report_path={doc['report_path']!r} 逃逸出 change 目录",
            )
        )
    elif not report_path.is_file():
        findings.append(
            Finding(manifest_rel, f"报告不存在：{doc['report_path']}")
        )
    elif sha256_tree(report_path) != doc["report_hash"]:
        findings.append(
            Finding(
                manifest_rel,
                f"report_hash 不匹配：报告 {doc['report_path']} 的字节与 manifest 记录不符",
            )
        )

    for field, artifact in (("tasks_hash", "tasks.md"), ("spec_hash", "specs")):
        target = directory / artifact
        if not target.exists():
            findings.append(Finding(manifest_rel, f"{artifact} 不存在，无法校验 {field}"))
            continue
        if sha256_tree(target) != doc[field]:
            findings.append(
                Finding(
                    manifest_rel,
                    f"{field} 不匹配：{artifact} 的字节与 manifest 记录不符"
                    "（evidence 与 artifact 已漂移）",
                )
            )

    # diff_hash 是 informational（design §5.3）：在位即可，不校验内容。
    return findings


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
