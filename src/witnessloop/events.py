"""``workflow-events.jsonl`` 里的结构化解释事件（D5）。

一行一个 JSON 对象。受保护路径的写入，需要在某个 change 目录的事件文件里
留下一条 ``artifact_path`` **点名该路径**、且 ``reason`` / ``approved_by`` 非空的事件。

诚实边界（design §2 / §9 风险 1）：这些字段是自由文本，**防漂移不防伪造**——
agent 手写一行同样的 JSON 提交即可放行。收紧 ``artifact_path`` 只堵「一条通配
豁免一切」，不改变这个边界。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from witnessloop import paths as pathutil
from witnessloop.policy import Policy

#: 在本模块的匹配语义里，这两个字符是唯一的通配符（见 ``paths.glob_to_regex``）。
GLOB_METACHARACTERS = "*?"


class EventError(RuntimeError):
    """事件文件无法解析。"""


@dataclass(frozen=True)
class Event:
    """一条解释事件。**构造即归一**：不变式在这里收口，不依赖调用方记得处理。

    ``artifact_path`` 去前导 ``./`` 并统一斜杠；``reason`` / ``approved_by`` /
    ``event_type`` 去首尾空白——否则 ``covers`` 里 ``not event.reason`` 这类
    真值判断会被 ``"   "`` 骗过去。
    """

    event_type: str
    artifact_path: str
    reason: str
    approved_by: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.event_type.strip())
        object.__setattr__(self, "artifact_path", pathutil.normalize(self.artifact_path))
        object.__setattr__(self, "reason", self.reason.strip())
        object.__setattr__(self, "approved_by", self.approved_by.strip())


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
                artifact_path=str(doc.get("artifact_path") or ""),
                reason=str(doc.get("reason") or ""),
                approved_by=str(doc.get("approved_by") or ""),
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
    """这条事件是否为**这一个**路径提供了合规的结构化解释。

    事件的 ``artifact_path`` 必须是**具体路径**，不接受通配（``*`` / ``?``）——
    否则一条 ``artifact_path:"**"`` 就能豁免全部受保护路径，
    「结构化解释」塌缩成「一行 `**` 放行一切」，连不变集都能被它绕过。
    """
    if event.event_type not in allowed_types:
        return False
    if not event.reason or not event.approved_by:
        return False
    if not event.artifact_path:
        return False
    if any(ch in event.artifact_path for ch in GLOB_METACHARACTERS):
        return False
    return event.artifact_path == pathutil.normalize(artifact_path)
