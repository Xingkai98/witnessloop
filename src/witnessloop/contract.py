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
import posixpath
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
    #: 该 target 是不是**本次到达的归档目录**（`archive/<name>/`）。出生即归档没有源 id，
    #: 故**不能**用它推 `archived`（旧实现对「无源的到达」会漏标）。
    archived: bool = False


#: 空 blob 的 sha1（git 的常量）——判据 5 里「内容为空者豁免」用。
EMPTY_BLOB_SHA = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


class TreeView:
    """到达判定所需的**树读取口**（注入用：真实现是 `gitutil.GitTree`，测试用假树）。

    四个方法对应 `design.md §2 D7` 的三种 `ls-tree` 写法 + 读正文。
    """

    def entry(self, rev: str, path: str):  # -> TreeEntry | None
        raise NotImplementedError

    def children(self, rev: str, path: str):  # -> list[TreeEntry]
        raise NotImplementedError

    def walk(self, rev: str, path: str):  # -> list[TreeEntry]
        raise NotImplementedError

    def read(self, rev: str, path: str):  # -> str | None
        raise NotImplementedError


@dataclass(frozen=True)
class Arrival:
    """一个**本次到达**的归档 change 目录（`design.md §2 D1` 五条判据筛出来的）。

    `records` 是**到达组** = 本次 diff 里 `new_path` 落在该目录之下的记录。
    `source_ids` 是到达组里出现过的**全部**源 id（用户 2026-10-15 裁定删掉名识别守卫 ⇒ 不再按名字过滤）。
    """

    name: str
    directory: str          # 仓根相对：`<changes_root>/archive/<name>`
    records: tuple          # tuple[gitutil.Change, ...]
    source_ids: frozenset[str]


def under_path(path: str, prefix: str) -> bool:
    """`path` 是否等于 `prefix` 或落在它之下（两者都先 normalize，**只按路径分量**比）。"""
    p = pathutil.normalize(path).rstrip("/")
    q = pathutil.normalize(prefix).rstrip("/")
    return p == q or p.startswith(q + "/")


def _resolve_rel(base_dir: str, target: str) -> str | None:
    """把 `report_path` / 符号链接文本解析成**仓根相对**路径（posix 规范化 `..`）。

    逃出仓根（绝对路径 / `..` 越过根）⇒ None。与 `resolve_report_path` 同一口径
    （那里是 `Path.resolve()` + `is_within`；这里是字符串版，便于纯函数单测）。
    """
    text = target.strip()
    if not text or text.startswith("/"):
        return None
    joined = posixpath.normpath(posixpath.join(base_dir, text))
    if joined == ".." or joined.startswith("../"):
        return None
    return joined


