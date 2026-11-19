"""适配器（P3）：``claude`` / ``codex`` / ``mock``，统一接口。

输入 ``prompt + context``，输出结构化 findings JSON（``ReviewResult``）。三个适配器
**同一个** ``run`` 签名——orchestrator 不关心底层是哪个 host / 哪个 base_url。

- ``ClaudeAdapter``：Anthropic Messages API（deepseek 的 ``/anthropic`` 端点同形状）。
- ``CodexAdapter``：OpenAI ``chat/completions``（heyroute 的 ``/v1`` 端点）。
- ``MockAdapter``：确定性、无网络；按 ``round`` 返回种子 findings（测试 / 降级链路）。

**回落规则由 orchestrator 执行**：本模块只负责「调用 + 把错误归一成
``AdapterError``（含 kind）」。kind ∈ ``auth`` / ``model_not_found`` / ``balance`` /
``other``——orchestrator 据 kind 决定是否回落 ``deepseek-flash``。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

#: severity 排序（去重时「取 severity 高的那条」用）。
SEVERITY_RANK = {"nit": 0, "low": 1, "medium": 2, "high": 3, "blocker": 4}

#: 近似价格（USD / 1M tokens，输入, 输出）。成本是**估算**，只用于预算止损与报告，
#: 不是计费依据。
APPROX_PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    # gpt-6.1-sol 不在本机 model_pricing 表里；按同代 Sol 档（gpt-5.6-sol $5/$30）
    # 保守估算。换真实价格时只改这一行。
    "gpt-6.1-sol": (5.0, 30.0),
    "gpt-6.1-terra": (2.0, 8.0),
    "glm-5.3": (0.6, 2.0),
    "deepseek-flash": (0.07, 0.28),
    "deepseek-v4-pro": (0.55, 2.2),
}


def severity_rank(severity: str) -> int:
    return SEVERITY_RANK.get(str(severity).strip().lower(), -1)


def cost_usd(model: str, usage: dict | None) -> float:
    """按 usage 估这一轮的成本（USD）。"""
    if not isinstance(usage, dict):
        return 0.0
    in_price, out_price = APPROX_PRICE_PER_MTOK.get(
        str(model).lower(), (0.0, 0.0)
    )
    def _tokens(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    in_tokens = _tokens(usage.get("input_tokens"))
    out_tokens = _tokens(usage.get("output_tokens"))
    return in_tokens / 1e6 * in_price + out_tokens / 1e6 * out_price


@dataclass
class ReviewRequest:
    """一次审阅请求。``prompt`` 是角色指令，``context`` 是审阅素材（diff/tasks/…）。"""

    prompt: str
    context: str
    round: int = 0


@dataclass
class ReviewResult:
    """一次审阅的结果。``findings`` 是**结构化** finding 列表（dict），``verdict`` 三态。"""

    findings: list[dict] = field(default_factory=list)
    verdict: str = "PASS"
    model: str = ""
    raw: str = ""
    error: str | None = None
    error_kind: str | None = None
    usage: dict | None = None


class AdapterError(RuntimeError):
    """适配器调用失败，``kind`` 供 orchestrator 判定是否回落。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


