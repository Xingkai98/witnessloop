"""change 目录契约（OpenSpec 形状）+ review manifest 校验。

D2：change 目录必须满足 proposal/design/tasks/specs + reviews/。
D3：review manifest 存在，且 hash **绑定真实 artifact 字节**
    （base/head sha + tasks/spec/report hash）。
D4：``reviewer_run_id != author_run_id``。

能力边界（design §5.3）：hash 绑定证明「证据之间没漂移」；身份字段是自由文本，
v1 不做语义绑定——**防漂移，不防伪造**。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from witnessloop import constants as C
from witnessloop import gitutil
from witnessloop import paths as pathutil
from witnessloop.hashing import sha256_tree
from witnessloop.policy import Policy


@dataclass(frozen=True)
class Finding:
    """一条校验失败。``path`` 是**仓根相对**路径，方便 CI 里点回去。"""

    path: str
    message: str


def change_dir(root: Path, policy: Policy, change_id: str) -> Path:
    return root / policy.changes_root / change_id


def archived_change_dir(root: Path, policy: Policy, name: str) -> Path:
    """`<changes_root>/archive/<name>`——归档 change 的目录。"""
    return root / policy.changes_root / C.ARCHIVE_DIR_NAME / name


@dataclass(frozen=True)
class ChangeTarget:
    """本次 diff 触及的**一个** change（active 或归档）。

    归档态与 active 走**同一套**校验（与 active 同构），只差两处：解析到的 `directory`
    与 `change_id` 的**接受集合**（D8 的别名：归档前产出的 manifest 带的是源 id）。

    ⚠️ 映射**以目录为键**：同一个单段 id 可以同时来自 active 目录与归档授予，
    两份都要校验（见 `change_targets`）。
    """

    change_id: str
    directory: Path
    label: str
    accepted_change_ids: frozenset[str]
    source_change_id: str | None = None

    @property
    def archived(self) -> bool:
        return self.source_change_id is not None


def is_archive_move(change, changes_root: str) -> bool:
    """`git mv <changes_root>/<id>/… <changes_root>/archive/<id>/…` —— 归档动作。

    只认**纯改名**（状态 ``R100``，没带内容改动）：带走改动的移动不算归档，
    仍须解释事件。旧路径必须在 active 目录（不能本来就是 archive 里的东西），
    新路径必须落在 ``<changes_root>/archive/**``。
    """
    if change.status != "R100" or not change.old_path:
        return False
    root = changes_root.rstrip("/")
    new = pathutil.normalize(change.path)
    old = pathutil.normalize(change.old_path)
    archive = f"{root}/{C.ARCHIVE_DIR_NAME}"
    return (
        pathutil.matches(new, f"{archive}/**")
        and pathutil.matches(old, f"{root}/*/**")
        and not pathutil.matches(old, f"{archive}/**")
    )


def changed_change_ids(changes, changes_root: str) -> list[str]:
    """从 diff 里挑出被触碰的 **active** change id。

    归档 move 的两端都要排除：目标在 ``archive/`` 下（否则 ``archive`` 会被当成
    一个 change id，然后报「缺少必需件 proposal.md」），来源是那个已经搬走的
    active 目录（它的内容已随归档离开 active，不该再按 active 契约校验）。

    ⚠️ **归档授予不在这里**：归档 move 带走的那个 change 由 ``archive_grant`` /
    ``change_targets`` 放回集合（id = 归档目录名）——本函数只认 active 路径首段。
    """
    root = changes_root.rstrip("/")
    prefix = root + "/"
    archived_sources = {
        pathutil.normalize(change.old_path)
        for change in changes
        if change.old_path and is_archive_move(change, changes_root)
    }
    ids: set[str] = set()
    for change in changes:
        for path in (change.path, change.old_path):
            if not path:
                continue
            normalized = pathutil.normalize(path)
            if normalized in archived_sources:
                continue
            if pathutil.matches(normalized, f"{root}/{C.ARCHIVE_DIR_NAME}/**"):
                continue
            if normalized.startswith(prefix):
                head = normalized[len(prefix) :].split("/", 1)[0]
                if head:
                    ids.add(head)
    return sorted(ids)


