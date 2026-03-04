# Three Initiatives Design Doc — 2026-03-04

## Initiative 1: Runner Checkout Recovery Fix (Priority: Immediate)

### Problem
Self-hosted runners retain stale sparse-checkout state between runs. The existing
recovery guard runs `git sparse-checkout disable` + `git reset --hard HEAD` but
blobs were never fetched for excluded paths, so reset restores nothing.

### Fix
Add `git fetch --no-tags origin "$GITHUB_SHA"` before `git reset --hard FETCH_HEAD`
in the recovery sequence. Propagate the canonical guard to all workflows.

### Canonical guard
```yaml
- name: Verify checkout integrity
  run: |
    if [[ ! -f pyproject.toml ]]; then
      echo "::warning::pyproject.toml missing after checkout; attempting recovery"
      git sparse-checkout disable || true
      git fetch --no-tags origin "$GITHUB_SHA"
      git reset --hard FETCH_HEAD
      git clean -ffd || true
    fi
    if [[ ! -f pyproject.toml ]]; then
      echo "::error::Repository checkout is incomplete (pyproject.toml missing)"
      ls -la
      exit 1
    fi
```

### Scope
- Update 5 existing workflows: lint.yml, test.yml, smoke.yml, smoke-offline.yml, deploy-frontend.yml
- Add guard to ~10 workflows that lack it: core-suites.yml, sdk-parity.yml, openapi.yml,
  benchmark.yml, nightly-full-matrix.yml, integration-minimal, etc.
- Place guard immediately after every `actions/checkout` step

---

## Initiative 2: Full Lockfile + Vulnerability Sweep (Priority: High)

### Problem
27 Dependabot alerts (14 high, 12 moderate, 1 low). No Python lockfile means
transitive deps are unpinned. Dev-only JS deps trigger alerts that CI correctly
ignores but clutter the dashboard.

### Components
1. **Python lockfile** — Generate `uv.lock` (or pip-compile output). CI validates freshness.
2. **JS dependency upgrades** — `npm update` in `aragora/live/` to resolve semver/minimatch/glob.
3. **Dismiss dev-only alerts** — After upgrades, dismiss remaining dev-only JS alerts.
4. **Pin vulnerable Python transitives** — Add explicit `>=X` floor pins in pyproject.toml
   for any high-severity transitive CVEs (pattern: `pillow>=12.1.1` with CVE comment).
5. **Update SECURITY.md** — Fix stale version table (2.6.x → 2.8.x).
6. **Harden SBOM Grype scan** — Remove `|| true` from sbom.yml critical gate.

---

## Initiative 3: Full Developer Onramp (Priority: Strategic)

### P0 — Consolidated Quickstart (1-2 days)
- Create `docs/quickstart.md` consolidating 6+ existing quickstarts
- Add `examples/quickstart.ts` at root level
- CI smoke test validating quickstart examples import and run

### P0 — Auto-generated /docs Page (1-2 days)
- Verify FastAPI's built-in `/docs` (Swagger) and `/redoc` work end-to-end
- Add tabbed code samples (Python/TS/curl) to OpenAPI descriptions
- Add `aragora/live/src/app/docs/page.tsx` embedding Redoc with live spec

### P1 — Interactive API Playground (3-5 days)
- `aragora/live/src/components/Playground/` — React request builder + response viewer + WS stream
- Rate-limited sandbox proxy via existing unified_server.py rate limiting
- `aragora/live/src/app/playground/page.tsx` — Next.js app router page

### P1 — SDK Parity Push (3-5 days)
- Close 46 stale TypeScript + 23 stale Python SDK gaps
- Focus on "core capabilities" subset for 100% parity

### P1 — Integration Testing (1-2 days)
- CI workflow: time-to-first-debate ≤300s gate
- Playground response <10s p99, docs load <3s p95

### Corrected Paths (vs. original spec)
| Spec Path | Actual Path |
|-----------|-------------|
| `frontend/pages/docs.tsx` | `aragora/live/src/app/docs/page.tsx` |
| `frontend/components/Playground/` | `aragora/live/src/components/Playground/` |
| `frontend/pages/api-playground.tsx` | `aragora/live/src/app/playground/page.tsx` |
| `api/middleware/sandbox.py` | Integrated into `aragora/server/unified_server.py` |
| `sdks/python/aragora/` | `aragora-sdk/` (PyPI: aragora-sdk) |
| `sdks/typescript/src/` | `sdk/typescript/` (npm: @aragora/sdk) |
| `api/openapi.yaml` | `docs/api/openapi.yaml` |
