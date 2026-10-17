"""issue #31（用户裁定 **B**）：搬移形状的 `D` finding **可行动** —— 判定**不变**，只改文案。

三条承重不变量（`design.md §2 D1` / `§7`）：

1. **判定零改动**：findings 的**有无 / 路径 / 条数**与退出码，全部与改动前相同；
2. **示例必须真能用**：文案里那个 JSON 示例喂给 `events.covers` 必须为**真**；
3. **示例的事件类型取自 policy**（不硬编码某个接入方 policy 里的类型名）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from witnessloop import constants as C
from witnessloop import contract, events as events_mod
from witnessloop import gitutil, policy as policy_mod

from conftest import commit_all, git
from helpers import change_dir, commit_content, commit_evidence, init_wired

CHANGES = C.DEFAULT_CHANGES_ROOT
ARCHIVE_REL = f"{CHANGES}/{C.ARCHIVE_DIR_NAME}"
CHANGE = "add-retry"
DAY = "2026-10-14"
ARCHIVED = f"{DAY}-{CHANGE}"
EVENTS = "workflow-events.jsonl"


def _event_line(path: str, body: str = "旧内容") -> str:
    return json.dumps(
        {
            "schema": "witnessloop/event@v1",
            "event_type": "protected_path_write",
            "artifact_path": path,
            "reason": body,
            "approved_by": "tester",
        },
        ensure_ascii=False,
    ) + "\n"


def _issue31_shape(repo: Path, cli) -> str:
    """复刻 issue #31：change 整体搬进 archive，但 `workflow-events.jsonl` 走 **`D` + `A`**。

    ——那个文件在搬移时被**改写**过（内容大改）⇒ git 配不上 rename ⇒ 旧路径是 `D`、新路径是 `A`。
    返回那条 `D` 的路径（仓库相对的 posix 路径）。
    """
    init_wired(repo, cli)
    change_dir(repo, CHANGE).mkdir(parents=True, exist_ok=True)
    (change_dir(repo, CHANGE) / EVENTS).write_text(
        _event_line(f"{CHANGES}/{CHANGE}/{EVENTS}"), encoding="utf-8"
    )
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)          # manifest 绑当时的 HEAD（晚于内容）
    git(repo, "checkout", "-q", "-b", "feature")

    old = f"{CHANGES}/{CHANGE}/{EVENTS}"
    git(repo, "rm", "-q", old)             # ⇒ 暂存 `D old`（unlink 不暂存，`git mv` 会报 bad source）
    (repo / ARCHIVE_REL).mkdir(parents=True, exist_ok=True)
    git(repo, "mv", f"{CHANGES}/{CHANGE}", f"{ARCHIVE_REL}/{ARCHIVED}")
    # 全新内容（与旧文件毫无相似度）⇒ git 不配对 ⇒ `A` 而不是 `R`
    (repo / ARCHIVE_REL / ARCHIVED / EVENTS).write_text(
        _event_line(f"{ARCHIVE_REL}/{ARCHIVED}/{EVENTS}", body="搬移后重写过的内容") * 5,
        encoding="utf-8",
    )
    commit_all(repo, "归档（其中一个文件被改写过 ⇒ D + A）")
    return old


def _check(repo: Path, cli):
    return cli("check", "--root", str(repo), "--base", "main", "--head", "HEAD")


# ------------------------------------------------------------------ 判定不变（承重）

def test_the_move_shaped_D_still_reddens_exactly_once(repo: Path, cli):
    """**判定不变**：issue #31 的形态仍然红，且**只有这一条**、路径就是那条 `D`。"""
    old = _issue31_shape(repo, cli)

    code, _, err = _check(repo, cli)

    assert code == C.EXIT_FAIL
    assert err.count("受保护路径被写入") == 1, err
    assert f"1. {old}：" in err or old in err


def test_a_pure_rename_archive_is_still_green(repo: Path, cli):
    """纯 `R100` 搬移（本仓第一次归档的形态）⇒ 仍然 0 findings、**不**需要任何事件。"""
    init_wired(repo, cli)
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)
    git(repo, "checkout", "-q", "-b", "feature")
    (repo / ARCHIVE_REL).mkdir(parents=True, exist_ok=True)
    git(repo, "mv", f"{CHANGES}/{CHANGE}", f"{ARCHIVE_REL}/{ARCHIVED}")
    commit_all(repo, "纯 move 归档")

    code, out, err = _check(repo, cli)

    assert code == C.EXIT_PASS, err
    assert "通过 ✓" in out
    assert "受保护路径被写入" not in err