def _content_provenance_ok(
    view: TreeView,
    rev: str,
    directory: str,
    base_blobs: set[str],
    rename_dests: set[str],
    manifest_glob: str,
) -> bool:
    """判据 5：`Ev(A)` 里**实际交付的每个文件**都必须是「新内容」或「本次搬过来的」。

    `Ev(A)` 的**根**（`design.md §2 D1`，由数据推导、不按路径前缀硬编码）：
    `HASHED_ARTIFACTS` 的 artifact 路径**整体** + `<A>/reviews` + 字面命中 `review_manifest_glob` 的 manifest；
    再叠上**每份 manifest 的 `report_path` 目标**（递归到不动点）。

    展开规则（**目录与符号链接都要展开到文件**——实现审阅实测过：只比 tree/blob sha 时，
    把 `reviews/` 做成 `ln -s _r reviews` 就能把别处的现成报告整份复用且判绿）：

    * **目录** ⇒ 其下全部文件逐个参与比对；
    * **符号链接** ⇒ 按解析后的内容参与比对（目标可能是文件或目录，见上）；
    * **未跟踪 / 悬空 / 解析到仓根之外**，或**`<A>` 下任何位置**出现 **gitlink** ⇒ fail-closed。
    """
    import fnmatch

    # 0) `<A>` 下**任何位置**的 gitlink ⇒ fail-closed（不只是 `Ev(A)` 成员）。
    if any(row.is_gitlink for row in view.walk(rev, directory)):
        return False

    roots = {f"{directory}/{artifact}" for _field, artifact in C.HASHED_ARTIFACTS}
    roots.add(f"{directory}/reviews")
    for row in view.walk(rev, directory):
        rel = row.path[len(directory) + 1:]
        if fnmatch.fnmatch(rel, manifest_glob):
            roots.add(row.path)

    def is_manifest(seen: str) -> bool:
        """**看见的路径**（不是解析后的真身）按 glob 是不是一份 manifest。

        ⚠️ 门禁是从**文件系统** glob `reviews/*.manifest.json` 的 ⇒ 一个**名叫** `x.manifest.json`
        的符号链接同样被读到（读的是目标的内容）⇒ 这里的判据必须用**看见的路径**，
        否则「manifest 做成符号链接、`report_path` 指到别处」会让借来的报告永不入比对集（实现审阅的 H2）。
        """
        return under_path(seen, directory) and fnmatch.fnmatch(seen[len(directory) + 1:], manifest_glob)

    def queue_report(seen: str, content_src: str) -> None:
        try:
            doc = json.loads(view.read(rev, content_src) or "")
        except ValueError:
            return
        if not isinstance(doc, dict):
            return
        resolved = _resolve_rel(directory, str(doc.get("report_path") or ""))
        if resolved is not None and under_path(resolved, directory):
            queue.append((resolved, resolved))

    seen_paths: set[str] = set()
    compared: set[str] = set()
    queue: list[tuple[str, str]] = [(path, path) for path in sorted(roots)]
    while queue:
        seen, content_src = queue.pop()
        if seen in seen_paths:
            continue
        seen_paths.add(seen)
        entry = view.entry(rev, seen)
        if entry is None:
            continue
        if entry.is_gitlink:
            return False
        if entry.is_symlink:
            target = _resolve_rel(posixpath.dirname(seen), view.read(rev, seen) or "")
            if target is None or view.entry(rev, target) is None:
                return False                        # 逃出仓根 / 悬空 / 未被 git 跟踪
            if is_manifest(seen):
                queue_report(seen, target)          # 正文按**内容源**（= 目标）读
            if under_path(target, directory):
                queue.append((target, target))      # 目标并入 Ev(A)（按目标自身路径比对）
            elif _is_reused(view.entry(rev, target).sha, seen, base_blobs, rename_dests):
                # 逃出 A：按**目标**的 blob 比对；(b) 的判定对象仍是**链接自身**的路径。
                return False
            continue
        if entry.type == "tree":
            queue.extend((row.path, row.path) for row in view.walk(rev, seen))
            continue
        if seen not in compared:
            compared.add(seen)
            if _is_reused(entry.sha, seen, base_blobs, rename_dests):
                return False
        if is_manifest(seen):
            queue_report(seen, content_src)
    return True


def _is_reused(sha: str, path: str, base_blobs: set[str], rename_dests: set[str]) -> bool:
    """这份内容是不是「基准树里已有、且不是本次搬过来的」⇒ 白捡。"""
    return (
        sha != EMPTY_BLOB_SHA     # 空文件豁免
        and sha in base_blobs
        and pathutil.normalize(path) not in rename_dests
    )


