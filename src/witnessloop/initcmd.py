"""``witnessloop init``：把 witnessloop 接入目标仓。

契约（design §5.1 / grill Q10）：
幂等 · 只增不改 · 不 auto-commit · 支持 ``--dry-run``。
写入 ``.witnessloop/policy.json``、``.witnessloop/init-manifest.json``、
一个极薄 caller workflow，外加一份**测试执行点**命令文件
（``constants.ADOPTER_TESTS_PATH``，change adopter-test-gate / issue #4）。

命令文件是**产物**，但它走一条**独立路径**：不进 ``desired_files()``、不进台账、
不参与冲突判定。理由是 ``desired_files()`` 同时喂**三个**消费者（写盘、台账、两条冲突
判定），种子一旦进去，接入方**改过命令之后** plain ``init`` 就会 exit 1（实测）——
而「改命令」是本 change 定义的**正常用法**，不能让工具唯一的升级入口对它坏掉。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import sys
from pathlib import Path

from witnessloop import __version__
from witnessloop import constants as C
from witnessloop import gitutil, policy
from witnessloop.hashing import sha256_bytes


def caller_workflow(gate_ref: str) -> str:
    """极薄的 GitHub caller workflow（design §5.1 / Q8）。"""
    return (
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
        f"    uses: {gate_ref}\n"
    )


def desired_files(gate_ref: str, policy_doc: dict | None = None) -> dict[str, str]:
    doc = policy.default_policy_doc() if policy_doc is None else policy_doc
    return {
        C.POLICY_PATH: policy.dumps(doc),
        C.GATE_WORKFLOW_PATH: caller_workflow(gate_ref),
    }


def tests_file_content(command: str | None) -> str:
    """命令文件的落盘内容：给定命令，或（``None``）哨兵占位；恒以单个换行结尾。"""
    body = C.ADOPTER_TESTS_SENTINEL if command is None else command.rstrip("\n")
    return body + "\n"


def write_tests_file(root: Path, content: str) -> None:
    path = root / C.ADOPTER_TESTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_policy_override(path_str: str) -> dict:
    """读 ``--policy`` 指向的文件 → policy dict。**轻校验**（design D2 / Q6b）。

    只要求「文件存在 + JSON 根是对象」；schema/字段的**语义**合法性刻意留给
    ``check`` 的 ``Policy.from_doc``——两处各造一套判定会引入漂移面。
    允许指向仓外路径（seed 不入库，常在仓外，见 Q5）。
    """
    path = Path(path_str)
    if not path.is_file():
        raise ValueError(f"--policy 文件不存在：{path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # `ValueError` 涵盖 `JSONDecodeError` 与 `UnicodeDecodeError`（本仓多数派 idiom）。
        raise ValueError(f"--policy 文件无法解析为 JSON：{exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("--policy 的 JSON 根必须是对象")
    return doc


def base_ref(root: Path) -> tuple[str | None, str | None]:
    """init **前**的 base ref（设计要求写进 init 台账）。非 git 仓则为 (None, None)。"""
    if not gitutil.is_repo(root):
        return None, None
    return gitutil.current_branch(root), gitutil.rev_parse(root, "HEAD")


def build_manifest(root: Path, desired: dict[str, str], gate_ref: str) -> dict:
    branch, sha = base_ref(root)
    created = [
        {"path": rel, "sha256": sha256_bytes(content.encode("utf-8"))}
        for rel, content in desired.items()
    ]
    # 台账把自己也列进创建清单（自引用 hash 无法自洽，标 self）。
    created.append({"path": C.INIT_MANIFEST_PATH, "sha256": None, "self": True})
    return {
        "schema": C.SCHEMA_INIT_MANIFEST,
        "witnessloop_version": __version__,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "base_ref": branch,
        "base_sha": sha,
        "gate_ref": gate_ref,
        "created_files": created,
    }


def render_diff(rel: str, current: str, desired: str) -> str:
    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            desired.splitlines(keepends=True),
            fromfile=f"a/{rel}（当前）",
            tofile=f"b/{rel}（witnessloop init 将写入）",
        )
    )


def conflicting_files(root: Path, desired: dict[str, str]) -> list[tuple[str, str, str]]:
    """``desired`` 里「磁盘已存在且内容不同」的文件 → ``(rel, 当前内容, 期望内容)``。

    init 的两处冲突判定（未接入时目标文件已存在、已接入时本次请求与已落地不同）
    共用这一处——两处各写一遍会漂（回归审阅 I3）。
    """
    out: list[tuple[str, str, str]] = []
    for rel, want in desired.items():
        path = root / rel
        if path.exists():
            try:
                current = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                # 读不出就判不了「冲突与否」⇒ fail-closed：抛给调用方报一行诊断并退 1。
                # **绝不**把 `None`/占位塞给 `render_diff`（那会产出 `AttributeError … splitlines`）。
                why = "无法解码" if isinstance(exc, UnicodeDecodeError) else "无法读取"
                raise ValueError(f"{rel} {why}：{exc}") from exc
            if current != want:
                out.append((rel, current, want))
    return out


def sync_caller_gate_ref(
    root: Path, manifest_path: Path, gate_ref: str, *, dry_run: bool
) -> str | None:
    """显式 ``--gate-ref``：重写 caller **并同步台账**（change gate-ref-pins-package / Q2 裁定 (a)）。

    只在**已接入**分支调用（调用方保证 ``manifest_path`` 是文件）。返回一句给用户的说明；
    ``None`` = 无需改动（台账里记的就是这个 ref，或盘上根本没有 caller）。

    ⚠️ **必须原子地同时改台账**：只重写 caller 会让「磁盘 ≠ 台账」——之后 plain ``init``
    走漂移分支退 1、``uninit`` 拒删退 1（实测，change `adopter-test-gate` 记过这个坑）。
    ⚠️ 盘上**没有** caller 时返回 ``None``：不凭空复活它，交给漂移分支响亮地报——
    「只增不改」在已接入分支里的含义就是**不新建**。
    """
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # 坏台账交给 `_already_initialized` 报（它有一手诊断）
    if not isinstance(manifest, dict) or manifest.get("gate_ref") == gate_ref:
        return None
    path = root / C.GATE_WORKFLOW_PATH
    if not path.is_file():
        return None

    if dry_run:
        print(f"init：[dry-run] 将重写 {C.GATE_WORKFLOW_PATH}（→ {gate_ref}）并同步台账")
        return f"[dry-run] 未落盘：{C.GATE_WORKFLOW_PATH} 与台账将一起改成 {gate_ref}"

    content = caller_workflow(gate_ref)
    path.write_text(content, encoding="utf-8")
    _set_ledger_gate_ref(manifest, gate_ref, sha256_bytes(content.encode("utf-8")))
    manifest_path.write_text(policy.dumps(manifest), encoding="utf-8")
    print(f"init：已重写 {C.GATE_WORKFLOW_PATH}（→ {gate_ref}）并同步台账")
    return f"{C.GATE_WORKFLOW_PATH} 与台账已改成 {gate_ref}"


def _set_ledger_gate_ref(manifest: dict, gate_ref: str, digest: str) -> None:
    """就地改台账：``gate_ref`` + caller 条目的 ``sha256``。

    条目缺失就补一条，且**插在 `self` 条目之前**（台账自己的那条约定俗成排最后）。
    """
    entries = manifest.get("created_files")
    if not isinstance(entries, list):
        entries = []
        manifest["created_files"] = entries
    for entry in entries:
        if (
            isinstance(entry, dict)
            and entry.get("path") == C.GATE_WORKFLOW_PATH
            and not entry.get("self")
        ):
            entry["sha256"] = digest
            break
    else:
        at = next(
            (i for i, e in enumerate(entries) if isinstance(e, dict) and e.get("self")),
            len(entries),
        )
        entries.insert(at, {"path": C.GATE_WORKFLOW_PATH, "sha256": digest})
    manifest["gate_ref"] = gate_ref


def ledger_gate_ref(manifest_path: Path) -> str | None:
    """台账里记录的 ``gate_ref``（重跑 ``init`` 时的缺省来源）；坏台账/不存在 → None。

    不读它的话，曾以非默认 ``--gate-ref`` 接入的仓，之后跑不带该 flag 的 `init`
    会因 caller workflow 内容不同被误判「冲突」——行为 fail-closed 但反直觉（回归审阅 I3）。
    """
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc.get("gate_ref") if isinstance(doc, dict) else None


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"init：目标目录不存在：{root}", file=sys.stderr)
        return C.EXIT_FAIL

    policy_override = getattr(args, "policy", None)
    policy_doc = None
    if policy_override:
        try:
            policy_doc = load_policy_override(policy_override)
        except ValueError as exc:
            print(f"init：{exc}", file=sys.stderr)
            return C.EXIT_FAIL

    tests_command = getattr(args, "test_command", None)
    no_tests = bool(getattr(args, "no_tests", False))
    if no_tests:
        # 显式 opt-out：不写命令文件 + 策略里写 `tests.disabled: true`。
        # ⚠️ **不是**「置空」：`Policy.from_doc` 沿既有惯例用 `or DEFAULT`（falsy 即回落）
        # ⇒ `""` / `null` / 缺省**都会**被读成「声明了执行点」。故唯一的 opt-out 字面是布尔真。
        policy_doc = (
            policy.default_policy_doc() if policy_doc is None else dict(policy_doc)
        )
        policy_doc["tests"] = {"disabled": True}

    manifest_path = root / C.INIT_MANIFEST_PATH
    # gate_ref 的缺省：已接入的仓沿用**台账**里的值（否则曾以非默认 --gate-ref 接入的仓，
    # 之后跑不带该 flag 的 init 会因 caller 内容不同被误判「冲突」）；未接入用出厂默认。
    # 显式传 --gate-ref 始终优先。
    gate_ref = args.gate_ref or ledger_gate_ref(manifest_path) or C.DEFAULT_GATE_REF
    desired = desired_files(gate_ref, policy_doc)

    # 命令文件写什么（`None` ⇒ 不写）。**不进 `desired_files()`** ⇒ 不进台账、不参与冲突判定。
    if no_tests:
        tests_write = None  # 显式 opt-out：不写（也不删接入方已有的那份）
    elif tests_command is not None:
        tests_write = tests_file_content(tests_command)  # 显式意图优先：**总是覆盖**
    elif (root / C.ADOPTER_TESTS_PATH).exists():
        tests_write = None  # 无 flag 且文件已在：不动它（幂等）
    else:
        tests_write = tests_file_content(None)  # 无 flag：种哨兵（未接线 ⇒ check 判红）

    if manifest_path.is_file():
        note = None
        if tests_write is not None:
            if args.dry_run:
                print(f"init：[dry-run] 将写入测试执行点 {C.ADOPTER_TESTS_PATH}")
                note = "[dry-run] 未落盘，其余文件无改动"
            else:
                # 写在前、其余判定照旧参与退出码（Z1/O2）：后续若报冲突，**不回滚**这次写入，
                # 但也绝不静默——这一行当场点名文件。
                write_tests_file(root, tests_write)
                why = (
                    "--test-command 覆盖已有内容"
                    if tests_command is not None
                    else "此前不存在"
                )
                print(f"init：已写入测试执行点 {C.ADOPTER_TESTS_PATH}（{why}）")
                note = "其余文件无改动，未 commit"
        # 显式 `--gate-ref` 的覆盖语义（Q2 裁定 (a)）。**只**在这个已接入分支里生效：
        # 未接入的仓走下面的「只增不改」——否则会静默覆盖新仓里外来的 caller
        # （`tests/test_init.py` 的「新仓目标文件已存在 ⇒ 冲突且整体不落盘」就是钉它的）。
        rewritten = (
            sync_caller_gate_ref(root, manifest_path, gate_ref, dry_run=args.dry_run)
            if args.gate_ref
            else None
        )
        if rewritten is None:
            return _already_initialized(root, desired, manifest_path, note=note)
        note = rewritten if note is None else f"{note}；{rewritten}"
        # caller 那条轴已按**显式意图**处理过 ⇒ 不再进冲突判定：`--dry-run` 下磁盘仍是旧内容，
        # 不滤掉它就会对一个「正要被自己改掉」的文件报红，用户无从判断。
        return _already_initialized(
            root, desired, manifest_path, note=note, ignore=(C.GATE_WORKFLOW_PATH,)
        )

    # 只增不改：目标文件已存在且内容不同 → 冲突，报 diff 并拒绝。
    try:
        conflicts = conflicting_files(root, desired)
    except ValueError as exc:
        print(f"init：{exc}", file=sys.stderr)
        return C.EXIT_FAIL
    if conflicts:
        print("init：检测到冲突（只增不改，拒绝覆盖已有文件）：", file=sys.stderr)
        for rel, current, want in conflicts:
            print(render_diff(rel, current, want), file=sys.stderr)
        return C.EXIT_FAIL

    if args.dry_run:
        print("[dry-run] init 将创建（不落盘、不 commit）：")
        for rel in desired:
            print(f"  + {rel}")
        print(f"  + {C.INIT_MANIFEST_PATH}")
        # 只列**真会写**的那些：文件已在就不会动它，列出来等于说会写（N3）。
        if tests_write is not None:
            print(f"  + {C.ADOPTER_TESTS_PATH}")
        return C.EXIT_PASS

    for rel, content in desired.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest_path.write_text(
        policy.dumps(build_manifest(root, desired, gate_ref)), encoding="utf-8"
    )

    print("init：已接入 witnessloop（文件未 commit，请人工审阅后提交）：")
    for rel in (*desired, C.INIT_MANIFEST_PATH):
        print(f"  + {rel}")
    if tests_write is not None:
        write_tests_file(root, tests_write)
        print(f"  + {C.ADOPTER_TESTS_PATH}")
    if policy_override:
        print(
            "init：policy 来自 --policy（**轻校验**：仅确认是 JSON 对象）；"
            "语义合法性由 `check` 兜底，`init` 不保证。"
        )
    if no_tests:
        # 判据用 `policy_override` 而不是 `policy_doc is not None`：`--no-tests` **也会**改
        # policy doc（加 `tests.disabled`），但它不是 `--policy`——否则会误打上面那句话。
        print(
            "init：--no-tests ⇒ 未写测试执行点，并在 policy 里写了 `tests.disabled: true`。"
            "⚠️ 它只关 `check` 的判定，门禁那一步照旧（文件在就跑、不在就跳过）。"
        )
    return C.EXIT_PASS


def _already_initialized(
    root: Path,
    desired: dict[str, str],
    manifest_path: Path,
    note: str | None = None,
    ignore: tuple[str, ...] = (),
) -> int:
    """幂等：已接入且台账未漂移 → 无改动退出 0；漂移 → 报 diff 退出 1。

    ``note``：本次对命令文件做了什么（已写 / dry-run 将写 / 没动）。非 ``None`` 时**不得**
    说「幂等，无改动」——工具不撒谎（B4b）；命令文件不在台账里，所以它**不是**漂移，
    退出码照旧（其余冲突判定照常参与）。

    ``ignore``：**调用方已按显式意图处理过**的那几条轴（目前只有 Q2 (a) 的 caller）——
    从「本次期望 vs 已落地」这条判定里排除掉。**不**影响「磁盘 vs 台账」那条（漂移判定照旧）：
    显式 `--gate-ref` 是一条升级入口，不是给手改文件兜底的后门。
    """
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"init：{C.INIT_MANIFEST_PATH} 无法解析：{exc}", file=sys.stderr)
        return C.EXIT_FAIL

    drift: list[tuple[str, str | None, str]] = []
    #: 内容已变但**读不出来**的那些（`drift` 里的 `current` 为 `None`）→ 报成因，不硬编 diff。
    unreadable: dict[str, str] = {}
    for entry in manifest.get("created_files", []):
        rel = entry.get("path")
        if not rel or entry.get("self") or rel == C.INIT_MANIFEST_PATH:
            continue
        path = root / rel
        if not path.exists():
            drift.append((rel, "", desired.get(rel, "") or ""))
            continue
        if entry.get("sha256") and sha256_bytes(path.read_bytes()) != entry["sha256"]:
            try:
                current = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                # 内容确实变了（sha 不符），但读不出来 ⇒ 只报成因，**不**把占位串当内容去 diff
                # （那会产出伪 diff，与 uninit 那条兄弟路径的 `! {rel} …` 形状也不一致）。
                unreadable[rel] = (
                    "无法解码" if isinstance(exc, UnicodeDecodeError) else "无法读取"
                )
                drift.append((rel, None, desired.get(rel, "")))
            else:
                drift.append((rel, current, desired.get(rel, "")))

    if drift:
        print(
            "init：已接入，但 init 创建的文件被改动过（拒绝覆盖）：",
            file=sys.stderr,
        )
        for rel, current, want in drift:
            if current is None:
                print(
                    f"  ! {rel} {unreadable[rel]}（内容已变，无法显示 diff）",
                    file=sys.stderr,
                )
            elif current == "" and want:
                print(f"  ! {rel} 缺失（台账记录它应存在）", file=sys.stderr)
            elif want:
                print(render_diff(rel, current, want), file=sys.stderr)
            else:
                print(f"  ! {rel} 内容与台账 hash 不符", file=sys.stderr)
        return C.EXIT_FAIL

    # R2 修复：台账未漂移、但**本次请求的内容**与已落地不同 → 冲突，**不得**静默忽略。
    # 与上面「磁盘 vs 台账」正交：上面查「已落地的文件被手改没」；这里查「这次想写的
    # 是不是另一份」（如 ``--policy`` 换了内容、``--gate-ref`` 换了）。
    # 早先只看台账 hash，于是「已接入后再 init --policy <不同>」会被判幂等并 exit 0
    # ——用户的 policy 被悄悄忽略（change dogfood-bootstrap 对抗验证 CRQ-B / R2）。
    try:
        conflicts = conflicting_files(root, desired)
    except ValueError as exc:
        print(f"init：{exc}", file=sys.stderr)
        return C.EXIT_FAIL
    conflicts = [item for item in conflicts if item[0] not in ignore]
    if conflicts:
        if ignore:
            # 组合语义写死（R2 的 L4）：`--gate-ref` 那一半**已经落盘且不回滚**，
            # 下面报的是**别的**轴。不写这句的话，用户会以为「什么都没发生」并跑去删 policy。
            print(
                f"init：注意——{'、'.join(ignore)} 已按显式 `--gate-ref` 处理（**已落盘、不回滚**）；"
                "下面报的是**别的**文件：",
                file=sys.stderr,
            )
        print(
            "init：检测到冲突（已接入，但本次指定的内容与已落地不同；"
            "只增不改，拒绝覆盖。要更换 policy 请先 `uninit`）：",
            file=sys.stderr,
        )
        for rel, current, want in conflicts:
            print(render_diff(rel, current, want), file=sys.stderr)
        return C.EXIT_FAIL

    if note:
        print(f"init：已接入 witnessloop（{note}）。")
    else:
        print("init：已接入 witnessloop（幂等，无改动）。")
    return C.EXIT_PASS
