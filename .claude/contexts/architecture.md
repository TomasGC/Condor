# Architecture - Condor

**Purpose**: Workflow structure, design decisions, and cross-repo usage patterns
**Last Updated**: 2026-08-06

---

## Repository Structure

```
.github/
├── actions/
│   └── check-docs-only/
│       └── action.yml                     # Composite: detect if push contains only .md changes
└── workflows/
    ├── common-check-pr-exists.yml         # Find open PR for a branch + extract title/number
    ├── common-context-check.yml           # Verify .claude/contexts/ updated with code changes
    ├── common-context-comment.yml         # Post PR comment if context files missing
    ├── common-pr-ci.yml                   # Orchestrator: full PR validation pipeline
    ├── common-pr-title-validation.yml     # Validate #123: type: description format
    ├── common-security-checks.yml         # OWASP dependency scan + TruffleHog + APK size
    ├── kotlin-build-apk.yml               # Debug APK build + size check
    ├── kotlin-cd.yml                      # Orchestrator: release pipeline
    ├── kotlin-coverage.yml                # Kover coverage report + threshold enforcement
    ├── kotlin-detect-changes.yml          # Detect Kotlin/Gradle file changes + docs-only check
    ├── kotlin-instrumented-tests.yml      # Android emulator tests: self-contained matrix (2 shards)
    ├── kotlin-lint-checks.yml             # Android lint, ktlint, detekt, OWASP, TruffleHog
    ├── kotlin-nvd-refresh.yml             # Scheduled NVD database refresh (OWASP)
    ├── kotlin-push-ci.yml                 # Orchestrator: full Kotlin pipeline
    ├── kotlin-validation.yml              # Branch name, commit format, TODO, large files
    ├── python-coverage.yml                # pytest coverage + threshold enforcement
    ├── python-detect-changes.yml          # Detect Python file changes + docs-only check
    ├── python-e2e-tests.yml               # End-to-end tests
    ├── python-integration-mock.yml        # Integration tests with FakeSubprocessRunner
    ├── python-integration-real.yml        # Integration tests with real tools
    ├── python-lint-checks.yml             # flake8, black, isort
    ├── python-push-ci.yml                 # Orchestrator: full Python pipeline
    └── python-unit-tests.yml              # pytest unit tests
```

---

## Design Principles

### 1. Single Concern Per File

Each reusable workflow does exactly one thing. Orchestrators (`push-ci.yml`, `pr-ci.yml`, `cd.yml`) only define job ordering and data flow — no business logic.

### 2. Structured Inputs Over Free-Form Strings

```yaml
# Bad — caller injects arbitrary shell
pre-instrumented-command: "adb push archives/ /sdcard/otter && do_other_thing"

# Good — explicit, validated, composable
pre-test-command: python scripts/manage.py create archives --rpa-only
archives-local-dir: archives/
device-archives-path: /sdcard/otter
```

### 3. Cross-Repo Context

When a caller repo (e.g., otter) references condor workflows:
```yaml
uses: TomasGC/condor/.github/workflows/kotlin/push-ci.yml@main
```

GitHub executes condor's YAML but `actions/checkout` checks out the **caller's** code. This means:
- `python scripts/manage.py` runs against otter's `scripts/` directory ✅
- Condor cannot reference its own scripts — all scripts must live in the caller repo ✅
- Nested `uses: ./` inside condor resolves to condor's own workflows ✅

### 4. `workflow_call` Input Propagation

`workflow_call` does NOT inherit `github.event.*` from the caller's trigger event. The caller must pass event data explicitly as inputs:

```yaml
# otter/pr-ci.yml (has workflow_run context)
with:
  push-ci-conclusion: ${{ github.event.workflow_run.conclusion }}
  head-branch: ${{ github.event.workflow_run.head_branch }}
  head-sha: ${{ github.event.workflow_run.head_sha }}

# condor/common/pr-ci.yml (receives as inputs, no event context)
inputs:
  push-ci-conclusion:
    type: string
    required: true
```

### 5. Instrumented Test Optimization (Self-Contained Shards)

`kotlin-instrumented-tests.yml` uses a single self-contained matrix job (no separate avd-setup):

