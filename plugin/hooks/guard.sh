#!/usr/bin/env bash
# witnessloop 的 PreToolUse 守卫（**只接线**）。
#
# 把 CC 的工具事件映射成 host-agnostic 的 `witnessloop guard`：
#   stdin JSON（含 tool_input.file_path / cwd） →  `witnessloop guard --path …`
#
# 退出码**直传**：guard 的 2 = 拦（CC 视 exit 2 为 block，stderr 回喂给模型）。
# 抽不到路径 → exit 0（不拦）：守卫是「防遗忘」，不是防对抗（见 README）。
#
# ⚠️ 本 shim **不带** witnessloop 二进制——装了 plugin 还要装 CLI（否则命令找不到，
#    以非 2 退出 ⇒ CC 视为不阻塞 ⇒ 静默 fail-open）。
set -u

payload="$(cat)"

# 用 python3 抽字段（witnessloop 本身就是 python 工具，宿主上 python3 是既有前提）。
field() {
  printf '%s' "$payload" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print((d.get('tool_input') or {}).get('$1') or '')" \
    2>/dev/null || true
}

path="$(field file_path)"
if [ -z "${path:-}" ]; then
  exit 0
fi

root="$(printf '%s' "$payload" | python3 -c \
  "import json,sys; print(json.load(sys.stdin).get('cwd') or '')" 2>/dev/null || true)"
[ -n "${root:-}" ] || root="$PWD"

witnessloop guard --root "$root" --path "$path"
