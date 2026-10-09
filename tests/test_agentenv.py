"""交互层侧的取值策略：run id 与模板目录。

Claude Code 没有稳定的「当前 run id」注入点，也没有固定的插件安装位置，
所以适配器与工具必须按**同一套规则**取值。把这些规则写成可执行的规范并用测试
钉住，各 host 的适配器才不会各编一套。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from witnessloop import agentenv as A

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- run id


def test_generated_ids_never_collide_between_roles():
    """**确定性**保证：即使时间戳与随机数完全相同，两个角色的 id 也不同。

    把 now/token 都钉死是关键——否则「不同」可能只是随机数碰巧不一样，
    测不出「role 编进了 id」这条真正的保证。
    """
    fixed = {"now": datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc), "token": "same"}
    assert A.generate_run_id("building", "reviewer", **fixed) != A.generate_run_id(
        "building", "author", **fixed
    )


def test_generated_ids_are_unique_across_many_calls():
    ids = {A.generate_run_id("building", "reviewer") for _ in range(200)}
    assert len(ids) == 200


def test_generated_id_shape():
    rid = A.generate_run_id(
        "building",
        "reviewer",
        now=datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc),
        token="abc123",
    )
    assert rid == "building-reviewer-20261009T120000Z-abc123"


def test_env_run_id_is_adopted():
    env = {A.RUN_ID_ENV: "run-from-env"}
    assert A.resolve_run_id("building", "reviewer", env=env) == "run-from-env"


def test_role_specific_env_wins_over_the_shared_one():
    env = {
        A.RUN_ID_ENV: "shared",
        A.role_env_name("reviewer"): "rev-1",
        A.role_env_name("author"): "auth-1",
    }
    assert A.resolve_run_id("building", "reviewer", env=env) == "rev-1"
    assert A.resolve_run_id("building", "author", env=env) == "auth-1"


def test_resolution_falls_back_to_generation():
    rid = A.resolve_run_id("building", "reviewer", env={})
    assert rid.startswith("building-reviewer-")


def test_blank_env_value_is_ignored():
    assert A.resolve_run_id("s", "reviewer", env={A.RUN_ID_ENV: "   "}).startswith(
        "s-reviewer-"
    )


def test_shared_env_alone_gives_both_roles_the_same_id():
    """文档化的footgun：只设共享变量时两个角色相同——门禁会拒。

    这正是「审阅者必须另开 run」的语义：想让两个角色不同，就得给它们各自的
    环境（或角色专用变量）。本条把该行为钉住，免得有人以为共享变量能做区分。
    """
    env = {A.RUN_ID_ENV: "same"}
    assert A.resolve_run_id("s", "reviewer", env=env) == A.resolve_run_id(
        "s", "author", env=env
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
