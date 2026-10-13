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


def test_design_documents_the_interaction_layer_environment_variables():
    """design §5.2 是交互层的权威——两个取值覆盖点必须写在那里。"""
    text = (REPO_ROOT / "docs/design.md").read_text(encoding="utf-8")
    assert "WITNESSLOOP_RUN_ID" in text
    assert "WITNESSLOOP_TEMPLATES_DIR" in text


@pytest.mark.parametrize("relpath", ("README.md", "docs/design.md"))
def test_docs_name_all_four_verbs(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    for verb in ("init", "check", "uninit", "manifest build"):
        assert verb in text, f"{relpath} 没提到动词 {verb}"


#: 讲 run id 取值的地方——兜底从「时间戳 + 随机」改成确定性锚（#3）之后，这些地方
#: 都不该再承诺一个**非确定性**的 id，否则读者会以为重复 build 幂等不了。
RUN_ID_DOCS = (
    "docs/design.md",
    "templates/grill.md",
    "templates/review-loop.md",
    "plugin/README.md",
    "plugin/commands/grill.md",
    "plugin/commands/review-loop.md",
    # `--help` 也是文档：不留神就会把「给了才幂等」这种**现在为假**的说法
    # 静默留在用户最先看到的地方。
    "src/witnessloop/cli.py",
)

STALE_FALLBACK_CLAIMS = (
    "短随机",
    "UTC 时间戳",
    "-<utc>-<随机>",
    # 同族假说法：「兜底 id 每次都不一样」。兜底是确定性的，重复 build 得到的是
    # **同一个** id。（R2 N2：原来只抓裸子串「才幂等」，既漏了这一族，又会误伤
    # 正确的「固定 base 与 revision **才**幂等」——所以改用具体措辞列举，
    # 「给了才幂等」那一类由下面那条**正向约束**兜住。）
    "重复 build 会得到不同",
    "重复 build 得到不同",
    "两次 build 会得到不同",
    "每次 build 都不同",
)


@pytest.mark.parametrize("relpath", RUN_ID_DOCS)
def test_docs_promise_a_deterministic_fallback(relpath: str):
    """#3：文档里不得再写「时间戳 / 短随机」那种非确定性兜底。"""
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    for stale in STALE_FALLBACK_CLAIMS:
        assert stale not in text, f"{relpath} 仍写「{stale}」——兜底已改成确定性锚"
    assert "确定性" in text, f"{relpath} 没写明兜底是确定性的"


#: Q3 定稿：兜底路径下 `reviewer ≠ author` **结构性恒真**，那道校验只挡
#: 「**显式**把同一个值喂给两个角色」——不能再写成「挡忘了另开 run」，那是被证伪的旧口径。
#:
#: 判据用**精确字面量**：正确的写法是 `**不**等于「挡忘了另开 run」`（整句被「」包住），
#: 被否定的旧写法是 `挡「忘了另开 run」`（`挡` 紧跟 `「忘了`）。两者形态不同，
#: 所以一个字面量就能把旧的挑出来，不会误伤新写法。
STALE_Q3_CLAIM = "挡「忘了另开 run」"

#: 会写 run id 口径的地方（含**用户可见**的报错文案、源码注释、以及测试 docstring
#: ——R2 N4：测试里的口径也是口径，同样会漂）。
Q3_DOCS = RUN_ID_DOCS + (
    "src/witnessloop/manifestcmd.py",
    "src/witnessloop/contract.py",
    "tests/test_check_manifest.py",
)


@pytest.mark.parametrize("relpath", Q3_DOCS)
def test_docs_use_the_settled_identity_wording(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    assert STALE_Q3_CLAIM not in text, (
        f"{relpath} 仍写「{STALE_Q3_CLAIM}」——Q3 定稿是"
        "「兜底路径下结构性恒真，只挡显式把同一个值喂给两个角色」"
    )


#: 讲 `manifest build` 幂等的地方（比 RUN_ID_DOCS 多一份门禁契约文档）。
IDEMPOTENCY_DOCS = RUN_ID_DOCS + ("docs/gate.md",)


@pytest.mark.parametrize("relpath", IDEMPOTENCY_DOCS)
def test_every_idempotency_claim_is_scoped_or_qualified(relpath: str):
    """Q2 **正向约束**：文件里**每个**「幂等」都得有出处。

    一个「幂等」要么
    *(a)* 说的是 `init`（该行含 `init`）——init 的幂等讲的是「只增不改」，
    跟 base/revision 无关；要么
    *(b)* 附近（±2 行）带「固定 base 与 revision」限定。

    为什么按**文件整体**扫、而不是「附近有没有 `manifest build`」的行窗口：
    后者对 `cli.py` / `plugin/README.md` / `docs/gate.md` 是**空转**——那三句
    「幂等」离 `manifest build` 字面量超过窗口，在 `cli.py` 那行**删掉限定词**
    也照样全绿（R2 N1 实测）。而 `cli.py` 正是 CD9 的点名落点。
    """
    lines = (REPO_ROOT / relpath).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if "幂等" not in line or "init" in line:
            continue
        window = "\n".join(lines[max(0, index - 2) : index + 3])
        assert "固定 base 与 revision" in window, (
            f"{relpath}:{index + 1} 有「幂等」却既不是在讲 `init`、"
            f"也没带「固定 base 与 revision」限定：{line.strip()}"
        )


#: D7 反转后的新口径：**强制**的叙述里不得再把 hooks 说成「只作提醒 / advisory」。
#: change `grill-evidence-gate` 把本地层从「advisory」升为「会拦」，但反转**此前没有任何守卫**
#: 钉这处措辞（漏改不会红）——只会留下一份「本仓卖点（文档不漂移）自我打脸」的文档。
#: 历史决策记录 `docs/reviews/grill-design.md` 不在本名单（它保留原文 + 更新注，属档案）。
HOOK_POLICY_DOCS = ("docs/design.md", "README.md")
STALE_HOOK_CLAIMS = (
    "hooks 只作提醒",
    "hook 只作提醒",
    "hooks 只作辅助提醒",
    "hooks 只 advisory",
)


@pytest.mark.parametrize("relpath", HOOK_POLICY_DOCS)
def test_docs_no_longer_call_hooks_advisory_only(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    for claim in STALE_HOOK_CLAIMS:
        assert claim not in text, (
            f"{relpath} 仍把 hooks 说成「{claim}」——本地层已升为会拦的守卫（D7）"
        )
    assert "guard" in text, f"{relpath} 没提到本地守卫 `guard`"


#: 测试执行点门禁（change adopter-test-gate / `docs/gate.md §11`）的**承诺面**。
#:
#: 它承诺「测试失败 = 合不了」，所以必须**逐条**写出四条诚实边界——少一条就是过度承诺
#: （spec 的「诚实边界」Requirement 把这件事定义成硬要求，靠文档不靠自觉）。
ADOPTER_TESTS_DOCS = ("README.md", "docs/gate.md")
ADOPTER_TESTS_BOUNDARY_KEYWORDS = (
    "不保证",  # ① 只保证「有一个已接线的执行点」，不保证它真跑过/跑的是真测试
    "可以改",  # ② PR 可以改掉自己的命令文件 / CI 配置（保护面不含 .github/workflows/**）
    "fork",  # ③ 测试命令是任意代码，每个 PR（含 fork PR）都会跑
    "天花板",  # ④ 能力天花板：只有 contents: read、无 services/matrix、命令只能一行 shell
)

#: 涉**合并**的承诺（spec 点名的两个措辞）。每一处都要在 ±2 行内带上面某条限定。
MERGE_CLAIM_PHRASES = ("合不了", "拦住合并")


@pytest.mark.parametrize("relpath", ADOPTER_TESTS_DOCS)
def test_docs_spell_out_the_four_adopter_test_boundaries(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    missing = [k for k in ADOPTER_TESTS_BOUNDARY_KEYWORDS if k not in text]
    assert not missing, f"{relpath} 少了诚实边界的关键词：{missing}——那就是过度承诺"


@pytest.mark.parametrize("relpath", ADOPTER_TESTS_DOCS)
def test_every_merge_claim_is_qualified(relpath: str):
    """「合不了 / 拦住合并」必须带限定（同 `test_every_idempotency_claim_...` 的 ±2 行范式）。

    本 change 的立论是「机械」，所以「承诺面」也要机械化：没有这条，下一处新写的
    「测试失败 = 合不了」可以在任何人都不察觉的情况下把四条边界甩掉。
    """
    lines = (REPO_ROOT / relpath).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not any(phrase in line for phrase in MERGE_CLAIM_PHRASES):
            continue
        window = "\n".join(lines[max(0, index - 2) : index + 3])
        assert any(k in window for k in ADOPTER_TESTS_BOUNDARY_KEYWORDS), (
            f"{relpath}:{index + 1} 有「测试失败 = 合不了」式承诺却没带任何一条诚实边界："
            f"{line.strip()}"
        )


@pytest.mark.parametrize(
    "relpath", ("README.md", "docs/gate.md", "templates/review-loop.md")
)
def test_docs_never_teach_editing_init_artifacts(relpath: str):
    """不许把「手改 `init` 产物」或「先 `uninit` 再 `init`」教成配置通道（实测死锁）。

    （超出 spec 的**额外**守卫：spec 只点名「拦住合并」那条承诺面，这两条是同一族的
    教法禁令——`init`/`uninit` 同时 exit 1 而没有任何 flag 可确认，走进去就没出口。）
    """
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    for forbidden in ("手改 `init` 产物", "先 `uninit` 再 `init`"):
        assert forbidden not in text, f"{relpath} 教了「{forbidden}」——那是一条死锁路"


#: 诚实边界 ① 必须把「能骗过存在性判定」的已知形态**举例**出来（审阅 R1 的 I4）。
#:
#: 第三条判据只堵「**意外**空文件」，堵不住「只有注释 / `true` / `:`」——那与
#: `|| true`、`--collect-only` 是**同一类**（都是已声明的边界，不是缺陷）。但不写出来，
#: 读者会把「`check` 绿」读成「测试真的会跑」，那就是过度承诺。
BOUNDARY_ONE_EXAMPLES = ("|| true", "--collect-only", "# TODO")


@pytest.mark.parametrize("relpath", ADOPTER_TESTS_DOCS)
def test_boundary_one_lists_the_known_ways_to_fake_wiring(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    missing = [e for e in BOUNDARY_ONE_EXAMPLES if e not in text]
    assert not missing, (
        f"{relpath} 的边界 ① 少了这些「骗过存在性判定」的举例：{missing}"
        "——不举例就等于默认读者知道 `check` 的绿不代表测试会跑"
    )


def test_readme_marks_the_init_variants_as_alternatives():
    """审阅 R1 的 I6③：三条 `init` 放在同一个代码块里读起来像**顺序执行**，
    而它们是**互斥的替代**（`--policy` 才可组合）。README 得说清这一点。"""
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "三选一" in text
    assert "不是顺序执行" in text


#: 命令文件路径是**常量**（`constants.ADOPTER_TESTS_PATH`），不是 policy 旋钮
#: ⇒ 不得再把它写成「默认值」——那是旧 `tests.execution_point` 旋钮的残留措辞
#: （审阅 R1 的 I6①）。
STALE_TESTS_PATH_DEFAULT_CLAIM = "（默认 `.github/witnessloop-tests.txt`）"


@pytest.mark.parametrize(
    "relpath",
    ADOPTER_TESTS_DOCS
    + ("openspec/changes/adopter-test-gate/specs/adopter-test-job/spec.md",),
)
def test_docs_do_not_call_the_tests_path_a_default(relpath: str):
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    assert STALE_TESTS_PATH_DEFAULT_CLAIM not in text, (
        f"{relpath} 仍把命令文件路径写成「{STALE_TESTS_PATH_DEFAULT_CLAIM}」"
        "——它不是可覆写的默认值，是 constants 里的常量（没有第二个取值）"
    )
