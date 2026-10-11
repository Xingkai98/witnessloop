#!/usr/bin/env bash
# witnessloop 的 PreToolUse 守卫（**只接线**）。
#
# 把 CC 的工具事件映射成 host-agnostic 的 `witnessloop guard`：
#   stdin JSON（含 tool_input.file_path / cwd） →  `witnessloop guard --path …`
#
# **退出码映射**（不直传！）：guard 的 1（拦住）→ CC 的 2（block）。
# 其余一律 0（放行）。直传会把「用法错误 / 旧版 CLI」的 2 也当成 block。
# 抽不到路径 → 0（不拦）：守卫是「防遗忘」，不是防对抗（见 README）。
#
# ⚠️ 本 shim **不带** witnessloop 二进制——装了 plugin 还要装 CLI。
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
status=$?

# guard 的 1 = 拦住 → 映射成 CC 的 block（exit 2）。
# **其余（含 2 = 用法错误 / 旧版 CLI 的 invalid choice）一律放行**——
# 否则旧版 CLI 会把每个 Write/Edit 都拦下（回归审阅 Issue 3）。
if [ "$status" -eq 1 ]; then
  exit 2
fi
exit 0

