"""路径归一化与 glob 匹配（受保护路径用）。

用自带的 ``**`` 感知匹配，而不是 ``fnmatch``：``fnmatch`` 的 ``*`` 会跨 ``/``，
``openspec/specs/**`` 这类前缀约束会失效。``**`` 跨分隔符，``*``/``?`` 不跨。
"""

from __future__ import annotations

import re
from pathlib import Path


def normalize(path: str) -> str:
    """统一成正斜杠、去掉前导 ``./``（Windows 反斜杠也是已知坑，见 design §9）。

    注意别用 ``str.lstrip("./")``：它按**字符集**剥离，会把 ``.witnessloop/x``
    削成 ``witnessloop/x``，让不变集静默失效。
    """
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    pat = normalize(pattern)
    out: list[str] = []
    i, n = 0, len(pat)
    while i < n:
        ch = pat[i]
        if ch == "*":
            if i + 1 < n and pat[i + 1] == "*":
                j = i + 2
                if j < n and pat[j] == "/":
                    out.append("(?:.*/)?")  # `**/` 也匹配零层目录
                    i = j + 1
                else:
                    out.append(".*")
                    i = j
                continue
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(path: str, pattern: str) -> bool:
    return bool(glob_to_regex(pattern).match(normalize(path)))


def matches_any(path: str, patterns) -> bool:
    return any(matches(path, p) for p in patterns)


def is_within(path: str | Path, parent: str | Path) -> bool:
    """``path`` 解析后是否落在 ``parent`` 之内。

    用于拒绝「台账/report_path 指向仓根之外」——manifest 是提交进仓的，
    agent 可写，所以任何随后会被 unlink/读取的路径都必须先过这道闸。
    ``resolve()`` 会展开 ``..`` 与符号链接，两条越界路径都拦得住。
    """
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
    except (ValueError, OSError):
        return False
    return True