def archive_grant(change, changes_root: str) -> tuple[str, str] | None:
    """这条 diff 记录是不是一次**授予资格**的归档 move？是 ⇒ `(源 id, 归档目录名)`。

    两道闸：

    1. `is_archive_move`（R100 纯改名 + 源在 active + 落点在 `archive/`）；
    2. **目标目录名认得源 id**：`<name> == <源id>` 或 `<name>.endswith("-" + <源id>)`
       （纯字符串比对，**不解析日期**）。

    第 2 道挡的是「把 active change 的**单个文件**改入一个**已存在的**归档目录」：
    那种 move 也是 R100，会把资格**凭空授予目标目录**，而源 change 因 `archived_sources`
    （见 `changed_change_ids`）被排除、**静默逃检**。名不认得 ⇒ **不授予**（回落到
    「什么都不建」的行为 ⇒ `_require_change` 照样命中，fail-closed）。
    """
    if not is_archive_move(change, changes_root):
        return None
    root = changes_root.rstrip("/")
    new = pathutil.normalize(change.path)
    old = pathutil.normalize(change.old_path or "")
    prefix = f"{root}/{C.ARCHIVE_DIR_NAME}/"
    if not new.startswith(prefix) or not old.startswith(root + "/"):
        return None  # pragma: no cover - is_archive_move 已保证；双保险
    name = new[len(prefix):].split("/", 1)[0]
    source = old[len(root) + 1:].split("/", 1)[0]
    if not name or not source:
        return None
    if name == source or name.endswith("-" + source):
        return source, name
    return None


def change_targets(root: Path, policy: Policy, changes) -> list[ChangeTarget]:
    """本次 diff 触及的 change（active ∪ 归档授予），**以目录为键**。

    ⚠️ 返回**列表**、不是 `dict[change_id] -> directory`：同一个单段 id 可以同时来自
    active 目录与归档授予（构造：同 PR 内同名 move + 新增 active 子文件）——两份都要校验；
    写成 dict 会**静默丢掉一份**（丢掉哪份取决于实现），而那条 diff 是攻击者可构造的。
    """
    root_rel = policy.changes_root.rstrip("/")
    targets = [
        ChangeTarget(
            change_id=change_id,
            directory=change_dir(root, policy, change_id),
            label=f"{root_rel}/{change_id}",
            accepted_change_ids=frozenset({change_id}),
        )
        for change_id in changed_change_ids(changes, policy.changes_root)
    ]
    grants: dict[str, str] = {}
    for change in changes:
        grant = archive_grant(change, policy.changes_root)
        if grant is not None:
            grants.setdefault(grant[1], grant[0])
    for name in sorted(grants):
        source = grants[name]
        targets.append(
            ChangeTarget(
                change_id=name,
                directory=archived_change_dir(root, policy, name),
                label=f"{policy.archive_root}/{name}",
                # D8 别名：归档**前**产出的 manifest 带的是源 id，归档**后**产出的是目录名。
                accepted_change_ids=frozenset({name, source}),
                source_change_id=source,
            )
        )
    return targets


def validate_change_dir(
    root: Path,
    policy: Policy,
    change_id: str,
    *,
    directory: Path | None = None,
    label: str | None = None,
) -> list[Finding]:
    """D2：OpenSpec 形状的 change 目录契约。

    `directory` / `label` 缺省 = active 路径（`changes_root/<id>`）；归档 target 由
    `change_targets` 传**解析后的归档目录**——判定本身与 active **同一套**。
    """
    directory = directory if directory is not None else change_dir(root, policy, change_id)
    rel = label or f"{policy.changes_root.rstrip('/')}/{change_id}"
    if not directory.is_dir():
        return [Finding(rel, "change 目录不存在（diff 里出现了它的文件，但目录不在工作树中）")]

    findings: list[Finding] = []
    for artifact in policy.required_artifacts:
        if not (directory / artifact).exists():
            findings.append(Finding(rel, f"缺少必需件 {artifact}"))
    return findings


_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")