def archive_arrivals(
    changes,
    policy: Policy,
    view: TreeView,
    base_rev: str,
    head_rev: str,
) -> list[Arrival]:
    """本次 diff 里**到达**的归档 change 目录（`design.md §2 D1`，判据 1 / 2 / 3 / 5）。

    ⚠️ **基准 revision 必须与 `changed_files` 同源**：传进来的 `base_rev` 应当是
    `git merge-base(base, head)` 的 sha（`checkcmd` 负责算），不是 `base` ref 自身的树。
    """
    root = policy.changes_root.rstrip("/")
    archive_root = f"{root}/{C.ARCHIVE_DIR_NAME}"
    required = tuple(a for a in policy.required_artifacts if a.strip() and a.strip() != ".")
    base_blobs = {row.sha for row in view.walk(base_rev, root)}
    rename_dests = {
        pathutil.normalize(change.path) for change in changes if change.status[:1] in ("R", "C")
    }

    arrivals: list[Arrival] = []
    for child in view.children(head_rev, archive_root):
        if child.type != "tree":
            continue                                   # 候选只取 tree（`archive/notes.md` 不算）
        name = child.path[len(archive_root) + 1:]
        if not name or "/" in name:
            continue
        directory = child.path
        # 判据 1：基准树里该路径**完全没有 entry**（blob 也算「有」）。
        if view.entry(base_rev, directory) is not None:
            continue
        # 判据 2：head 里是 tree（已知）+ 含**全部**必需件（与契约门同一判定语义：路径存在）。
        present = {row.path for row in view.walk(head_rev, directory)}
        if not all(
            any(p == f"{directory}/{a}" or p.startswith(f"{directory}/{a}/") for p in present)
            for a in required
        ):
            continue
        group = tuple(
            change for change in changes if under_path(pathutil.normalize(change.path), directory)
        )
        # 判据 3：不是从另一个归档目录改名而来。
        if any(
            change.old_path and under_path(pathutil.normalize(change.old_path), archive_root)
            for change in group
        ):
            continue
        # 判据 5：内容来源（`Ev(A)` 逐项：新内容 or 本次搬来的）。
        if not _content_provenance_ok(
            view, head_rev, directory, base_blobs, rename_dests, policy.review_manifest_glob
        ):
            continue
        sources = {
            pathutil.normalize(change.old_path)[len(root) + 1:].split("/", 1)[0]
            for change in group
            if change.old_path
            and under_path(pathutil.normalize(change.old_path), root)
            and not under_path(pathutil.normalize(change.old_path), archive_root)
        }
        arrivals.append(
            Arrival(name=name, directory=directory, records=group, source_ids=frozenset(sources))
        )
    return arrivals


def near_miss_archives(policy: Policy, view: TreeView, base_rev: str, head_rev: str) -> list[str]:
    """「像归档目录、但缺必需件」的候选名（**只为诊断文案**，不参与任何判定）。

    R3 的 E-2：判据 2 收紧后，件不齐的到达目录**不是** target ⇒ 只报「没有任何 change 目录」，
    而**不**点名缺的那一件——对「已经建了归档目录、只是少写一件」的接入方是误导性文案。
    """
    root = policy.changes_root.rstrip("/")
    archive_root = f"{root}/{C.ARCHIVE_DIR_NAME}"
    required = tuple(a for a in policy.required_artifacts if a.strip() and a.strip() != ".")
    out: list[str] = []
    for child in view.children(head_rev, archive_root):
        if child.type != "tree":
            continue
        name = child.path[len(archive_root) + 1:]
        if not name or "/" in name or view.entry(base_rev, child.path) is not None:
            continue
        present = {row.path for row in view.walk(head_rev, child.path)}
        missing = [
            a for a in required
            if not any(
                p == f"{child.path}/{a}" or p.startswith(f"{child.path}/{a}/") for p in present
            )
        ]
        if missing:
            out.append(f"{name}（缺 {'、'.join(missing)}）")
    return sorted(out)