```
instrumented (matrix: shard-index [0, 1]) — each shard runs on its own runner
    ├── Cache system image  → key: android-system-image-api30-default-x86_64-v1
    ├── Install system image via ./gradlew pixel4api30Setup (cache miss only)
    ├── Cache Android emulator → key: android-emulator-v1
    ├── Install emulator via sdkmanager (cache miss only)
    │     Note: pixel4api30Setup installs system image only, not the emulator binary
    ├── Create AVD + cold boot (-no-snapshot-load -no-snapshot-save)
    └── ./gradlew connectedDebugAndroidTest -PnumShards=2 -PshardIndex={shard}
```

**Why no AVD snapshot cache**: AVD snapshots encode QEMU machine state (CPU, memory layout). GitHub Actions runners are ephemeral VMs with non-deterministic hardware — restoring a snapshot on a different hypervisor/CPU configuration causes emulator boot failure (`adb wait-for-device` timeout 124). Removed; cold boot is reliable and fits in the 60-min job timeout.

**Savings vs baseline** (system image + emulator cache hit, both shards parallel): ~11min saved (~2min system image + ~4min cold boot × 2 shards + ~5min per half-suite).

### 6. Docs-Only Push Detection

Both `kotlin-detect-changes.yml` and `python-detect-changes.yml` output a `docs-only` flag. When true, all downstream jobs are skipped.

**Why not `paths-ignore` in caller repos**: that only applies to the top-level trigger, not reusable workflow jobs individually.

**Why not `dorny/paths-filter`**: in nested `workflow_call` context, dorny has no push event range — it falls back to branch-vs-main comparison, which is always true on feature branches.

**Solution**: composite action `.github/actions/check-docs-only` runs `git diff --name-only $BEFORE $AFTER` using `github.event.before`/`after` push SHAs. Outputs `true` only if every changed file ends with `.md`.

```yaml
# kotlin-detect-changes.yml / python-detect-changes.yml
- uses: actions/checkout@v4
- uses: TomasGC/Condor/.github/actions/check-docs-only@main
  id: docs-check
  with:
    before: ${{ github.event.before }}
    after: ${{ github.event.after }}

# kotlin-push-ci.yml / python-push-ci.yml — each downstream job:
if: needs.detect-changes.outputs.docs-only != 'true' && ...
```

**Edge cases handled**:
- Initial push (before SHA = `0000...`): `docs-only=false` (run pipeline)
- Empty diff: `docs-only=false` (run pipeline)
- All `.md`: `docs-only=true` (skip pipeline)
- Mixed `.md` + code: `docs-only=false` (run pipeline)

---

### 7. Pre-Release Detection

`cd.yml` uses hyphen-suffix convention — no hardcoded suffixes:

```bash
VERSION=${TAG#v}
[[ "$VERSION" == *-* ]] && IS_PRERELEASE=true || IS_PRERELEASE=false
```

`v1.0.0` → stable, `v1.0.0-alpha` / `v1.0.0-rc1` / `v1.0.0-beta.2` → pre-release.

---

## PR Validation Pipeline

```
workflow_run (Push-CI completes)
    └── common/pr-ci.yml
            ├── check-pr-exists       → outputs: has_pr, pr_number, pr_title
            ├── pr-title-validation   → validates: #123: type: description
            ├── context-check         → checks: kanban.md (mandatory), architecture.md + tests.md (warnings)
            ├── context-comment       → posts PR comment if context files missing
            └── security-checks       → OWASP + TruffleHog + APK size
```

### Context Check Rules

| File | Trigger | Level |
|------|---------|-------|
| `.claude/contexts/kanban.md` | Any `app/src/` change | Mandatory (fails CI) |
| `.claude/contexts/architecture.md` | New classes/interfaces/DI detected | Warning (comment only) |
| `.claude/contexts/tests.md` | `app/src/test/` or `app/src/androidTest/` changed | Warning (comment only) |

---

## Kotlin Pipeline Flow

```
detect-changes
    │
    ├── validation (branch, commit, TODO, large files)
    ├── lint-checks (android lint, ktlint, detekt, OWASP, TruffleHog)
    │
    ├── unit-tests
    │       └── integration-mock
    │               └── integration-real
    │                       ├── build-apk ──→ instrumented-tests
    │                       └── coverage
    └── (all blocked by detect-changes gate if skip-on-no-changes=true)
```

---

## Adding a New Language Pipeline

1. Create `<lang>/reusable/<stage>.yml` per concern
2. Create `<lang>/push-ci.yml` orchestrator with `uses: ./.github/workflows/<lang>/reusable/<stage>.yml`
3. Document inputs in `README.md`
4. Update this file

---

**End of Architecture Documentation**