def test_a_plain_deletion_is_still_red(repo: Path, cli):
    """单独删一个受保护文件 ⇒ 照旧红（**与改动前同结论**），且**不**出现搬移诊断。"""
    init_wired(repo, cli)
    change_dir(repo, CHANGE).mkdir(parents=True, exist_ok=True)
    (change_dir(repo, CHANGE) / EVENTS).write_text(
        _event_line(f"{CHANGES}/{CHANGE}/{EVENTS}"), encoding="utf-8"
    )
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)
    git(repo, "checkout", "-q", "-b", "feature")
    git(repo, "rm", "-q", f"{CHANGES}/{CHANGE}/{EVENTS}")
    commit_all(repo, "只删事件文件")

    code, _, err = _check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err
    assert "搬移的一半" not in err, "没有同相对子路径的 A ⇒ 不该给搬移诊断"


# ------------------------------------------------------------------ 诊断（只改文案）

def test_the_finding_names_the_counterpart_and_the_one_line_remedy(repo: Path, cli):
    old = _issue31_shape(repo, cli)

    _, _, err = _check(repo, cli)

    new = f"{ARCHIVE_REL}/{ARCHIVED}/{EVENTS}"
    assert "搬移的一半" in err
    assert old in err and new in err, "诊断必须点名**两侧的实际路径**"
    assert "同一个 PR" in err and "一条" in err


def test_the_embedded_json_example_is_actually_usable(repo: Path, cli):
    """**示例必须真能用**：把它解析出来喂 `events.covers` ⇒ 真。"""
    old = _issue31_shape(repo, cli)
    _, _, err = _check(repo, cli)

    blob = re.search(r"\{.*\}", err)
    assert blob, f"消息里没有 JSON 示例：{err}"
    doc = json.loads(blob.group(0))
    assert doc["artifact_path"] == old, "示例的 artifact_path 必须是那条 D 的**真实路径**"

    pol = policy_mod.load_policy(repo)
    example_path = repo / "example-events.jsonl"
    example_path.write_text(blob.group(0) + "\n", encoding="utf-8")
    loaded = events_mod.load_events_file(example_path)
    assert len(loaded) == 1
    assert events_mod.covers(loaded[0], old, pol.protected_write_event_types), (
        "示例写成的事件必须能通过 covers——否则「可直接复制」是假的"
    )


def test_appending_the_example_in_the_same_diff_turns_it_green(repo: Path, cli):
    """照文案在**同一次 diff** 里补一行事件（写进归档后那份）⇒ `check：通过 ✓`。"""
    _issue31_shape(repo, cli)
    _, _, err = _check(repo, cli)
    blob = re.search(r"\{.*\}", err).group(0)

    target = repo / ARCHIVE_REL / ARCHIVED / EVENTS
    target.write_text(target.read_text(encoding="utf-8") + blob + "\n", encoding="utf-8")
    commit_all(repo, "补一行解释事件（同一个 PR）")

    code, out, _ = _check(repo, cli)

    assert code == C.EXIT_PASS, out
    assert "通过 ✓" in out


def test_the_example_type_comes_from_the_policy(repo: Path, cli, tmp_path):
    """示例的 `event_type` 取自 policy 的允许集（**不**硬编码某个接入方 policy 里的名字）。"""
    old = _issue31_shape(repo, cli)
    pol_file = repo / C.POLICY_PATH
    doc = json.loads(pol_file.read_text(encoding="utf-8"))
    doc["evidence"]["protected_write_event_types"] = ["protected_artifact_explained"]
    seed = tmp_path / "policy.json"
    seed.write_text(json.dumps(doc), encoding="utf-8")
    # 直接改盘上 policy（本测试只看文案；不改 init 台账，`check` 不读它）
    pol_file.write_text(json.dumps(doc), encoding="utf-8")
    commit_all(repo, "policy 换成接入方的类型名")

    _, _, err = _check(repo, cli)

    assert old in err
    assert '"event_type": "protected_artifact_explained"' in err


# ------------------------------------------------------------------ 诊断不触发

