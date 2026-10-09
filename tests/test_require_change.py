"""① `require_change_for`：改了代码就必须挂一个 change 目录。

堵的是「不建 change 目录就绕过」——在此之前 `check` 只保证「**如果你**动了
change 目录/受保护路径，它要齐备」，于是最省事的绕过办法是什么都不建：
一个只改 `src/` 的 PR 直接放行。
"""

from __future__ import annotations

import json
from pathlib import Path

from witnessloop import constants as C

from conftest import commit_all, git
from helpers import check, commit_content, commit_evidence, write_artifact


def _commit(repo: Path, rel: str, body: str, message: str) -> None:
    write_artifact(repo, rel, body)
    commit_all(repo, message)


def test_source_change_without_change_dir_is_rejected(gated: Path, cli):
    _commit(gated, "src/app.py", "x = 1\n", "只改代码，没建 change")

    code, _, err = check(gated, cli)

    assert code == C.EXIT_FAIL
    assert "src/app.py" in err  # 点名命中的源码文件
    assert "require_change_for" in err
    assert "没有任何 change 目录" in err


def test_source_change_with_change_dir_passes(gated: Path, cli):
    commit_content(gated, "add-x", spec_writes=(("src/app.py", "x = 1\n"),))
    commit_evidence(gated, "add-x")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_docs_only_change_passes(gated: Path, cli):
    """`docs/**` 不在默认 require_change_for 里 —— 不误伤纯文档改动。"""
    _commit(gated, "docs/notes.md", "# 笔记\n", "只改文档")

    code, out, err = check(gated, cli)
    assert code == C.EXIT_PASS, err


def test_default_policy_declares_require_change_for(repo: Path, cli, read_json):
    cli("init", "--root", str(repo))
    policy = read_json(repo / C.POLICY_PATH)
    patterns = policy["require_change_for"]

    assert isinstance(patterns, list) and patterns
    # 覆盖常见源码目录
    assert "src/**" in patterns
    # 别太激进：纯文档目录不该被纳进来
    assert not any(p.startswith("docs") for p in patterns)


def test_require_change_for_is_configurable(repo: Path, cli, read_json):
    """repo-agnostic 参数化轴：目标仓可以换成自己的路径。"""
    cli("init", "--root", str(repo))
    policy_path = repo / C.POLICY_PATH
    doc = read_json(policy_path)
    doc["require_change_for"] = ["infra/**"]
    policy_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    commit_all(repo, "换成 infra/**")
    git(repo, "checkout", "-q", "-b", "feature")

    # src/ 已不在名单里 → 放行
    _commit(repo, "src/app.py", "x = 1\n", "改 src，不在名单")
    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err

    # infra/ 在名单里 → 拦下
    _commit(repo, "infra/main.tf", "# infra\n", "改 infra，没建 change")
    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "infra/main.tf" in err


def test_empty_require_change_for_disables_the_rule(repo: Path, cli, read_json):
    cli("init", "--root", str(repo))
    policy_path = repo / C.POLICY_PATH
    doc = read_json(policy_path)
    doc["require_change_for"] = []
    policy_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    commit_all(repo, "显式关掉")
    git(repo, "checkout", "-q", "-b", "feature")

    _commit(repo, "src/app.py", "x = 1\n", "改 src")

    code, out, err = check(repo, cli)
    assert code == C.EXIT_PASS, err


def test_deleting_source_without_change_dir_is_rejected(repo: Path, cli):
    """删代码同样是「改了代码」。"""
    cli("init", "--root", str(repo))
    write_artifact(repo, "src/app.py", "x = 1\n")
    commit_all(repo, "main 上先有源码")
    git(repo, "checkout", "-q", "-b", "feature")

    (repo / "src" / "app.py").unlink()
    commit_all(repo, "删掉源码，没建 change")

    code, _, err = check(repo, cli)
    assert code == C.EXIT_FAIL
    assert "src/app.py" in err


def test_onboarding_pr_itself_is_not_blocked(repo: Path, cli):
    """接入 PR 只写 .witnessloop/** 与 .github/**，不在 require_change_for 里。"""
    cli("init", "--root", str(repo))
    commit_all(repo, "接入 witnessloop")

    code, out, err = cli(
        "check", "--root", str(repo), "--base", "HEAD~1", "--head", "HEAD"
    )
    assert code == C.EXIT_PASS, err
