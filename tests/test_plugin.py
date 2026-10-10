"""E2–E4：CC 适配器（plugin/）。

适配器只做**接线**：把自己的命令入口接到 host 中立模板上。三条硬要求：
物理分离（不内联模板正文）、只读无状态（不持有自己的状态文件）、
收尾调 `witnessloop manifest build`。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN = REPO_ROOT / "plugin"
TEMPLATES = REPO_ROOT / "templates"

EXPECTED_FILES = {
    ".claude-plugin/plugin.json",
    "commands/grill.md",
    "commands/review-loop.md",
    "README.md",
}

COMMANDS = ("grill", "review-loop")

#: 模板正文里出现这串长度（去空白后）的逐字复制，就算「内联算法」。
MIN_INLINED_RUN = 60

_FENCE = re.compile(r"```.*?```", re.DOTALL)


def _prose(path: Path) -> str:
    """去掉围栏代码块并归一空白——比对**算法正文**，命令行不算正文。"""
    text = _FENCE.sub(" ", path.read_text(encoding="utf-8"))
    return " ".join(text.split())


def _longest_shared_run(a: str, b: str) -> int:
    if not a or not b:
        return 0
    n = min(MIN_INLINED_RUN, len(a), len(b))
    grams = {a[i : i + n] for i in range(len(a) - n + 1)}
    best = 0
    for i in range(len(b) - n + 1):
        if b[i : i + n] in grams:
            # 命中即说明至少有这么长的共同段；再往后量一点作证据
            run = n
            while (
                i + run < len(b)
                and i + run < len(a)
                and b[i : i + run + 1] in a
            ):
                run += 1
            best = max(best, run)
    return best


# ---------------------------------------------------------------- 结构


def test_plugin_file_inventory_is_exactly_expected():
    """只有一个 manifest、两条命令、一个说明——**没有状态文件**（E4）。"""
    found = {
        p.relative_to(PLUGIN).as_posix()
        for p in PLUGIN.rglob("*")
        if p.is_file()
    }
    assert found == EXPECTED_FILES, f"多出/缺少：{found ^ EXPECTED_FILES}"


def test_plugin_manifest_is_valid():
    doc = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text("utf-8"))
    assert doc["name"] == "witnessloop"
    assert doc["description"].strip()
    assert doc["version"].strip()


@pytest.mark.parametrize("command", COMMANDS)
def test_command_file_exists(command: str):
    path = PLUGIN / "commands" / f"{command}.md"
    assert path.is_file()
    assert path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------- E1 物理分离


@pytest.mark.parametrize("command", COMMANDS)
def test_adapter_does_not_inline_the_template(command: str):
    """适配器不得复制模板正文——超过阈值的逐字段即算内联。"""
    adapter = _prose(PLUGIN / "commands" / f"{command}.md")
    template = _prose(TEMPLATES / f"{command}.md")
    shared = _longest_shared_run(template, adapter)
    assert shared < MIN_INLINED_RUN, (
        f"{command} 适配器内联了模板正文（共同段 {shared} 字符 ≥ {MIN_INLINED_RUN}）"
    )


@pytest.mark.parametrize("command", COMMANDS)
def test_adapter_points_at_the_template(command: str):
    text = (PLUGIN / "commands" / f"{command}.md").read_text(encoding="utf-8")
    assert f"templates/{command}.md" in text


# ---------------------------------------------------------------- E4 只读无状态


@pytest.mark.parametrize("command", COMMANDS)
def test_adapter_declares_readonly_and_stateless(command: str):
    text = (PLUGIN / "commands" / f"{command}.md").read_text(encoding="utf-8")
    assert "只读" in text
    assert "无状态" in text or "不得持有" in text
    assert "manifest" in text  # 状态一律以 manifest 为准


# ---------------------------------------------------------------- 命令语义


def test_grill_adapter_hands_off_to_the_user():
    text = (PLUGIN / "commands" / "grill.md").read_text(encoding="utf-8")
    assert "停轮" in text or "确认" in text
    assert "reviews/grill-review.md" in text


def test_review_loop_adapter_calls_manifest_build():
    text = (PLUGIN / "commands" / "review-loop.md").read_text(encoding="utf-8")
    assert "witnessloop manifest build" in text
    assert "--reviewer-run-id" in text and "--author-run-id" in text


def test_grill_adapter_stops_for_the_user_only_after_convergence():
    """(A) 时序落在适配器上的部分：命令不再「跨多轮等用户答复」，
    而是**审阅者跑完 + 对抗收敛之后，才**把 Open Questions 一次性交给用户。"""
    text = (PLUGIN / "commands" / "grill.md").read_text(encoding="utf-8")
    assert "一次性" in text
    assert "才" in text
    # 对抗验证与整合回 design.md 也在接线里点到
    assert "grill-adversarial" in text
    assert "Pre-Implementation Review" in text


def test_grill_adapter_does_not_hold_a_round_for_a_fact_lookup():
    """事实在查时不要整体卡住本轮——只有它下游的问题顺延。"""
    text = (PLUGIN / "commands" / "grill.md").read_text(encoding="utf-8")
    assert "不要阻塞" in text or "不整体" in text


def test_review_loop_adapter_handles_a_blocked_verdict():
    """R1 落在适配器上的部分：BLOCKED 要停、报告、不自行修复。"""
    text = (PLUGIN / "commands" / "review-loop.md").read_text(encoding="utf-8")
    assert "BLOCKED" in text
    assert "不自行修复" in text


def test_review_loop_adapter_is_batch_aware_and_syncs_docs():
    text = (PLUGIN / "commands" / "review-loop.md").read_text(encoding="utf-8")
    assert "后续批" in text
    assert "审阅修复" in text


def test_review_loop_adapter_states_the_bounded_rounds():
    text = (PLUGIN / "commands" / "review-loop.md").read_text(encoding="utf-8")
    assert "轮" in text and ("封顶" in text or "上限" in text)


@pytest.mark.parametrize("command", COMMANDS)
def test_adapters_pass_the_run_id_strategy_through(command: str):
    """CC 侧怎么设/传 run id——策略在模板里，适配器负责把它接到环境变量上。"""
    text = (PLUGIN / "commands" / f"{command}.md").read_text(encoding="utf-8")
    assert "WITNESSLOOP_RUN_ID" in text
    assert "--reviewer-run-id" in text or "--author-run-id" in text


@pytest.mark.parametrize("command", COMMANDS)
def test_adapters_let_the_templates_dir_be_overridden(command: str):
    """plugin/ 被单独拷走时，靠这个环境变量把模板位置指回去。"""
    text = (PLUGIN / "commands" / f"{command}.md").read_text(encoding="utf-8")
    assert "WITNESSLOOP_TEMPLATES_DIR" in text
    assert "${CLAUDE_PLUGIN_ROOT}/../templates" in text  # 未设时的回落


def test_readme_documents_both_environment_variables():
    text = (PLUGIN / "README.md").read_text(encoding="utf-8")
    assert "WITNESSLOOP_TEMPLATES_DIR" in text
    assert "WITNESSLOOP_RUN_ID" in text


def test_docs_say_git_or_local_distribution():
    """分发按 design §4：git / 本地 `--plugin-dir`，不上 marketplace。"""
    text = (PLUGIN / "README.md").read_text(encoding="utf-8").lower()
    assert "--plugin-dir" in text
    assert "marketplace" in text  # 说明「不上」


def test_readme_accounts_for_itself_in_the_inventory():
    """回归 M2 §4-7：自述说「只有 manifest 和两条命令」，漏了自己这个 README。"""
    text = (PLUGIN / "README.md").read_text(encoding="utf-8")
    assert "README" in text
