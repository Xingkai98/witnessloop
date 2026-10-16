"""Q4 裁定 (a)：`check` 自报它实际跑的包 ref —— **尽力而为**。

R1 的 K1 实测证伪了原稿的「包无法自报 ref」：`uvx --from "git+…"` 装出的 dist-info 带
PEP 610 的 `direct_url.json`，其 `vcs_info` 有 `requested_revision` 与 `commit_id`。

两条边界（裁定原文）：
- **尽力而为、取不到不失败**：本地 editable / 源码直跑没有 `vcs_info` ⇒ 打 `<未知>`，
  **退出码不变**（报不出 ref 不是一条红）。
- 它比 gate.yml 的 `::notice::` **严格更强**：那个只能打出**请求的 ref**，
  这个还能打出**解析出的 commit**（issue #30 的验收证据恰恰是 resolved sha）。
"""

from __future__ import annotations

from pathlib import Path

from witnessloop import checkcmd
from witnessloop import constants as C

from helpers import init_wired

#: R1 实测抓到的**真实**载荷（uv 0.13.1，`uvx --from git+…@v1`）。
REAL_DIRECT_URL = (
    '{"url":"https://github.com/Xingkai98/witnessloop",'
    '"vcs_info":{"vcs":"git",'
    '"commit_id":"ae992565ee2162e5b272af471e9adf895e7f83fb",'
    '"requested_revision":"v1"}}'
)


def test_parses_the_real_payload():
    revision, commit = checkcmd.vcs_info_from_direct_url(REAL_DIRECT_URL)

    assert revision == "v1"
    assert commit == "ae992565ee2162e5b272af471e9adf895e7f83fb"


def test_absent_or_unusable_metadata_is_not_an_error():
    """尽力而为：这些输入全都只能得到 `(None, None)`，**不得抛**。"""
    for raw in (
        None,
        "",
        "not json",
        "[]",  # 根不是对象
        "{}",  # 没有 vcs_info（editable 安装就是这个形状）
        '{"vcs_info": null}',
        '{"vcs_info": []}',
        '{"vcs_info": {"commit_id": null, "requested_revision": null}}',
        '{"vcs_info": {"commit_id": 42, "requested_revision": []}}',
    ):
        assert checkcmd.vcs_info_from_direct_url(raw) == (None, None), raw


def test_child_fields_can_be_present_independently():
    assert checkcmd.vcs_info_from_direct_url('{"vcs_info":{"commit_id":"abc"}}') == (
        None,
        "abc",
    )
    assert checkcmd.vcs_info_from_direct_url(
        '{"vcs_info":{"requested_revision":"main"}}'
    ) == ("main", None)


# ---------------------------------------------------------------- 端到端

def test_check_prints_the_line_even_from_source(gated: Path, cli):
    """本仓测试是**源码直跑**（没有 `direct_url.json` 的 `vcs_info`）⇒ 打 `<未知>`。

    这正是「取不到不失败」那条：这一行必须在，且 `check` 的判定不受它影响。
    """
    (gated / "note.txt").write_text("x\n", encoding="utf-8")

    code, out, _ = cli("check", "--root", str(gated), "--base", "main", "--head", "HEAD")

    assert "requested_revision=" in out
    assert "commit_id=" in out
    # 源码直跑 ⇒ 两值都取不到，但**不因此**改变退出码（这里红的是别的东西，
    # 与「报不出 ref」无关——断言这一行本身没引入判决即可）。
    assert "<未知>" in out or "ae9925" in out
    assert code in (C.EXIT_PASS, C.EXIT_FAIL)


def test_not_onboarded_still_reports_the_package_source(repo: Path, cli):
    code, out, _ = cli("check", "--root", str(repo), "--base", "main", "--head", "HEAD")

    assert code == C.EXIT_NOT_ONBOARDED
    assert "requested_revision=" in out


def test_installed_vcs_ref_is_a_pair():
    """真实环境里读一次（不 mock）：只要不抛、返回二元组即可。"""
    pair = checkcmd.installed_vcs_ref()

    assert isinstance(pair, tuple) and len(pair) == 2
    for value in pair:
        assert value is None or isinstance(value, str)


def test_wired_repo_check_line_survives_a_green_run(repo: Path, cli):
    """全绿的一次 `check` 里那一行照样在（它不属于任何 finding）。"""
    init_wired(repo, cli)
    from conftest import commit_all, git

    commit_all(repo, "接入")
    git(repo, "checkout", "-q", "-b", "feature")
    (repo / "note.txt").write_text("x\n", encoding="utf-8")
    commit_all(repo, "改动")

    code, out, _ = cli("check", "--root", str(repo), "--base", "main", "--head", "HEAD")

    assert "requested_revision=" in out
    assert "check：通过 ✓" in out
    assert code == C.EXIT_PASS