@dataclass(frozen=True)
class SpanScope:
    """核对审阅跨度（D3 的 revision 绑定）所需的上下文。

    ``pr_paths`` 是**本次 PR 自身的变更集**（``base...head`` 的文件路径）。
    判定 stale 时必须与它求交——否则被检 head 是一个 merge commit 时
    （``pull_request`` 事件下 ``actions/checkout`` 的默认检出对象），
    顺着 merge 进来的 **base 侧**改动会被误判成「审阅后又改了代码」。
    """

    checked_head: str
    pr_paths: frozenset[str]
    evidence_patterns: tuple[str, ...]


def validate_review_manifests(
    root: Path,
    policy: Policy,
    change_id: str,
    *,
    scope: SpanScope,
    directory: Path | None = None,
    label: str | None = None,
    accepted_change_ids: frozenset[str] | None = None,
) -> list[Finding]:
    """D3 + D4：review manifest 存在、hash 绑定、base/head 真绑；reviewer ≠ author。

    `directory` / `label` / `accepted_change_ids` 同 `validate_change_dir` 与 D8 的别名——
    归档 target 只是换了个目录与名字集合，**判定逻辑一份**。
    """
    directory = directory if directory is not None else change_dir(root, policy, change_id)
    rel = label or f"{policy.changes_root.rstrip('/')}/{change_id}"
    manifests = sorted(directory.glob(policy.review_manifest_glob))
    if not manifests:
        return [
            Finding(
                rel,
                "缺少 review manifest（审阅证据必须「报告 + manifest」成对，"
                f"glob={policy.review_manifest_glob}）",
            )
        ]

    findings: list[Finding] = []
    bound: set[Path] = set()
    for manifest_path in manifests:
        findings.extend(
            _validate_one(
                root, directory, rel, manifest_path, scope,
                accepted_change_ids=accepted_change_ids,
            )
        )
        report = _bound_report(directory, manifest_path)
        if report is not None:
            bound.add(report)

    # **逐 manifest** 处理：某份 manifest 贡献不了绑定，就只是它自己少一条——
    # **绝不**因此跳过整条孤儿规则。整体跳过会成为「一份特制 manifest 关掉规则」的
    # 开关（回归审阅 §3.2/§4），原则是**宁多报不漏报**。
    findings.extend(_check_orphan_reports(directory, rel, bound))
    return findings


