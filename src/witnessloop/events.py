"""``workflow-events.jsonl`` 里的结构化解释事件（D5）。

一行一个 JSON 对象。受保护路径的写入，需要在某个 change 目录的事件文件里
留下一条 ``artifact_path`` 指向它、且 ``reason`` / ``approved_by`` 非空的事件。

诚实边界（design §2 / §9 风险 1）：这些字段是自由文本，**防漂移不防伪造**——
agent 手写一行同样的 JSON 提交即可放行。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from witnessloop import paths as pathutil
from witnessloop.policy import Policy


class EventError(RuntimeError):
    """事件文件无法解析。"""


@dataclass(frozen=True)
class Event:
    event_type: str
    artifact_path: str
    reason: str
    approved_by: str
    change_id: str | None = None


def load_events_file(path: Path) -> list[Event]:
    events: list[Event] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventError(f"{path}:{lineno} 不是合法 JSON：{exc}") from exc
        if not isinstance(doc, dict):
            raise EventError(f"{path}:{lineno} 事件必须是 JSON 对象")
        events.append(
            Event(
                event_type=str(doc.get("event_type") or ""),
                artifact_path=pathutil.normalize(str(doc.get("artifact_path") or "")),
                reason=str(doc.get("reason") or "").strip(),
                approved_by=str(doc.get("approved_by") or "").strip(),
                change_id=doc.get("change_id"),
            )
        )
    return events


def load_all(root: Path, policy: Policy) -> list[Event]:
    """收集仓内所有 change 目录的事件文件。"""
    events: list[Event] = []
    for events_file in sorted(root.glob(f"{policy.changes_root}/*/{policy.events_file}")):
        events.extend(load_events_file(events_file))
    return events


def covers(event: Event, artifact_path: str, allowed_types) -> bool:
    """这条事件是否为 ``artifact_path`` 提供了合规的结构化解释。"""
    if event.event_type not in allowed_types:
        return False
    if not event.reason or not event.approved_by:
        return False
    if not event.artifact_path:
        return False
    return pathutil.matches(artifact_path, event.artifact_path) or (
        event.artifact_path == pathutil.normalize(artifact_path)
    )
