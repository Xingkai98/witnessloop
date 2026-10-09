"""文档漂移守卫：自述里的动词面必须与实际 CLI 一致。

M2 把动词面从 3 个扩到 4 个（+`manifest build`）后，design / README / 包自述一度
仍写「3 个动词」，README 甚至**自己和自己**矛盾（上面说 M2 尚未开始，下面已在演示
`manifest build` 与 plugin 用法）。对一个「以不让文档漂移为核心卖点」的项目，
这处漂移本身就是缺陷——所以把它钉成测试。
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: 自述动词面的地方。CLI 的真实动词面见 tests/test_cli.py。
VERB_SURFACE_DOCS = ("docs/design.md", "README.md", "src/witnessloop/__init__.py")

STALE_CLAIMS = ("3 个动词", "三个动词", "三动词", "2 动词", "2 个动词")


@pytest.mark.parametrize("relpath", VERB_SURFACE_DOCS)
def test_no_stale_verb_count(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    for claim in STALE_CLAIMS:
        assert claim not in text, f"{relpath} 仍写「{claim}」，与 CLI 实际动词面不符"


def test_design_documents_the_manifest_build_verb():
    """design 是权威——新动词必须在设计里有出处，不能只活在 CLI 和 README 里。"""
    assert "manifest build" in (REPO_ROOT / "docs/design.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("relpath", ("README.md", "docs/design.md"))
def test_docs_name_all_four_verbs(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    for verb in ("init", "check", "uninit", "manifest build"):
        assert verb in text, f"{relpath} 没提到动词 {verb}"
