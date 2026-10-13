"""B 组：`init` 侧的测试执行点（change adopter-test-gate / design D3、D6）。

三条承重性质，每条都有实测依据：

* **种子不进 `desired_files()`**（D3）——`desired_files()` 同时喂写盘、台账、**两条冲突判定**，
  所以哪怕只是「不进台账」也不够：接入方改过命令之后 plain `init` 仍会 exit 1（实测）。
* **`--test-command` 总是覆盖**（B2/X1）——默认序列（plain `init` 先种哨兵）恰好让文件存在，
  「不存在才写」会让唯一能自动接线的入口静默 no-op。
* **`--no-tests` 写的是 `tests.disabled: true`**（B3/Y1）——不是「置空」：`from_doc` 用
  `or DEFAULT`，`""`/`null`/缺省**都会**被读成「声明」。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from witnessloop import constants as C
from witnessloop import initcmd

from conftest import commit_all, git

TESTS = C.ADOPTER_TESTS_PATH
CMD = "uv run pytest -q"
SENTINEL_BODY = C.ADOPTER_TESTS_SENTINEL + "\n"


def _text(repo: Path) -> str:
    return (repo / TESTS).read_text(encoding="utf-8")


# ---------------------------------------------------------------- B1/B2：写入语义

def test_init_without_flag_seeds_the_sentinel(repo: Path, cli):
    code, out, err = cli("init", "--root", str(repo))
    assert code == C.EXIT_PASS, err
    assert _text(repo) == SENTINEL_BODY
    assert TESTS in out  # 产物清单里点名（它仍是产物）


def test_init_test_command_wires_the_file(repo: Path, cli):
    code, _, err = cli("init", "--root", str(repo), "--test-command", CMD)
    assert code == C.EXIT_PASS, err
    assert _text(repo) == CMD + "\n"


def test_test_command_overwrites_an_existing_sentinel(repo: Path, cli):
    """X1 的回归：**默认序列**（plain init ⇒ 哨兵）之后 `--test-command` 必须生效。"""
    cli("init", "--root", str(repo))
    assert _text(repo) == SENTINEL_BODY

    code, _, err = cli("init", "--root", str(repo), "--test-command", CMD)

    assert code == C.EXIT_PASS, err
    assert _text(repo) == CMD + "\n"


def test_test_command_overwrites_a_hand_edited_command(repo: Path, cli):
    cli("init", "--root", str(repo), "--test-command", CMD)
    (repo / TESTS).write_text("uv run pytest -x -q\n", encoding="utf-8")

    code, _, err = cli("init", "--root", str(repo), "--test-command", CMD)

    assert code == C.EXIT_PASS, err
    assert _text(repo) == CMD + "\n"


# ---------------------------------------------------------------- B4b：覆盖分支的对外表现

def test_overwrite_says_it_wrote_and_never_claims_no_change(repo: Path, cli):
    """Z1：这一跑**确实改了**文件 ⇒ 不许沿用「幂等，无改动」（工具不得撒谎）。"""
    cli("init", "--root", str(repo))
    commit_all(repo, "接入")

    code, out, err = cli("init", "--root", str(repo), "--test-command", CMD)

    assert code == C.EXIT_PASS, err
    assert TESTS in out
    assert "幂等" not in out


def test_dry_run_on_an_onboarded_repo_writes_nothing_and_says_so(repo: Path, cli):
    """`--dry-run` 的语义是**不落盘**：那条「将写入」的话之后，收尾不得说「未 commit」
    （什么都没写，哪来的提交），也不得说「幂等，无改动」（下一秒就会写）。"""
    cli("init", "--root", str(repo), "--test-command", CMD)
    commit_all(repo, "接入")

    code, out, err = cli("init", "--root", str(repo), "--test-command", "别的命令", "--dry-run")

    assert code == C.EXIT_PASS, err
    assert "dry-run" in out
    assert "未 commit" not in out
    assert "幂等" not in out
    assert _text(repo) == CMD + "\n"  # 没落盘
    assert git(repo, "status", "--porcelain").strip() == ""


def test_plain_init_with_an_existing_command_is_idempotent(repo: Path, cli):
    """对照分支：无 flag 且文件已存在（没动它）⇒ 仍是「幂等，无改动」。"""
    cli("init", "--root", str(repo), "--test-command", CMD)
    commit_all(repo, "接入")

    code, out, err = cli("init", "--root", str(repo))

    assert code == C.EXIT_PASS, err
    assert "幂等" in out
    assert _text(repo) == CMD + "\n"


def test_overwrite_does_not_swallow_other_conflicts(repo: Path, cli):
    """Z1/O2：覆盖写在早返回之前，但**其余判定照旧参与退出码**。

    已接入仓上 `--test-command` 叠一个**不同**的 `--policy` ⇒ 仍必须报冲突退 1
    （否则「`--policy` 被静默忽略」那个老洞会从新 flag 借尸还魂）。

    ⚠️ 同时钉住**副作用本身**（审阅 R1 的 I5）：这次失败的 `init` **已经把命令文件覆盖了**
    ——「写在前、不因后续冲突回滚」是认下的行为（当场打印点名那一行 ⇒ 绝不静默）。
    把它写成断言，免得将来谁把写入挪到判定之后而没人发现行为变了。
    """
    cli("init", "--root", str(repo))
    commit_all(repo, "接入")
    assert _text(repo) == SENTINEL_BODY
    seed = repo.parent / "seed-policy.json"
    doc = json.loads((repo / C.POLICY_PATH).read_text(encoding="utf-8"))
    doc["changes_root"] = "elsewhere/changes"
    seed.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    code, err_out, err = cli(
        "init", "--root", str(repo), "--test-command", CMD, "--policy", str(seed)
    )

    assert code == C.EXIT_FAIL
    assert "冲突" in err
    # 副作用：命令文件已被覆盖（这是**声明出来的**行为，不是漏网），且**当场**说了。
    assert _text(repo) == CMD + "\n"
    assert TESTS in err_out


# ---------------------------------------------------------------- B3：opt-out

def test_no_tests_writes_the_disabled_policy_and_no_file(repo: Path, cli, read_json):
    code, _, err = cli("init", "--root", str(repo), "--no-tests")

    assert code == C.EXIT_PASS, err
    assert not (repo / TESTS).exists()
    assert read_json(repo / C.POLICY_PATH)["tests"] == {"disabled": True}


def test_no_tests_on_a_default_policy_repo_is_a_conflict(repo: Path, cli):
    """已接入且 policy 与出厂默认一致的仓，再给 `--no-tests` ⇒ policy 的「本次期望」
    与磁盘不同 ⇒ 冲突退 1。（这是已接入仓的 opt-out 只能改 `policy.json`、
    因而每次都要一条解释事件的原因——**不是**「`--no-tests` 完全不可用」。）
    """
    cli("init", "--root", str(repo))
    commit_all(repo, "接入")

    code, _, err = cli("init", "--root", str(repo), "--no-tests")

    assert code == C.EXIT_FAIL
    assert "冲突" in err


def test_no_tests_is_idempotent_on_an_already_disabled_repo(repo: Path, cli, read_json):
    """订正（审阅 R1 的 I6②）：**已经**是 opt-out 的仓再给 `--no-tests` 是**幂等** exit 0。

    「`--no-tests` 只在新接入时可用」这句**说过头了**——它描述的是「从默认 policy 切到
    opt-out」那一次（上一条），而不是这个 flag 本身不可用。
    """
    code, _, err = cli("init", "--root", str(repo), "--no-tests")
    assert code == C.EXIT_PASS, err

    code, out, err = cli("init", "--root", str(repo), "--no-tests")

    assert code == C.EXIT_PASS, err
    assert "幂等" in out
    assert read_json(repo / C.POLICY_PATH)["tests"] == {"disabled": True}


def test_no_tests_does_not_claim_the_policy_came_from_a_file(repo: Path, cli):
    """`--no-tests` **也会**改 policy doc，但它不是 `--policy`——别打那条「policy 来自 --policy」。

    （手工 e2e 抓到的：判据原先写成「policy_doc 非 None」，于是 `--no-tests` 会误触发
    `init：policy 来自 --policy（轻校验…）`，而用户根本没给过该 flag。）
    """
    code, out, err = cli("init", "--root", str(repo), "--no-tests")

    assert code == C.EXIT_PASS, err
    assert "--policy" not in out
    # 该说的是它对 policy 做了什么；否则 `--no-tests` 的用户以为 policy 是出厂默认。
    assert "tests.disabled" in out


def test_no_tests_and_test_command_cannot_be_combined(repo: Path, cli):
    """两个 flag 是「写一条命令」与「不写文件」——互斥（argparse 退 2，同 `test_cli.py` 的手法）。"""
    with pytest.raises(SystemExit) as exc:
        cli("init", "--root", str(repo), "--no-tests", "--test-command", CMD)

    assert exc.value.code == C.EXIT_USAGE
    assert not (repo / C.POLICY_PATH).exists()
    assert not (repo / TESTS).exists()


# ---------------------------------------------------------------- B1：双重身份

def test_tests_file_is_not_in_desired_files():
    """承重：`desired_files()` 同时喂写盘、台账与**两条冲突判定** ⇒ 种子不能进。"""
    assert TESTS not in initcmd.desired_files(C.DEFAULT_GATE_REF)


def test_tests_file_is_not_in_the_ledger(repo: Path, cli, read_json):
    cli("init", "--root", str(repo))
    manifest = read_json(repo / C.INIT_MANIFEST_PATH)
    assert TESTS not in {entry["path"] for entry in manifest["created_files"]}


def test_edited_command_survives_a_plain_init(repo: Path, cli):
    """D3 的兑现（**回归重点**）：接入方改过命令之后，plain `init` 仍 exit 0。

    这条不测，D3 那句「改命令 = 一次普通 commit」就是空话。
    """
    cli("init", "--root", str(repo), "--test-command", CMD)
    commit_all(repo, "接入")
    (repo / TESTS).write_text("uv run pytest -x -q --cov\n", encoding="utf-8")
    commit_all(repo, "改命令（普通 commit，无解释事件）")

    code, out, err = cli("init", "--root", str(repo))

    assert code == C.EXIT_PASS, err
    assert _text(repo) == "uv run pytest -x -q --cov\n"  # 没被覆盖回去


def test_tests_file_survives_uninit(repo: Path, cli):
    """命令文件不在台账 ⇒ `uninit` 看不见它（**不需要**改 `uninitcmd.py`）。"""
    cli("init", "--root", str(repo), "--test-command", CMD)

    code, _, err = cli("uninit", "--root", str(repo))

    assert code == C.EXIT_PASS, err
    assert not (repo / C.INIT_MANIFEST_PATH).exists()
    assert _text(repo) == CMD + "\n"


# ---------------------------------------------------------------- --dry-run（N3）

def test_dry_run_lists_the_tests_file_only_when_it_would_write_it(repo: Path, cli):
    code, out, _ = cli("init", "--root", str(repo), "--dry-run")
    assert code == C.EXIT_PASS
    assert TESTS in out
    assert not (repo / TESTS).exists()
    assert git(repo, "status", "--porcelain").strip() == ""


def test_dry_run_does_not_claim_a_file_it_would_not_write(repo: Path, cli):
    """已存在 ⇒ 种子不动它 ⇒ 「产物清单」不得谎称会写（N3）。"""
    (repo / TESTS).parent.mkdir(parents=True, exist_ok=True)
    (repo / TESTS).write_text(CMD + "\n", encoding="utf-8")
    commit_all(repo, "自带的命令文件")

    code, out, _ = cli("init", "--root", str(repo), "--dry-run")

    assert code == C.EXIT_PASS
    assert TESTS not in out


# ---------------------------------------------------------------- B6：既有字节冻结

def test_caller_workflow_bytes_are_frozen():
    """R9：本 change **不许**改 `caller_workflow()` 的字节。

    本仓 init 台账里记着 caller 的 sha256；改一个字节就让「磁盘 ≠ 台账」，
    而本仓的 `init` 本来就坏（定制 policy 撞出厂默认）⇒ 只能靠这条 golden literal 钉住。
    """
    expected = (
        "# 由 `witnessloop init` 生成，请勿手改——`witnessloop uninit` 依\n"
        "# .witnessloop/init-manifest.json 的 hash 台账回滚它。\n"
        "# 门禁本体住在 reusable workflow 里，本文件只是 caller。\n"
        "name: witnessloop\n"
        "\n"
        "on:\n"
        "  pull_request:\n"
        "\n"
        "permissions:\n"
        "  contents: read\n"
        "\n"
        "jobs:\n"
        "  gate:\n"
        f"    uses: {C.DEFAULT_GATE_REF}\n"
    )
    assert initcmd.caller_workflow(C.DEFAULT_GATE_REF) == expected
