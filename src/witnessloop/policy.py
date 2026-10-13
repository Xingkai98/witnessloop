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
        "require_change_for": list(C.DEFAULT_REQUIRE_CHANGE_FOR),
        "required_artifacts": list(C.DEFAULT_REQUIRED_ARTIFACTS),
        "evidence": {
            "review_manifest_glob": C.DEFAULT_REVIEW_MANIFEST_GLOB,
            "events_file": C.DEFAULT_EVENTS_FILE,
            "protected_write_event_types": list(C.DEFAULT_PROTECTED_EVENT_TYPES),
            "grill_stage": C.DEFAULT_GRILL_STAGE,
            "grill_adversarial_stage": C.DEFAULT_GRILL_ADVERSARIAL_STAGE,
            "building_stage": C.DEFAULT_BUILDING_STAGE,
        },
        # ⚠️ 刻意**不物化** `tests` 键（change adopter-test-gate / 对抗轮 X2）：
        # 出厂 doc 一旦多一个键，**已接入的仓**跑 plain `init` 就会因「本次期望 ≠ 磁盘」
        # 命中冲突分支 exit 1（实测）——而 `init` 是唯一的升级入口。
        # 「缺省 ⇒ 声明」这条语义**只活在 `from_doc` 里**。
    }


@dataclass(frozen=True)
class Policy:
    changes_root: str
    protected_paths: tuple[str, ...]
    require_change_for: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    review_manifest_glob: str
    events_file: str
    protected_write_event_types: tuple[str, ...]
    grill_stage: str
    grill_adversarial_stage: str
    building_stage: str
    #: 策略里**显式**写了 `tests.disabled: true`（= 唯一的 opt-out 字面）。
    #: 缺省 / `""` / `null` / `false` 一律读成「**声明了**测试执行点」（见 `from_doc`）。
    tests_disabled: bool

    @property
    def archive_root(self) -> str:
        return f"{self.changes_root.rstrip('/')}/{C.ARCHIVE_DIR_NAME}"

    @property
    def stale_exempt_paths(self) -> tuple[str, ...]:
        """被审阅 revision 之后**允许**出现的路径（D3 判 stale 时的豁免集）。

        * 证据本体——刻意收窄到 **change 目录内的 reviews/**。早先用
          ``**/reviews/**``，任意深度的 ``reviews/`` 目录都算证据
          （例如 ``src/reviews/x.py``），审阅后往那儿塞内容即可绕开 stale 判定。
        * ``archive/**``——归档是**簿记动作**，把已审的 change 从 active 挪走
          不改变任何被审内容，不该算「审阅后动了非证据文件」。
        """
        root = self.changes_root.rstrip("/") + "/"
        return (
            ".witnessloop/**",  # 门禁自身配置（改动仍需解释事件）
            f"{root}*/reviews/**",  # 审阅报告 + manifest
            f"{root}*/{self.events_file}",  # 结构化解释事件
            f"{self.archive_root}/**",  # 归档（簿记）
        )

    @classmethod
    def from_doc(cls, doc: dict) -> "Policy":
        if not isinstance(doc, dict):
            raise PolicyError("policy 根必须是 JSON 对象")
        evidence = doc.get("evidence") or {}
        if not isinstance(evidence, dict):
            raise PolicyError("policy.evidence 必须是 JSON 对象")
        tests = doc.get("tests") or {}
        if not isinstance(tests, dict):
            raise PolicyError("policy.tests 必须是 JSON 对象")
        # 语义：字段**缺省** → 用出厂默认（保护性默认，别让老 policy 静默失去这条规则）；
        # 显式写 `[]` → 关掉这条规则。
        raw_require_change = doc.get("require_change_for")
        return cls(
            changes_root=str(doc.get("changes_root") or C.DEFAULT_CHANGES_ROOT),
            protected_paths=tuple(doc.get("protected_paths") or ()),
            require_change_for=tuple(
                C.DEFAULT_REQUIRE_CHANGE_FOR
                if raw_require_change is None
                else raw_require_change
            ),
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
            grill_stage=str(
                evidence.get("grill_stage") or C.DEFAULT_GRILL_STAGE
            ),
            grill_adversarial_stage=str(
                evidence.get("grill_adversarial_stage")
                or C.DEFAULT_GRILL_ADVERSARIAL_STAGE
            ),
            building_stage=str(
                evidence.get("building_stage") or C.DEFAULT_BUILDING_STAGE
            ),
            # 测试执行点（change adopter-test-gate / design D6）。**缺省 ⇒ 声明**——与
            # `require_change_for` 同一条既有惯例（保护性默认，别让老 policy 静默失去这条规则）。
            #
            # 唯一的 opt-out 字面是**布尔** `tests.disabled: true`：这里刻意用 `is True`
            # 而不是 truthiness——本文件别处是 `value or DEFAULT`（falsy 即回落），
            # 于是 `""` / `null` / 缺省**都会**被读成「声明」。若 opt-out 也走 truthiness，
            # 「显式置空 ⇒ 不判」就会被实现成「不判 ⇒ 其实还判」，两种读法后果相反。
            tests_disabled=tests.get("disabled") is True,
        )

def policy_path(root: str | Path) -> Path:
    return Path(root) / C.POLICY_PATH


def load_policy(root: str | Path) -> Policy | None:
    """读目标仓 policy；返回 None 表示**未接入**（check 据此 fail-closed）。"""
    path = policy_path(root)
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # ValueError 涵盖 json.JSONDecodeError **与** UnicodeDecodeError（非法 UTF-8 的 policy）——
        # 后者此前漏捕 ⇒ 崩溃退 1 ⇒ 被 host 当成 block（change guard-crash-exit / #9）。
        raise PolicyError(f"{C.POLICY_PATH} 无法解析：{exc}") from exc
    return Policy.from_doc(doc)


def dumps(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