def _classify(status: int, body: str) -> str:
    """把 HTTP 状态码 + 响应体归一到 error kind。"""
    low = body.lower()
    if status in (401, 403) or "invalid api key" in low or "authentication" in low:
        return "auth"
    if status == 402 or "insufficient" in low or "quota" in low or "balance" in low:
        return "balance"
    if status in (404,) or "model_not_found" in low or "not found" in low or "does not exist" in low:
        return "model_not_found"
    return "other"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """拒绝所有 HTTP 重定向：Authorization / x-api-key 不能跟着跨信任域走。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AdapterError(
            "other", f"拒绝重定向（防止凭据转发）：HTTP {code} -> {newurl}"
        )


_OPENER = urllib.request.build_opener(_NoRedirect)


def _http_json(url: str, headers: dict, payload: dict, *, timeout: int = 300) -> dict:
    """POST JSON → 解析出的 JSON 对象；失败抛 ``AdapterError``。"""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        kind = _classify(exc.code, raw)
        raise AdapterError(kind, f"HTTP {exc.code}: {raw[:400]}") from exc
    except urllib.error.URLError as exc:
        raise AdapterError("other", f"网络错误：{exc}") from exc
    except OSError as exc:
        # socket timeout（TimeoutError）/ 连接重置等也是 OSError，不是 URLError；
        # 不接住会让 review run 以「内部错误」崩溃，而不是走 BLOCKED + manifest。
        raise AdapterError("other", f"网络超时/错误：{exc}") from exc
    try:
        return json.loads(data.decode("utf-8"))
    except ValueError as exc:
        raise AdapterError("other", f"响应不是 JSON：{data[:200]!r}") from exc


def _extract_json(text: str):
    """从模型输出里取第一个**平衡**的 JSON 对象；取不到 ⇒ None。

    模型可能加前言 / 代码围栏，所以按花括号配对扫，不要求全文是 JSON。
    """
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : index + 1])
                except ValueError:
                    return None
    return None


def _top_level_object_count(text: str) -> int:
    """数顶层 JSON 对象的个数（忽略字符串里的花括号）。"""
    count = 0
    depth = 0
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                count += 1
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
    return count


def parse_review_output(text: str) -> tuple[list[dict], str, str | None]:
    """把模型输出解析成 ``(findings, verdict, error)``。

    接受 ``{"findings": [...], "verdict": "..."}`` 或 ``{"findings": [...]}``。
    解析不出 ⇒ error 非 None（orchestrator 按「通路失败」处理，走回落）。
    **必须恰好一个顶层 JSON 对象**：多个对象是歧义输出，判失败而不是取第一个。
    """
    if _top_level_object_count(text) != 1:
        return [], "PASS", "输出必须恰好包含一个 JSON 对象"
    doc = _extract_json(text)
    if not isinstance(doc, dict):
        return [], "PASS", "输出里没有可解析的 JSON 对象"
    findings = doc.get("findings")
    if findings is None and isinstance(doc.get("issues"), list):
        findings = doc.get("issues")
    if not isinstance(findings, list):
        return [], "PASS", "JSON 里没有 findings 数组"
    allowed = {"blocker", "high", "medium", "low", "nit"}
    normalized: list[dict] = []
    for index, item in enumerate(findings):
        if not isinstance(item, dict):
            return [], "PASS", f"findings[{index}] 不是对象"
        severity = str(item.get("severity") or "").strip().lower()
        if severity not in allowed:
            # 缺 severity 的 finding 会被 _pass_rule 当成「不阻塞」——必须在解析层
            # fail closed，否则畸形输出（含字符串 finding / 漏 severity）会假 PASS。
            return [], "PASS", f"findings[{index}] 的 severity 非法：{item.get('severity')!r}"
        # 校验用规范化后的值，返回给判定层的也必须是同一个值；否则
        # `severity=" high "` 会通过解析却不阻塞收敛。
        normalized.append(dict(item, severity=severity))
    findings = normalized
    verdict = str(doc.get("verdict") or "PASS").strip().upper()
    if verdict not in ("PASS", "CHANGES_REQUESTED", "BLOCKED"):
        verdict = "CHANGES_REQUESTED" if findings else "PASS"
    return findings, verdict, None


class MockAdapter:
    """确定性适配器：无网络，按 ``round`` 返回种子 findings。

    ``scenario``：``{round: [finding, ...]}``；某轮没种子 ⇒ 空（PASS）。
    用于单测、降级链路与「无 .git / 无网络」的 lite 形态。
    """

    def __init__(self, scenario: dict | None = None):
        self.scenario = scenario or {}

    def run(self, request: ReviewRequest, *, model: str, **_kwargs) -> ReviewResult:
        findings = list(self.scenario.get(request.round, []))
        verdict = "PASS" if not any(
            severity_rank(f.get("severity")) >= severity_rank("medium")
            for f in findings
        ) else "CHANGES_REQUESTED"
        return ReviewResult(
            findings=findings,
            verdict=verdict,
            model=model or "mock",
            raw=json.dumps({"findings": findings, "verdict": verdict}),
        )


class ClaudeAdapter:
    """Anthropic Messages API（``/v1/messages``）。"""

    def __init__(self, base_url: str, auth_token: str, *, max_tokens: int = 4096):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.max_tokens = max_tokens

    def run(self, request: ReviewRequest, *, model: str) -> ReviewResult:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "content-type": "application/json",
            "x-api-key": self.auth_token,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": f"{request.prompt}\n\n{request.context}"}],
        }
        try:
            doc = _http_json(url, headers, payload)
        except AdapterError as exc:
            return ReviewResult(model=model, error=str(exc), error_kind=exc.kind)
        if not isinstance(doc, dict):
            return ReviewResult(
                model=model, error="HTTP 响应不是 JSON 对象", error_kind="other"
            )
        # Anthropic 形状：content 是 [{type:text|thinking, text|thinking}, ...]
        blocks = doc.get("content")
        if not isinstance(blocks, list):
            return ReviewResult(
                model=model, error="HTTP 响应 content 不是数组", error_kind="other"
            )
        texts = [
            block.get("text")
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ]
        raw = "\n".join(texts)
        findings, verdict, err = parse_review_output(raw)
        usage = doc.get("usage")
        if not isinstance(usage, dict):
            usage = None
        return ReviewResult(
            findings=findings,
            verdict=verdict,
            model=model,
            raw=raw,
            error=err,
            # 解析失败是**通路失败**，不是「零 findings 的 PASS」——否则一个
            # 畸形输出会被编排器当成收敛。orchestrator 据此走回落 / BLOCKED。
            error_kind="parse" if err else None,
            usage=usage,
        )


class CodexAdapter:
    """OpenAI ``chat/completions``（heyroute 的 ``/v1`` 端点同形状）。"""

    def __init__(self, base_url: str, auth_token: str, *, max_tokens: int = 4096):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.max_tokens = max_tokens

    def run(self, request: ReviewRequest, *, model: str) -> ReviewResult:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
        }
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": f"{request.prompt}\n\n{request.context}"}],
        }
        try:
            doc = _http_json(url, headers, payload)
        except AdapterError as exc:
            return ReviewResult(model=model, error=str(exc), error_kind=exc.kind)
        if not isinstance(doc, dict):
            return ReviewResult(
                model=model, error="HTTP 响应不是 JSON 对象", error_kind="other"
            )
        try:
            content = doc["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = ""
        raw = content if isinstance(content, str) else ""
        findings, verdict, err = parse_review_output(raw)
        usage = doc.get("usage")
        if not isinstance(usage, dict):
            usage = None
        # OpenAI 形状的 usage 键名换算成统一键，供 cost_usd 用。
        if usage and "input_tokens" not in usage and "prompt_tokens" in usage:
            usage = {
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
            }
        return ReviewResult(
            findings=findings,
            verdict=verdict,
            model=model,
            raw=raw,
            error=err,
            error_kind="parse" if err else None,
            usage=usage,
        )


def resolve_auth_token(role: dict) -> str:
    """一个角色可用的 auth token；**构造适配器与实际请求共用这一处**。

    顺序：内联 ``auth_token`` → ``auth_env``；只有角色显式声明
    ``allow_host_auth_fallback: true`` 时才再尝试 ``ANTHROPIC_AUTH_TOKEN`` /
    ``ANTHROPIC_API_KEY``。

    宿主 token **不能默认跨端点复用**：`reviewerA` 的 `auth_env` 缺失时，把宿主的
    Anthropic token 发往 heyroute/deepseek 属于跨信任域凭据复用。需要宿主兜底的角色
    （例如 deepseek 回落通路）必须在角色配置里显式打开开关。
    """
    token = (role.get("auth_token") or "").strip()
    if token:
        return token
    env_name = (role.get("auth_env") or "").strip()
    if env_name and os.environ.get(env_name, "").strip():
        return os.environ[env_name].strip()
    if role.get("allow_host_auth_fallback") is True:
        for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
            if os.environ.get(name, "").strip():
                return os.environ[name].strip()
    return ""


def build_adapter(adapter: str, *, role: dict, scenario: dict | None = None):
    """按角色配置构造适配器实例。``adapter`` ∈ ``claude`` / ``codex`` / ``mock``。

    auth 走 ``resolve_auth_token``（与 orchestrator 的预检、回落判定同口径）；
    mock 不需要 auth。
    """
    if adapter == "mock":
        return MockAdapter(scenario=scenario)

    token = resolve_auth_token(role)
    base_url = role.get("base_url") or ""
    if adapter == "claude":
        return ClaudeAdapter(base_url, token)
    if adapter == "codex":
        return CodexAdapter(base_url, token)
    raise ValueError(f"未知适配器：{adapter!r}（可选 claude/codex/mock）")
