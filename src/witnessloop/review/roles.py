"""roles@v1 配置（P3）。

- 读入 ``reviewloop.roles.json``（仓根，用户可编辑）；缺省用**出厂默认**。
- 展开成 ``config.resolved.json``：补默认、把 auth 的 env 引用解析成「已解析/未解析」。
- 展开后 JSON 的 sha256 写进每轮 manifest 的 ``config_hash``。

角色四元组：``reviewerA`` / ``reviewerB`` / ``fixer`` / ``judge``。每个角色的
**通路**（adapter / base_url / model / auth）都是配置，**不硬编码**任何路径进代码——
换 key / 换 base_url / 换模型都只改这个文件（或环境变量）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from witnessloop import constants as C
from witnessloop.hashing import sha256_bytes
from witnessloop.review import adapters as A

#: review loop 里出现的角色（顺序即产物里 actors 的顺序）。
ROLE_NAMES = ("reviewerA", "reviewerB", "fixer", "judge")

#: 两个 reviewer 角色——「两路同一 actor」负样本只看它们。
REVIEWER_ROLES = ("reviewerA", "reviewerB")


def default_roles_doc() -> dict:
    """出厂默认角色表。

    ⚠️ 这里的 base_url / model 是**真值表的缺省**，但 auth 一律走环境变量：
    key 不进仓、不进 config.resolved.json（那是要哈希、可能提交的产物）。
    某条通路拿不到 key（env 未设）⇒ 运行期回落（见 orchestrator 的回落规则）。
    """
    return {
        "schema": C.REVIEW_ROLES_SCHEMA,
        "roles": {
            "reviewerA": {
                "adapter": "codex",
                "model": "gpt-6.1-terra",
                "base_url": "https://heyroute.ai/v1",
                "auth_env": "WITNESSLOOP_CODEX_KEY",
            },
            "reviewerB": {
                "adapter": "claude",
                "model": "glm-5.3",
                # ⚠️ claude 适配器会拼 `/v1/messages`：这里若带 `/v1` 会打成
                # `/v1/v1/messages`（404 endpoint_not_found，T-075 实测）。故 base_url
                # 停在 `https://heyroute.ai`，适配器拼完是 `https://heyroute.ai/v1/messages`。
                "base_url": "https://heyroute.ai",
                "auth_env": "WITNESSLOOP_GLM_KEY",
            },
            "fixer": {
                "adapter": "claude",
                "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com/anthropic",
                "auth_env": "WITNESSLOOP_DEEPSEEK_KEY",
            },
            "judge": {
                "adapter": "claude",
                "model": "deepseek-v4-pro",
                "base_url": "https://api.deepseek.com/anthropic",
                "auth_env": "WITNESSLOOP_DEEPSEEK_KEY",
            },
        },
    }


def load_roles(root: str | Path) -> dict:
    """读仓根的 ``reviewloop.roles.json``；不存在 / 读不出 ⇒ 出厂默认。

    「读不出」不抛——roles 是**运行期**配置，缺它还能回落（review run 不该因
    缺配置崩溃）。但**语法坏**时抛 ``ValueError``（那是显式错误，不是缺省）。
    """
    path = Path(root) / C.REVIEW_ROLES_PATH
    if not path.is_file():
        return default_roles_doc()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        # 读不出（权限 / IO 错误）⇒ 按「缺配置」回落默认；语法坏才是显式 ValueError。
        return default_roles_doc()
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"{C.REVIEW_ROLES_PATH} 无法解析：{exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError(f"{C.REVIEW_ROLES_PATH} 根必须是 JSON 对象")
    # 允许覆盖部分角色：缺的角色用出厂默认补；**已知角色做字段级合并**，
    # 只写 model 不会把默认 adapter/base_url/auth_env 丢掉（否则会隐式落到 mock）。
    merged = default_roles_doc()
    roles = doc.get("roles") or {}
    if not isinstance(roles, dict):
        raise ValueError(f"{C.REVIEW_ROLES_PATH} 的 roles 必须是 JSON 对象")
    defaults = merged["roles"]
    for name, override in roles.items():
        if isinstance(override, dict) and name in defaults:
            merged_role = dict(defaults[name])
            merged_role.update(override)
            merged["roles"][name] = merged_role
        else:
            merged["roles"][name] = override
    merged["schema"] = doc.get("schema") or C.REVIEW_ROLES_SCHEMA
    return merged


def _auth_resolved(role: dict) -> bool:
    """该角色的 auth 在**当前环境**里是否可用。

    **委托 adapters.resolve_auth_token**——预检、回落判定与实际构造适配器必须是
    同一套口径；否则会出现「config 说未解析、实际请求却带着 token」的静默分叉。
    """
    return bool(A.resolve_auth_token(role))


def _resolved_role(role: dict, adapter: str | None, *, redact: bool = True) -> dict:
    """展开一个角色：adapter 覆盖 + auth 解析状态。

    ``redact=True``（写盘的 ``config.resolved.json``）**不写密钥**，只标
    ``auth_token_provided``；``redact=False`` 用于**运行时**角色表——实际调用必须
    拿到内联 ``auth_token``，否则会出现「resolved 说已解析、适配器拿到空串」。
    """
    src = dict(role)
    resolved_adapter = adapter or src.get("adapter")
    if not resolved_adapter:
        # 不能把「缺 adapter」静默当成 mock：mock 返回空 findings 会假 PASS。
        raise ValueError("角色缺少 adapter，拒绝隐式 mock（请显式写 adapter 或 --adapter mock）")
    out = {
        "adapter": resolved_adapter,
        "model": src.get("model") or C.REVIEW_FALLBACK_MODEL,
        "base_url": src.get("base_url") or "",
    }
    if src.get("auth_env"):
        out["auth_env"] = src["auth_env"]
    if src.get("auth_token"):
        if redact:
            # 内联 token 只标「已提供」，不落值。
            out["auth_token_provided"] = True
        else:
            out["auth_token"] = src["auth_token"]
    if src.get("allow_host_auth_fallback") is True:
        # 必须带进 resolved config：orchestrator 用的是展开后的角色，
        # 少了这个开关会出现「auth_resolved=True，但 build_adapter 拿到空 token」。
        out["allow_host_auth_fallback"] = True
    out["auth_resolved"] = _auth_resolved(src)
    return out


def _role_with_defaults(name: str, raw_roles: dict, defaults: dict) -> dict:
    """已知角色做字段级合并；缺的角色整份用默认。"""
    base = dict(defaults[name])
    override = raw_roles.get(name)
    if isinstance(override, dict):
        base.update(override)
    return base


def runtime_roles(roles_doc: dict, *, adapter: str | None = None) -> dict:
    """返回**运行时**角色表：字段与 resolved 一致，但保留内联 ``auth_token``。

    这份表只活在内存里，不写盘；`config.resolved.json` 仍用脱敏版本。
    """
    raw = roles_doc.get("roles") or {}
    defaults = default_roles_doc()["roles"]
    return {
        name: _resolved_role(
            _role_with_defaults(name, raw, defaults), adapter, redact=False
        )
        for name in ROLE_NAMES
    }


def resolve_config(
    root: str | Path,
    *,
    roles_doc: dict | None = None,
    mode: str = "auto",
    pass_rule: str = C.DEFAULT_PASS_RULE,
    stall_rounds: int = C.DEFAULT_STALL_ROUNDS,
    budget_max_cost_usd: float = C.DEFAULT_BUDGET_MAX_COST_USD,
    adapter: str | None = None,
) -> tuple[dict, list[str]]:
    """展开成 ``config.resolved.json`` 的 doc + 一串 warning。

    ``adapter`` 非空时**覆盖所有角色**的通路（``--adapter mock`` 降级链路用）。
    warning 记录「auth 未解析」这类可诊断的降级前置事实——由 orchestrator 决定
    是否因此回落，这里只陈述、不裁决。
    """
    doc = roles_doc or load_roles(root)
    raw_roles = doc.get("roles") or {}
    defaults = default_roles_doc()["roles"]
    resolved_roles: dict[str, dict] = {}
    warnings: list[str] = []
    for name in ROLE_NAMES:
        role = _role_with_defaults(name, raw_roles, defaults)
        resolved_roles[name] = _resolved_role(role, adapter)
        if not resolved_roles[name]["auth_resolved"] and adapter != "mock":
            warnings.append(f"角色 {name} 的 auth 未解析（env 未设 / 无内联 token）")
    return {
        "schema": C.REVIEW_ROLES_SCHEMA,
        "mode": mode,
        "pass_rule": pass_rule,
        "stall_rounds": stall_rounds,
        "budget": {"max_cost_usd": budget_max_cost_usd},
        "roles": resolved_roles,
    }, warnings


def dumps(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def config_hash(doc: dict) -> str:
    """展开后配置的 sha256——写进每轮 manifest 的 ``config_hash``。"""
    return sha256_bytes(dumps(doc).encode("utf-8"))


def write_config(root: str | Path, resolved_doc: dict) -> Path:
    """把 ``config.resolved.json`` 写进产物目录，返回落盘路径。"""
    out_dir = Path(root) / C.REVIEW_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / C.REVIEW_CONFIG_FILENAME
    path.write_text(dumps(resolved_doc), encoding="utf-8")
    return path