def resolve_report_path(directory: Path, raw) -> Path | None:
    """把 manifest 的 `report_path` 解析成 change 目录内的**规范**路径。

    `check` 的 hash 校验、孤儿绑定、以及 `manifest build` 的落盘**共用这一个实现**。
    口径分歧会同时造成两类 bug——**漏报**（一边认、一边不认 → 规则被跳过）与
    **假阳性**（`build` 接受 `reviews/./x.md`、`check` 认不出 → 误报孤儿），两条都踩过。

    返回 None = 不能作为有效的报告引用（空 / 逃逸出 change 目录）。
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    base = directory.resolve()
    candidate = (base / text).resolve()
    if not pathutil.is_within(candidate, base):
        return None
    return candidate


def _bound_report(directory: Path, manifest_path: Path) -> Path | None:
    """这份 manifest 绑定了哪个报告（**解析后**的绝对路径）；取不到则 None。"""
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # ValueError 涵盖 JSON 语法坏**与**非法 UTF-8（后者此前漏捕 ⇒ 崩溃）。
        return None
    if not isinstance(doc, dict):
        return None
    return resolve_report_path(directory, doc.get("report_path"))


def _check_orphan_reports(
    directory: Path, rel_change: str, bound: set[Path]
) -> list[Finding]:
    """`reviews/**/*.md` 里每个报告都必须被某份 manifest 的 `report_path` 引用。

    否则会出现「只绑一份、把另一份晾着」的缺口——那份报告可以随便漂移而门禁不管。

    **只做文件名交叉引用**，不解析报告正文。两侧都取**解析后**的路径来比：
    这样 `./` / `//` / `..` / 反斜杠字面名 / 符号链接都不会造成误判。
    多份 manifest 指向同一个报告不额外报错（保持简单）；
    `reviews/` 下没有 `.md` 报告时不报孤儿。
    """
    reviews = directory / "reviews"
    if not reviews.is_dir():
        return []

    # 目录名以 `.md` 结尾不算报告（回归审阅 §3.4）；链接与目标解析到同一条目（§3.5）。
    reports: dict[Path, str] = {}
    for report in sorted(reviews.rglob("*.md")):
        if not report.is_file():
            continue
        reports.setdefault(report.resolve(), report.relative_to(directory).as_posix())

    findings: list[Finding] = []
    for resolved, rel_report in reports.items():
        if resolved in bound:
            continue
        findings.append(
            Finding(
                f"{rel_change}/{rel_report}",
                f"孤儿报告：{rel_report} 未被任何 manifest 绑定"
                "（每个审阅报告都要各配一份 manifest，见 docs/gate.md §3）",
            )
        )
    return findings


def _validate_one(
    root: Path,
    directory: Path,
    rel_change: str,
    manifest_path: Path,
    scope: SpanScope,
    *,
    accepted_change_ids: frozenset[str] | None = None,
) -> list[Finding]:
    manifest_rel = f"{rel_change}/{manifest_path.relative_to(directory).as_posix()}"
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # 同上：JSON 坏与字节坏**同归**于这条 finding（它**点名文件**）。
        return [Finding(manifest_rel, f"manifest 无法解析：{exc}")]
    if not isinstance(doc, dict):
        return [Finding(manifest_rel, "manifest 根必须是 JSON 对象")]

    findings: list[Finding] = []

    missing = [
        field
        for field in C.REVIEW_MANIFEST_REQUIRED_FIELDS
        if not str(doc.get(field) or "").strip()
    ]
    if missing:
        findings.append(Finding(manifest_rel, f"manifest 缺字段：{', '.join(missing)}"))
        # 缺字段时后面没法可靠比对，直接返回。
        return findings

    # change 的身份 = **change 目录的名字**（缺省口径）。归档态多一个**别名**（D8）：
    # 归档**前**产出的 manifest 带的是**源 id**（一次改名把两个名字连起来）——
    # 少了这个别名，归档那一刻既有 manifest 会全部判「与目录不符」，而唯一的补救
    # 「用归档目录名重建」在同一个 diff 里会毁掉 `R100`（见 `design.md §1.5`）。
    accepted = (
        accepted_change_ids
        if accepted_change_ids is not None
        else frozenset({rel_change.rsplit("/", 1)[-1]})
    )
    if doc.get("change_id") and doc["change_id"] not in accepted:
        findings.append(
            Finding(manifest_rel, f"manifest.change_id={doc['change_id']!r} 与目录不符")
        )

    # D4：强制 reviewer ≠ author。注意口径（#3 Q3）：**兜底路径下两者结构性不同**，
    # 所以这道校验只挡「**显式**把同一个值喂给两个角色」（如只设共享的
    # WITNESSLOOP_RUN_ID），**不证独立 run**，也不挡蓄意伪造。
    if doc["reviewer_run_id"] == doc["author_run_id"]:
        findings.append(
            Finding(
                manifest_rel,
                "reviewer_run_id == author_run_id：审阅者必须独立于作者",
            )
        )

    # D3：hash 绑定真实 artifact 字节；base/head 绑定真实 git revision。
    findings.extend(_check_hashes(directory, manifest_rel, doc))
    findings.extend(_check_git_span(root, manifest_rel, doc, scope))
    return findings


def _check_git_span(
    root: Path, manifest_rel: str, doc: dict, scope: SpanScope
) -> list[Finding]:
    """D3 的 revision 绑定（tasks.md：「base/head sha + ...」）。

    一条 manifest 不可能写下**自己所在提交**的 sha（自指），所以「head_sha 等于本次
    被检 revision」在字面上不可满足。等价且可满足的规则是：head_sha 必须是本次被检
    head 的**祖先**，且从 head_sha 到被检 head 之间**只允许出现证据文件**。
    这等价于「head_sha 是最后一个非证据 revision」——审阅之后又落了代码即判 stale。

    约定（docs/gate.md §3）：**先提交内容，再单独提交证据**。
    """
    findings: list[Finding] = []
    base_sha = doc["base_sha"]
    head_sha = doc["head_sha"]

    # 字段名叫 *_sha：先卡形状。`rev_parse` 什么 ref 表达式都收（main、HEAD~3、
    # tag……），不卡的话字段语义会松到没有意义。
    for field, value in (("base_sha", base_sha), ("head_sha", head_sha)):
        # isinstance 守卫不能省：manifest 是 agent 可写的 JSON，字段可能是数字/
        # 布尔/列表，直接喂给 re.match 会抛未捕获 TypeError（栈回溯崩溃）。
        # 非字符串一律走干净 finding——fail-closed 但要**受控**。
        if not isinstance(value, str) or not _SHA_RE.match(value):
            findings.append(
                Finding(
                    manifest_rel,
                    f"{field}={value!r} 不是一个 git sha（40 位小写十六进制）",
                )
            )
    if findings:
        return findings

    if gitutil.rev_parse(root, base_sha) is None:
        findings.append(
            Finding(
                manifest_rel,
                f"base_sha={base_sha} 不是本仓的提交（证据必须绑定真实 revision）",
            )
        )

    if gitutil.rev_parse(root, head_sha) is None:
        findings.append(
            Finding(
                manifest_rel,
                f"head_sha={head_sha} 不是本仓的提交（证据必须绑定真实 revision）",
            )
        )
        return findings

    if not gitutil.is_ancestor(root, head_sha, scope.checked_head):
        findings.append(
            Finding(
                manifest_rel,
                f"head_sha={head_sha} 不是本次被检 revision {scope.checked_head} 的祖先"
                "——审阅的是别的 revision",
            )
        )
        return findings

    try:
        delta = gitutil.diff_names(root, head_sha, scope.checked_head)
    except gitutil.GitError as exc:
        findings.append(Finding(manifest_rel, f"无法核对审阅跨度：{exc}"))
        return findings

    # 只关心**本次 PR 自己**改过的文件：checked_head 可能是 merge commit
    # （pull_request 事件下 actions/checkout 的默认检出对象），两点 diff 会把
    # 顺着 merge 进来的 base 侧改动也算进 delta——那是别人改的，不是本 PR 漂移。
    stray = sorted(
        path
        for path in delta
        if pathutil.normalize(path) in scope.pr_paths
        and not pathutil.matches_any(path, scope.evidence_patterns)
    )
    if stray:
        shown = ", ".join(stray[:5]) + ("…" if len(stray) > 5 else "")
        findings.append(
            Finding(
                manifest_rel,
                f"审阅的是旧 revision：head_sha={head_sha} 之后又改动了非证据文件：{shown}",
            )
        )
    return findings


def _check_hashes(directory: Path, manifest_rel: str, doc: dict) -> list[Finding]:
    findings: list[Finding] = []

    # 与孤儿绑定、`manifest build` 共用同一个解析器——口径分歧会让规则被绕过。
    report_path = resolve_report_path(directory, doc["report_path"])
    if report_path is None:
        findings.append(
            Finding(
                manifest_rel,
                f"report_path={doc['report_path']!r} 逃逸出 change 目录",
            )
        )
    elif not report_path.is_file():
        findings.append(
            Finding(manifest_rel, f"报告不存在：{doc['report_path']}")
        )
    elif sha256_tree(report_path) != doc["report_hash"]:
        findings.append(
            Finding(
                manifest_rel,
                f"report_hash 不匹配：报告 {doc['report_path']} 的字节与 manifest 记录不符",
            )
        )

    for field, artifact in C.HASHED_ARTIFACTS:
        target = directory / artifact
        if not target.exists():
            findings.append(Finding(manifest_rel, f"{artifact} 不存在，无法校验 {field}"))
            continue
        if sha256_tree(target) != doc[field]:
            findings.append(
                Finding(
                    manifest_rel,
                    f"{field} 不匹配：{artifact} 的字节与 manifest 记录不符"
                    "（evidence 与 artifact 已漂移）",
                )
            )

    # diff_hash 是 informational（design §5.3）：在位即可，不校验内容。
    return findings