def changed_change_ids(
    changes, policy: Policy, arrivals, view: TreeView, head_rev: str
) -> list[str]:
    """从 diff 里挑出被触碰的 **active** change id。

    排除两类路径：

    * 落在 `archive/` 下的（否则 `archive` 会被当成一个 change id）；
    * 属于**到达组**、且其源 change 目录在 head 树里**已不存在**的路径——`R`/`C` 记录的
      `old_path`，**以及 `D` 侧记录的 `path`**（`gitutil._parse_name_status` 对 `D` 记录把被删路径
      放在 `path`、`old_path` 留空 ⇒ 只认 `old_path` 会让「move + 整体重写」留下幽灵 id）。

    ⚠️ 源目录**仍在 head 里**（只搬走了部分文件）⇒ **不排除**：那个 change 照旧按 active 契约校验
    （「源 change 不得静默逃检」）。⚠️ 本条是这条路上**唯一**的保护——原来的名识别守卫已由
    用户 2026-10-15 裁定删除。
    """
    root = policy.changes_root.rstrip("/")
    prefix = root + "/"
    archive_root = f"{root}/{C.ARCHIVE_DIR_NAME}"
    # 「已搬走」的源 id = 到达组里出现过的源，且它的目录在 head 树里**已不存在**。
    # ⚠️ 判定要同时看 `R`/`C` 记录的 `old_path` 与 **`D` 侧记录的 `path`**：
    # `gitutil._parse_name_status` 对 `D` 记录把被删路径放在 `path`（`old_path` 留空），
    # 「move + 被搬文件整体重写」正是这种形态（R3 的 A4）。
    moved_sources: set[str] = set()
    for arrival in arrivals:
        for change in arrival.records:
            candidates = [change.old_path]
            if not change.old_path:
                candidates.append(change.path)
            for raw in candidates:
                if not raw:
                    continue
                normalized = pathutil.normalize(raw)
                if not normalized.startswith(prefix) or under_path(normalized, archive_root):
                    continue
                src = normalized[len(prefix):].split("/", 1)[0]
                if view.entry(head_rev, f"{root}/{src}") is None:
                    moved_sources.add(src)
    excluded: set[str] = set()
    for change in changes:
        for path in (change.old_path, change.path):
            if not path:
                continue
            normalized = pathutil.normalize(path)
            if under_path(normalized, archive_root) or not under_path(normalized, root):
                continue
            if normalized[len(prefix):].split("/", 1)[0] in moved_sources:
                excluded.add(normalized)
    ids: set[str] = set()
    for change in changes:
        for path in (change.path, change.old_path):
            if not path:
                continue
            normalized = pathutil.normalize(path)
            if normalized in excluded:
                continue
            if under_path(normalized, archive_root):
                continue
            if normalized.startswith(prefix):
                head = normalized[len(prefix):].split("/", 1)[0]
                if head:
                    ids.add(head)
    return sorted(ids)


def change_targets(
    root: Path, policy: Policy, changes, view: TreeView, base_rev: str, head_rev: str
) -> list[ChangeTarget]:
    """本次 diff 触及的 change（active ∪ 到达的归档目录），**以目录为键**。

    ⚠️ 返回**列表**、不是 `dict[change_id] -> directory`：同一个单段 id 可以同时来自
    active 目录与归档到达（构造：同 PR 内 move + 新增 active 子文件）——两份都要校验；
    写成 dict 会**静默丢掉一份**（丢掉哪份取决于实现），而那条 diff 是攻击者可构造的。
    """
    root_rel = policy.changes_root.rstrip("/")
    arrivals = archive_arrivals(changes, policy, view, base_rev, head_rev)
    targets = [
        ChangeTarget(
            change_id=change_id,
            directory=change_dir(root, policy, change_id),
            label=f"{root_rel}/{change_id}",
            accepted_change_ids=frozenset({change_id}),
        )
        for change_id in changed_change_ids(changes, policy, arrivals, view, head_rev)
    ]
    # 别名集合 = {归档目录名} ∪ 到达组里出现过的**全部**源 id（不再按名字过滤：名识别守卫已由
    # 用户 2026-10-15 裁定删除）。取集合而非单个源 ⇒ 与 diff 顺序无关、也不丢源。
    for arrival in arrivals:
        targets.append(
            ChangeTarget(
                change_id=arrival.name,
                directory=archived_change_dir(root, policy, arrival.name),
                label=f"{policy.archive_root}/{arrival.name}",
                accepted_change_ids=frozenset({arrival.name}) | arrival.source_ids,
                source_change_id=(
                    min(sorted(arrival.source_ids), key=len) if arrival.source_ids else None
                ),
                archived=True,
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
