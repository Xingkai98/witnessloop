"""路径归一化与 glob 匹配（受保护路径用）。

用自带的 ``**`` 感知匹配，而不是 ``fnmatch``：``fnmatch`` 的 ``*`` 会跨 ``/``，
``openspec/specs/**`` 这类前缀约束会失效。``**`` 跨分隔符，``*``/``?`` 不跨。
"""

from __future__ import annotations

import re


def normalize(path: str) -> str:
    """统一成正斜杠、去掉前导 ``./``（Windows 反斜杠也是已知坑，见 design §9）。"""
    return path.replace("\\", "/").lstrip("./")


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