def test_a_move_into_an_existing_archive_dir_gets_no_move_hint(repo: Path, cli):
    """往**已存在**的归档目录搬 ⇒ 照旧红，且**不**给搬移诊断（它不是到达）。"""
    init_wired(repo, cli)
    (repo / ARCHIVE_REL / "2026-10-01-old").mkdir(parents=True)
    for name in ("proposal.md", "design.md", "tasks.md"):
        (repo / ARCHIVE_REL / "2026-10-01-old" / name).write_text("x\n", encoding="utf-8")
    (repo / ARCHIVE_REL / "2026-10-01-old" / "specs").mkdir()
    (repo / ARCHIVE_REL / "2026-10-01-old" / "reviews").mkdir()
    change_dir(repo, CHANGE).mkdir(parents=True, exist_ok=True)
    (change_dir(repo, CHANGE) / EVENTS).write_text(
        _event_line(f"{CHANGES}/{CHANGE}/{EVENTS}"), encoding="utf-8"
    )
    commit_content(repo, CHANGE)
    commit_evidence(repo, CHANGE)
    git(repo, "checkout", "-q", "-b", "feature")
    git(repo, "rm", "-q", f"{CHANGES}/{CHANGE}/{EVENTS}")
    # 同相对子路径的 `A` 落在**已存在**的归档目录里 ⇒ 不是到达 ⇒ 不给诊断
    (repo / ARCHIVE_REL / "2026-10-01-old" / EVENTS).write_text(
        _event_line("x") * 5, encoding="utf-8"
    )
    commit_all(repo, "往已存在的归档目录搬")

    code, _, err = _check(repo, cli)

    assert code == C.EXIT_FAIL
    assert "受保护路径被写入" in err
    assert "搬移的一半" not in err


# ------------------------------------------------------------------ 纯函数

def _change(path, status="D", old=None):
    return gitutil.Change(status, path, old)  # 字段顺序：(status, path, old_path)


def _arrival(name="x", directory=None, records=(), source_ids=frozenset()):
    return contract.Arrival(
        name=name,
        directory=directory or f"{ARCHIVE_REL}/{name}",
        records=tuple(records),
        source_ids=frozenset(source_ids),
    )


def _pol():
    return policy_mod.Policy.from_doc(policy_mod.default_policy_doc())


def test_pairs_a_D_with_an_A_at_the_same_relative_subpath():
    d = _change(f"{CHANGES}/b/{EVENTS}")
    a = _change(f"{ARCHIVE_REL}/x/{EVENTS}", status="A")
    got = contract.move_half_candidates([d, a], _pol(), [_arrival()])
    assert got == {f"{CHANGES}/b/{EVENTS}": f"{ARCHIVE_REL}/x/{EVENTS}"}


def test_requires_an_arriving_directory():
    d = _change(f"{CHANGES}/b/{EVENTS}")
    a = _change(f"{ARCHIVE_REL}/x/{EVENTS}", status="A")
    assert contract.move_half_candidates([d, a], _pol(), []) == {}


def test_requires_the_same_relative_subpath():
    d = _change(f"{CHANGES}/b/{EVENTS}")
    a = _change(f"{ARCHIVE_REL}/x/other.jsonl", status="A")
    assert contract.move_half_candidates([d, a], _pol(), [_arrival()]) == {}


def test_ignores_a_source_outside_the_changes_root():
    d = _change(f"{EVENTS}")            # 仓根下，不在 `<changes_root>/<id>/`
    a = _change(f"{ARCHIVE_REL}/x/{EVENTS}", status="A")
    assert contract.move_half_candidates([d, a], _pol(), [_arrival()]) == {}


def test_ignores_an_empty_subpath():
    d = _change(f"{CHANGES}/b")          # `<sub>` 为空（目录本身）
    a = _change(f"{ARCHIVE_REL}/x", status="A")
    assert contract.move_half_candidates([d, a], _pol(), [_arrival()]) == {}


def test_is_deterministic_with_several_candidates():
    d = _change(f"{CHANGES}/b/{EVENTS}")
    a1 = _change(f"{ARCHIVE_REL}/z/{EVENTS}", status="A")
    a2 = _change(f"{ARCHIVE_REL}/a/{EVENTS}", status="A")
    arrivals = [_arrival(name="z"), _arrival(name="a")]
    got = contract.move_half_candidates([d, a1, a2], _pol(), arrivals)
    assert got[f"{CHANGES}/b/{EVENTS}"] == f"{ARCHIVE_REL}/a/{EVENTS}"  # 字典序最小
