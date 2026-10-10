"""交互层侧的取值策略：run id 与模板目录。

Claude Code 没有稳定的「当前 run id」注入点，所以适配器与工具必须按**同一套规则**
取值。把规则写成可执行的规范并用测试钉住，各 host 的适配器才不会各编一套。

run id 两条环境变量路径**保留**（真 run id 优先）；**兜底是确定性的**（#3）——
`<stage>-<role>-<anchor>`，同输入 → 同 id。原来的时间戳+随机兜底会让同一个逻辑 run
重复 `manifest build` 产出不一致的 manifest（不幂等）。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import agentenv as A

REPO_ROOT = Path(__file__).resolve().parent.parent

ANCHOR = A.default_run_anchor("add-retry", "0123456789abcdef0123456789abcdef01234567")


# ---------------------------------------------------------------- run id


def test_default_anchor_carries_change_and_revision():
    """Q1：摘要**≥12 位**——太短会丧失 revision 区分力。"""
    head = "0123456789abcdef0123456789abcdef01234567"
    anchor = A.default_run_anchor("add-retry", head)
    assert "add-retry" in anchor
    assert head[:12] in anchor
    assert anchor == A.default_run_anchor("add-retry", head)


def test_default_anchor_uses_at_least_twelve_hex_chars_of_the_revision():
    head = "abcdef0123456789abcdef0123456789abcdef01"
    digest = A.default_run_anchor("c", head).rsplit("-", 1)[-1]
    assert digest == head[:12]
    assert len(digest) >= 12


def test_same_input_gives_the_same_id():
    """#3 的核心：兜底**确定性**——同 stage/role/anchor → 同 id。"""
    first = A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env={})
    second = A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env={})
    assert first == second


def test_generated_ids_never_collide_between_roles():
    """确定性兜底下 `role` 仍编进 id——两角色**必然不同**（门禁硬校验）。"""
    assert A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env={}) != (
        A.resolve_run_id("building", "author", anchor=ANCHOR, env={})
    )


def test_generated_id_shape():
    assert (
        A.generate_run_id("building", "reviewer", "add-retry-01234567")
        == "building-reviewer-add-retry-01234567"
    )


def test_different_anchor_gives_a_different_id():
    other = A.default_run_anchor("add-retry", "ffffffffffffffff")
    assert A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env={}) != (
        A.resolve_run_id("building", "reviewer", anchor=other, env={})
    )


def test_env_run_id_is_adopted():
    env = {A.RUN_ID_ENV: "run-from-env"}
    assert A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env=env) == (
        "run-from-env"
    )


def test_role_specific_env_wins_over_the_shared_one():
    env = {
        A.RUN_ID_ENV: "shared",
        A.role_env_name("reviewer"): "rev-1",
        A.role_env_name("author"): "auth-1",
    }
    assert A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env=env) == "rev-1"
    assert A.resolve_run_id("building", "author", anchor=ANCHOR, env=env) == "auth-1"


def test_resolution_falls_back_to_generation():
    rid = A.resolve_run_id("building", "reviewer", anchor=ANCHOR, env={})
    assert rid.startswith("building-reviewer-")
    assert ANCHOR in rid


def test_blank_env_value_is_ignored():
    rid = A.resolve_run_id("s", "reviewer", anchor=ANCHOR, env={A.RUN_ID_ENV: "   "})
    assert rid.startswith("s-reviewer-")


def test_shared_env_alone_gives_both_roles_the_same_id():
    """文档化的 footgun：只设共享变量时两个角色相同——门禁会拒。

    这正是「审阅者必须另开 run」的语义：想让两个角色不同，就得给它们各自的
    环境（或角色专用变量）。本条把该行为钉住，免得有人以为共享变量能做区分。
    """
    env = {A.RUN_ID_ENV: "same"}
    assert A.resolve_run_id("s", "reviewer", anchor=ANCHOR, env=env) == (
        A.resolve_run_id("s", "author", anchor=ANCHOR, env=env)
    )


# ---------------------------------------------------------------- 模板目录


def test_templates_dir_defaults_to_the_repo_templates():
    assert A.resolve_templates_dir(env={}) == REPO_ROOT / "templates"


def test_templates_dir_env_override(tmp_path):
    assert A.resolve_templates_dir(
        env={A.TEMPLATES_DIR_ENV: str(tmp_path)}
    ) == tmp_path


def test_templates_dir_blank_env_falls_back():
    assert A.resolve_templates_dir(
        env={A.TEMPLATES_DIR_ENV: "   "}
    ) == REPO_ROOT / "templates"


def test_templates_dir_expands_user_home(monkeypatch, tmp_path):
    """`~` 在模板路径里该展开——这是人手工设的变量，不是 git 输出的路径。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    assert A.resolve_templates_dir(
        env={A.TEMPLATES_DIR_ENV: "~/my-templates"}
    ) == (tmp_path / "my-templates").resolve()
