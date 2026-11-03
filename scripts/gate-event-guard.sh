#!/bin/sh
# issue #48：reusable gate 只接受 pull_request 事件。
#
# 本门禁按 **PR 区间**设计：base 是目标分支、head 是 PR head，区间里恒有变更。
# push / schedule 触发时 github.base_ref 为空，base 可能不可解析、也可能与 head 相同；
# 零变更按 issue #45 是 EXIT_EMPTY(5)——「无操作、非通过」，不是门禁故障，更不是通过。
#
# 确实需要让零变更通过时，必须在 check 命令上显式加 --allow-empty；
# 不要为了抹掉这条红而默认加上它（那等于放弃「区间内有变更」这个前提）。

set -eu

EVENT="${GITHUB_EVENT_NAME:-}"

case "$EVENT" in
  pull_request)
    echo "::notice::witnessloop gate：事件=pull_request（PR 区间，继续）"
    exit 0
    ;;
  "")
    echo "::error::witnessloop gate 无法判断事件类型：GITHUB_EVENT_NAME 为空（本门禁只接受 pull_request）。" >&2
    ;;
  *)
    echo "::error::witnessloop gate 只接受 pull_request 事件（当前：${EVENT}）。" >&2
    ;;
esac

echo "  本门禁按 PR 区间设计：base 是目标分支、head 是 PR head，区间里恒有变更。" >&2
echo "  push / schedule 触发时 base 与 head 通常是同一个提交；零变更按 issue #45 是" >&2
echo "  「无操作（EXIT_EMPTY=5）」——不是通过，也不是一条门禁故障。" >&2
echo "  确实需要零变更放行时，请在 check 命令上显式加 --allow-empty；" >&2
echo "  不要为了抹掉这条红而默认加上它（那等于放弃「区间内有变更」这个前提）。" >&2
exit 1
