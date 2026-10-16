"""Q2 裁定 (a)：**已接入**的仓上显式 `init --gate-ref <新>` ⇒ 重写 caller + 同步台账。

背景（issue #30）：`--gate-ref` 只影响 workflow 文件的 ref，包版本另有一处来源；
接入方要换 ref 时，`init` 的「只增不改」会判冲突 ⇒ 必须有一个**单一、显式**的动作。

三条硬约束（grill M2，均已实测）：
1. 动作 = 重写 caller **+ 同步台账该条目的 `sha256` 与 `gate_ref`** ——只改 caller 会让
   「磁盘 ≠ 台账」：plain `init` 走漂移分支退 1、`uninit` 拒删退 1。
2. **作用域限定「已接入分支」**（`init-manifest.json` 存在）——否则会静默覆盖新仓里
   外来的 caller，推翻 `tests/test_init.py` 的「新仓目标文件已存在 ⇒ 冲突且整体不落盘」。
3. 其余文件（policy）照旧**只增不改**，plain `init` 的幂等与 `uninit` 的回滚都不受影响。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import constants as C
from witnessloop import initcmd
from witnessloop.hashing import sha256_bytes

from conftest import git

#: **刻意取一个不可能成为出厂默认的 ref**（对抗轮 R3 的 M1）：这组用例的前提是
#: 「换成一个**不同**的 ref」，若它与 `C.DEFAULT_GATE_REF` 撞值，`sync_caller_gate_ref`
#: 会判「台账里记的就是这个」而直接 no-op，整套用例的前提就整条塌掉——
#: 而默认值在 post-merge 步骤里是要挪的（`tasks.md §6.1` 会把它挪到 `@v1.7.0`）。
NEW_REF = f"{C.REPO_SLUG}/.github/workflows/gate.yml@v9.9.9"
OLD_REF = C.DEFAULT_GATE_REF


def _ledger(repo: Path) -> dict:
    import json

    return json.loads((repo / C.INIT_MANIFEST_PATH).read_text(encoding="utf-8"))


def _caller_entry(manifest: dict) -> dict:
    return next(
        entry
        for entry in manifest["created_files"]
        if entry["path"] == C.GATE_WORKFLOW_PATH
    )


def test_new_ref_does_not_collide_with_the_factory_default():
    """把「前提」本身钉成一条测试——否则 post-merge 挪默认值时它会**静默**塌掉。"""
    assert NEW_REF != C.DEFAULT_GATE_REF


def _init(repo: Path, cli, *extra: str) -> None:
    code, _, err = cli("init", "--root", str(repo), *extra)
    assert code == C.EXIT_PASS, err


# ---------------------------------------------------------------- 主路径

def test_explicit_different_ref_rewrites_caller_and_syncs_the_ledger(repo: Path, cli):
    _init(repo, cli)
    assert _ledger(repo)["gate_ref"] == OLD_REF

    code, out, err = cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    assert code == C.EXIT_PASS, err
    expected = initcmd.caller_workflow(NEW_REF)
    assert (repo / C.GATE_WORKFLOW_PATH).read_text(encoding="utf-8") == expected
    manifest = _ledger(repo)
    assert manifest["gate_ref"] == NEW_REF
    assert _caller_entry(manifest)["sha256"] == sha256_bytes(expected.encode("utf-8"))
    # 不能谎称「幂等，无改动」——它确实改了东西（工具不撒谎）。
    assert "幂等" not in out
    assert C.GATE_WORKFLOW_PATH in out


def test_rewrite_leaves_the_policy_untouched(repo: Path, cli):
    _init(repo, cli)
    before = (repo / C.POLICY_PATH).read_bytes()

    cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    assert (repo / C.POLICY_PATH).read_bytes() == before


def test_plain_init_is_idempotent_after_the_rewrite(repo: Path, cli):
    """终态必须是**不动点**：重写之后 plain `init` 得回到「幂等，无改动」。"""
    _init(repo, cli)
    cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    code, out, err = cli("init", "--root", str(repo))

    assert code == C.EXIT_PASS, err
    assert "幂等" in out


def test_uninit_still_works_after_the_rewrite(repo: Path, cli):
    """只重写 caller 而不同步台账会**卸载不掉**（`uninit` 拒删）——这条是那件事的钉子。"""
    _init(repo, cli)
    cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    code, out, err = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_PASS, err
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
    assert not (repo / C.INIT_MANIFEST_PATH).exists()


def test_rewrite_rescues_a_hand_edited_caller(repo: Path, cli):
    """K3 的分叉态（人把 caller 手改成新 ref、台账没跟）也要能被这个动作救回来。"""
    _init(repo, cli)
    (repo / C.GATE_WORKFLOW_PATH).write_text(
        initcmd.caller_workflow(NEW_REF), encoding="utf-8"
    )
    # 先确认这确实是个分叉态：plain init 退 1
    code, _, _ = cli("init", "--root", str(repo))
    assert code == C.EXIT_FAIL

    code, _, err = cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    assert code == C.EXIT_PASS, err
    assert _ledger(repo)["gate_ref"] == NEW_REF
    assert cli("uninit", "--root", str(repo))[0] == C.EXIT_PASS


# ---------------------------------------------------------------- 不越界

def test_same_ref_is_a_noop(repo: Path, cli):
    _init(repo, cli)

    code, out, err = cli("init", "--root", str(repo), "--gate-ref", OLD_REF)

    assert code == C.EXIT_PASS, err
    assert "幂等" in out


def test_plain_init_still_refuses_a_hand_edited_caller(repo: Path, cli):
    """漂移判定照旧——「显式 --gate-ref」不是一条给手改兜底的后门。"""
    _init(repo, cli)
    (repo / C.GATE_WORKFLOW_PATH).write_text("name: tampered\n", encoding="utf-8")

    code, _, err = cli("init", "--root", str(repo))

    assert code == C.EXIT_FAIL
    assert "被改动过" in err


def test_missing_caller_is_not_resurrected(repo: Path, cli):
    """盘上没有 caller ⇒ **不**凭空复活它（只增不改）；让漂移分支响亮地报。"""
    _init(repo, cli)
    (repo / C.GATE_WORKFLOW_PATH).unlink()

    code, _, err = cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    assert code == C.EXIT_FAIL
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
    assert _ledger(repo)["gate_ref"] == OLD_REF  # 没同步（没动就没同步）
    assert err  # 有诊断，不静默


def test_foreign_caller_in_a_new_repo_still_conflicts(repo: Path, cli):
    """作用域：**未接入**的仓里已存在内容不同的 caller ⇒ 冲突且整体不落盘（照旧）。

    这条与重写动作是一对：少了作用域限制，重写语义会把这个外来文件静默覆盖。
    """
    target = repo / C.GATE_WORKFLOW_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("name: someone-elses-gate\n", encoding="utf-8")

    code, _, err = cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    assert code == C.EXIT_FAIL
    assert "冲突" in err
    assert target.read_text(encoding="utf-8") == "name: someone-elses-gate\n"
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert not (repo / C.POLICY_PATH).exists()


def test_uninitialized_repo_writes_the_requested_ref(repo: Path, cli):
    """未接入（正常路径）：`--gate-ref` 照旧写进 caller（这条是回归，不是新行为）。"""
    _init(repo, cli, "--gate-ref", NEW_REF)

    assert (repo / C.GATE_WORKFLOW_PATH).read_text(encoding="utf-8") == (
        initcmd.caller_workflow(NEW_REF)
    )
    assert _ledger(repo)["gate_ref"] == NEW_REF


# ---------------------------------------------------------------- dry-run

def test_dry_run_previews_without_writing(repo: Path, cli):
    _init(repo, cli)
    caller_before = (repo / C.GATE_WORKFLOW_PATH).read_bytes()
    manifest_before = (repo / C.INIT_MANIFEST_PATH).read_bytes()
    status_before = git(repo, "status", "--porcelain")

    code, out, err = cli("init", "--root", str(repo), "--dry-run", "--gate-ref", NEW_REF)

    assert code == C.EXIT_PASS, err
    assert "[dry-run]" in out
    assert (repo / C.GATE_WORKFLOW_PATH).read_bytes() == caller_before
    assert (repo / C.INIT_MANIFEST_PATH).read_bytes() == manifest_before
    assert git(repo, "status", "--porcelain") == status_before


def test_dry_run_does_not_report_a_conflict_it_would_have_fixed(repo: Path, cli):
    """`--dry-run --gate-ref <新>` 不该报冲突——那个「冲突」正是这个动作要消掉的那条。

    （不修这条的话，dry-run 会对一个将要被自己改掉的文件报红，用户无从判断。）
    """
    _init(repo, cli)

    code, _, err = cli("init", "--root", str(repo), "--dry-run", "--gate-ref", NEW_REF)

    assert code == C.EXIT_PASS, err
    assert "冲突" not in err


def test_explicit_gate_ref_plus_conflicting_policy_writes_then_reports(repo: Path, cli, tmp_path):
    """组合语义**写死**（对抗轮 R2 的 L4）：caller + 台账**先写**，其余判定照常参与退出码，
    失败**不回滚**——与 `--test-command` 的既有先例同口径（`initcmd` 的 Z1/O2 注释）。

    并且**必须**在报错里说明那一半已经落盘：否则用户会以为什么都没发生，
    转头去删 policy（对抗轮 R2 实测：旧 CLI 上正是这条误导文案）。
    """
    import json

    _init(repo, cli)
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"changes_root": "custom/root"}), encoding="utf-8")

    code, _, err = cli(
        "init", "--root", str(repo), "--gate-ref", NEW_REF, "--policy", str(seed)
    )

    assert code == C.EXIT_FAIL
    assert "冲突" in err  # policy 那条轴照旧参与退出码
    # 显式 --gate-ref 那一半**确实做成了**（不是「整体不落盘」——那是未接入分支的语义）
    assert f"uses: {NEW_REF}" in (
        repo / C.GATE_WORKFLOW_PATH
    ).read_text(encoding="utf-8")
    assert _ledger(repo)["gate_ref"] == NEW_REF
    # 报错里点明「已落盘、不回滚」——这是 L4 的实质
    assert "不回滚" in err


def test_dry_run_must_not_claim_it_wrote_anything(repo: Path, cli, tmp_path):
    """对抗轮 R3 的 M4：`--dry-run` 下**什么都没落盘** ⇒ 那句话不得说「已落盘」。

    这条与上一条是一对：上一条钉「真跑时要点明已落盘、不回滚」，这一条钉
    「dry-run 时**不许**这么说」——两句都由同一个参数喂，很容易被写成一个常量而撒谎。
    """
    import json

    _init(repo, cli)
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"changes_root": "custom/root"}), encoding="utf-8")

    code, _, err = cli(
        "init",
        "--root",
        str(repo),
        "--dry-run",
        "--gate-ref",
        NEW_REF,
        "--policy",
        str(seed),
    )

    assert code == C.EXIT_FAIL  # policy 那条轴照旧参与退出码
    assert "冲突" in err
    assert "已落盘" not in err, "dry-run 里什么都没写，不得声称已落盘"
    assert "未落盘" in err
    assert (repo / C.GATE_WORKFLOW_PATH).read_text(encoding="utf-8") != (
        initcmd.caller_workflow(NEW_REF)
    )
    assert _ledger(repo)["gate_ref"] == OLD_REF


def test_ledger_without_a_caller_entry_is_repaired(repo: Path, cli):
    """spec 的 Scenario「台账里没有 caller 条目」的**行为级钉子**（对抗轮 R4 的观察：
    `initcmd._set_ledger_gate_ref` 的「补条目」分支此前**没有任何测试覆盖**）。

    语义：显式 `--gate-ref` ⇒ 同步 `gate_ref` **并补上**该条目（`sha256` = 新内容），
    且插在台账自己的 `self` 条目**之前**（台账自己那条约定俗成排最后，`uninit` 依赖这个顺序）。
    """
    import json

    _init(repo, cli)
    manifest = _ledger(repo)
    manifest["created_files"] = [
        entry for entry in manifest["created_files"] if entry["path"] != C.GATE_WORKFLOW_PATH
    ]
    (repo / C.INIT_MANIFEST_PATH).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    code, _, err = cli("init", "--root", str(repo), "--gate-ref", NEW_REF)

    assert code == C.EXIT_PASS, err
    after = _ledger(repo)
    assert after["gate_ref"] == NEW_REF
    paths = [entry["path"] for entry in after["created_files"]]
    assert paths[-1] == C.INIT_MANIFEST_PATH, f"self 条目必须排最后，实得 {paths}"
    assert paths.count(C.GATE_WORKFLOW_PATH) == 1
    expected = initcmd.caller_workflow(NEW_REF)
    assert _caller_entry(after)["sha256"] == sha256_bytes(expected.encode("utf-8"))
    # 补出来的条目不是「死账」：随后 plain init 幂等、uninit 仍能回滚它。
    assert "幂等" in cli("init", "--root", str(repo))[1]
    assert cli("uninit", "--root", str(repo))[0] == C.EXIT_PASS
    assert not (repo / C.GATE_WORKFLOW_PATH).exists()
