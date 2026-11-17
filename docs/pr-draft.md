# PR Draft: Add the multi-model review loop (`witnessloop review`)

> **Status: draft only — do not push, do not open a PR.** This file is a written
> record of the intended PR, per T-071. Merging is a separate, later step.

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
- `src/witnessloop/review/orchestrator.py` — the loop.
- `src/witnessloop/review/report.py` — read-back + verification.

## Degradation rule (mechanical, never silent)

If a reviewer's path returns 401/402/`model_not_found`/balance-exhausted — or its auth
was never resolvable — that role degrades **immediately to `deepseek-flash`** and the
manifest/report record `degraded_from: <original-model>`. If both reviewer paths
degrade, the report notes "same-source dual review" (`本轮为同源双审`).

## Validation

- `uv run pytest -q` → **832 passed** (788 existing + 44 new).
- Full (git) form: `check` walks the four exit codes 3 (not onboarded) → 1 (evidence
  missing) → 0 (evidence present) → 5 (empty range). Logs in `/tmp/wl-p5-logs/full.log`.
- Lite (no `.git`) form: the same `review run` auto-detects digest mode and converges;
  `check` itself is git-only by design, so it stops at rc=1 there (documented boundary).
- Real dual-review smoke test: `reviewerA = gpt-6.1-terra` (codex/heyroute),
  `reviewerB = glm-5.3` → **degraded to `deepseek-flash`** (the third heyroute key
  `hy-glm-5.3` is not present on this host). One round, `PASS`, cost ≈ $0.0145.

## Out of scope / known limitations

- The fixer produces fix **plans**, not auto-applied patches (safety boundary).
- `glm-5.3` was not exercised for real — its key is unavailable, so reviewerB ran
  degraded throughout (honestly marked).
- No version bump, no PyPI, no upstream/OpenDirector changes, no merge to `main`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
