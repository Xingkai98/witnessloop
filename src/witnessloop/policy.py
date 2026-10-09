"""目标仓策略（``.witnessloop/policy.json``）与 witnessloop 自身的不变集。

不变集（design §5.1 / §9 风险 3）：witnessloop 的**自身输入**——policy 文件、
init 台账、每 change 的 review manifest、解释事件文件——**恒受保护**，repo policy
无法把它们从保护范围里移除。否则 agent 改一行 policy 就能让门禁对自己失效。
封顶 ~5 条常量（见 ``INVARIANT_PROTECTED_PATHS``）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from witnessloop import constants as C

# 不变集：**不可**由 repo policy 移除。~5 条常量封顶。
INVARIANT_PROTECTED_PATHS: tuple[str, ...] = (
    ".witnessloop/policy.json",  # 门禁自身的策略
    ".witnessloop/init-manifest.json",  # init 台账（uninit 的权威）
    "**/workflow-events.jsonl",  # 结构化解释事件
    "**/reviews/*.manifest.json",  # 审阅证据 manifest
)


class PolicyError(RuntimeError):
    """policy 缺失或结构非法。"""


def default_policy_doc() -> dict:
    """init 写入目标仓的默认 policy（v1 硬编码 OpenSpec 形状）。"""
    return {
        "schema": C.SCHEMA_POLICY,
        "changes_root": C.DEFAULT_CHANGES_ROOT,
        "protected_paths": [
            "openspec/specs/**",
            ".witnessloop/**",
        ],
        "required_artifacts": list(C.DEFAULT_REQUIRED_ARTIFACTS),
        "evidence": {
            "review_manifest_glob": C.DEFAULT_REVIEW_MANIFEST_GLOB,
            "events_file": C.DEFAULT_EVENTS_FILE,
            "protected_write_event_types": list(C.DEFAULT_PROTECTED_EVENT_TYPES),
        },
    }


@dataclass(frozen=True)
class Policy:
    changes_root: str
    protected_paths: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    review_manifest_glob: str
    events_file: str
    protected_write_event_types: tuple[str, ...]

    @classmethod
    def from_doc(cls, doc: dict) -> "Policy":
        if not isinstance(doc, dict):
            raise PolicyError("policy 根必须是 JSON 对象")
        evidence = doc.get("evidence") or {}
        if not isinstance(evidence, dict):
            raise PolicyError("policy.evidence 必须是 JSON 对象")
        return cls(
            changes_root=str(doc.get("changes_root") or C.DEFAULT_CHANGES_ROOT),
            protected_paths=tuple(doc.get("protected_paths") or ()),
            required_artifacts=tuple(
                doc.get("required_artifacts") or C.DEFAULT_REQUIRED_ARTIFACTS
            ),
            review_manifest_glob=str(
                evidence.get("review_manifest_glob")
                or C.DEFAULT_REVIEW_MANIFEST_GLOB
            ),
            events_file=str(evidence.get("events_file") or C.DEFAULT_EVENTS_FILE),
            protected_write_event_types=tuple(
                evidence.get("protected_write_event_types")
                or C.DEFAULT_PROTECTED_EVENT_TYPES
            ),
        )

    @property
    def effective_protected_paths(self) -> tuple[str, ...]:
        """repo policy ∪ 不变集。不变集永远在，policy 只能**增加**保护。"""
        seen: dict[str, None] = {}
        for pat in (*self.protected_paths, *INVARIANT_PROTECTED_PATHS):
            seen.setdefault(pat, None)
        return tuple(seen)


def policy_path(root: str | Path) -> Path:
    return Path(root) / C.POLICY_PATH


def load_policy(root: str | Path) -> Policy | None:
    """读目标仓 policy；返回 None 表示**未接入**（check 据此 fail-closed）。"""
    path = policy_path(root)
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"{C.POLICY_PATH} 无法解析：{exc}") from exc
    return Policy.from_doc(doc)


def dumps(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
