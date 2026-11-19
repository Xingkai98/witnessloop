# Add the multi-model review loop (`witnessloop review`)

## Summary

Adds a `review` verb group to `witnessloop` that runs a **multi-model review closed
loop** on top of a change, orthogonal to the existing gate (`contract` / `evidence` /
`checkcmd` — none of which are modified).

- `witnessloop review run --change <id>`: two zero-memory reviewers run concurrently,
  their findings are merged and de-duplicated **by `where` only** (keeping the higher
  severity), a fixer produces fix plans, and the loop stops on convergence
  (`pass_rule=medium_plus_zero`), stall escalation (`stall_rounds=2` → a judge
  single-pass review), or cost cap (`budget.max_cost_usd=30`).
- Every round writes a manifest binding `actors[]` (role/adapter/model/run_id +
  `degraded_from`) and the `config.resolved.json` hash.
- `witnessloop review report --md` reads the loop back into Markdown and runs four
  mechanical negative-sample checks (tampered manifest / missing evidence / same actor
  twice / missed positive control), exiting non-zero on any violation.

## Components

- `src/witnessloop/review/revision.py` — `GitRevision` / `DigestRevision` anchors with
  `mode: auto` detection (git vs. digest). Digest hashes the working tree (stable sort,
  excluding `.git` and the loop's own `.reviewloop/` output dir).
- `src/witnessloop/review/roles.py` — `reviewloop.roles.json` (schema
  `witnessloop/roles@v1`) resolved into `config.resolved.json` (secrets never written).
- `src/witnessloop/review/adapters.py` — `claude` / `codex` / `mock` adapters with one
  interface (prompt + context → structured findings JSON). Errors are normalized to
  `AdapterError` kinds so the orchestrator can degrade mechanically.
- `src/witnessloop/review/orchestrator.py` — the loop. Review context includes the
  changed-file list and a **code-first** diff (up to 120k chars): the earlier
  `diff[:20000]` let docs consume the budget and caused false "code missing" findings.
- `src/witnessloop/review/report.py` — read-back + verification.
- `reviewloop.roles.json` — this repo's review routing: `reviewerA = gpt-6.1-sol`
  (codex/heyroute), `reviewerB = glm-5.3` (claude/heyroute), `fixer = deepseek-flash`,
  `judge = deepseek-flash`.

## Degradation rule (mechanical, never silent)

If a reviewer's path returns 401/402/`model_not_found`/balance-exhausted — or its auth
was never resolvable — that role degrades **immediately to `deepseek-flash`** and the
manifest/report record `degraded_from: <original-model>`. If both reviewer paths
degrade, the report notes "same-source dual review" (`本轮为同源双审`).

Auth resolution is single-sourced in `adapters.resolve_auth_token` (`auth_token` →
`auth_env`; `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` only when the role explicitly
sets `allow_host_auth_fallback: true`): the pre-check, the degrade decision, and the
actual adapter construction cannot disagree. Malformed model
output is marked `error_kind="parse"`, gets one fallback attempt, and if it still
fails the round is `BLOCKED` — an empty finding list is never treated as `PASS`.
If the deepseek fallback key is also unavailable, the round is likewise `BLOCKED`;
mock is never used as a stand-in for a real review unless `--adapter mock` is
explicitly requested (smoke-test path). Host `ANTHROPIC_*` credentials are **not**
reused by default: a role must opt in with `allow_host_auth_fallback: true`, and the
fallback role only reads `WITNESSLOOP_DEEPSEEK_KEY` (no cross-endpoint token reuse).

Hardening from the real-model review runs: findings are structurally validated
(object + severity, normalized before ranking); fixer `fixes` / judge `rulings` are
not misclassified by the reviewer parser; a judge `PASS` must cover every stalled
finding with `false-positive` rulings and cannot override unstalled medium+ findings;
the budget is checked both before judge/fixer and at each round entry; and the report
is robust to tampered manifest field types (including missing reviewer actors and
non-object `fixer` / `judge`), validates HTTP response shapes before `.get`, and keeps
role overrides field-level so a partial override cannot silently become `mock`.
`review report --md` is accepted (the report is Markdown; the flag is kept for
documented commands). A diff acquisition failure aborts the run instead of proceeding
without code context; transient 5xx/timeouts fall back once; HTTP redirects are refused
so credentials cannot cross hosts; the worktree digest length-prefixes path/content
(no NUL-ambiguity); and the report requires exactly `reviewerA` + `reviewerB` with
non-empty, distinct run ids.

## Validation

- `uv run pytest -q` → **904 passed** (788 existing + 116 review-loop tests).
- T-075 real-model run: `reviewerA = gpt-6.1-terra` (codex/heyroute),
  `reviewerB = glm-5.3` (claude/heyroute) with **no `degraded_from`**.
  Clean 3-round loop: `BLOCKED` (the demo code really had medium findings);
  tamper positive control: the injected manifest defect was reported by **both**
  reviewers at blocker/high severity. Costs: $0.0451 + $0.0364 (approximate).
- Full (git) form: `check` walks the four exit codes 3 (not onboarded) → 1 (evidence
  missing) → 0 (evidence present) → 5 (empty range). Logs in `/tmp/wl-p5-logs/full.log`.
- Lite (no `.git`) form: the same `review run` auto-detects digest mode and converges;
  `check` itself is git-only by design, so it stops at rc=1 there (documented boundary).
- This change carries three stage manifests (`grill` / `grill-adversarial` /
  `building`) bound to the content revision; `witnessloop check` is the gate.

## Out of scope / known limitations

- The fixer produces fix **plans**, not auto-applied patches (safety boundary).
- `.reviewloop/` artifacts are **not** gate evidence; `manifest build` is still the
  bridge to `reviews/*.manifest.json`.
- The judge currently receives only `where` strings, not finding bodies or diffs, so
  stalled loops tend to end `BLOCKED`/`uncertain` (known limitation, unchanged here).
- `roles@v1` is a single repo-root table; there is no per-change / per-stage routing.
  `grill` / `grill-adversarial` remain host-plugin driven.
- `gpt-6.1-sol` is not in this host's `model_pricing` table; its price entry ($5/$30
  per 1M tokens) is a conservative same-generation estimate used only for budget
  stop-loss, not billing.
- No version bump, no PyPI, no upstream/OpenDirector changes, no merge to `main`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
