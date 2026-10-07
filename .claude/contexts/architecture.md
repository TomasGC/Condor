# Architecture - Condor

**Purpose**: Workflow structure, design decisions, and cross-repo usage patterns
**Last Updated**: 2026-10-07

---

## Repository Structure

```
.github/
├── actions/
│   └── check-docs-only/
│       └── action.yml                     # Composite: detect if push contains only .md changes
└── workflows/
    ├── common-context-check.yml           # Verify context files updated with code changes (dir + path regexes are inputs)
    ├── common-context-comment.yml         # Post PR comment if context files missing
    ├── common-pr-ci.yml                   # Orchestrator: PR validation, called from a pull_request workflow
    ├── common-pr-title-validation.yml     # Validate #123: type: description format
    ├── common-security-checks.yml         # TruffleHog secret scan of the PR's changes
    ├── kotlin-build-apk.yml               # Debug APK build + size check
    ├── kotlin-cd.yml                      # Orchestrator: release pipeline
    ├── kotlin-coverage.yml                # Kover coverage report + threshold enforcement
    ├── kotlin-detect-changes.yml          # Detect Kotlin/Gradle file changes + docs-only check
    ├── kotlin-instrumented-tests.yml      # Android emulator tests: self-contained matrix (2 shards)
    ├── kotlin-lint-checks.yml             # Android lint, ktlint, detekt, OWASP, TruffleHog
    ├── kotlin-nvd-refresh.yml             # Scheduled NVD database refresh (OWASP)
    ├── kotlin-push-ci.yml                 # Orchestrator: full Kotlin pipeline
├── kotlin-gradle-tier.yml              # One test tier: matrix of Gradle commands (empty list skips)
    ├── kotlin-validation.yml              # Branch name, commit format, TODO, large files
    ├── python-coverage.yml                # unit + integration_mock + integration_real coverage, 80% gate
    ├── python-detect-changes.yml          # Detect Python file changes + docs-only check
    ├── python-lint-checks.yml             # flake8, black, isort, pylint, mypy, bandit, pip-audit, vulture
    ├── python-push-ci.yml                 # Orchestrator: the one Python pipeline of every project
    └── python-pytest.yml                  # One pytest run: dir, requirements, marker, extra args (one per tier)
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
uses: TomasGC/Condor/.github/workflows/kotlin-push-ci.yml@main
```

GitHub executes condor's YAML but `actions/checkout` checks out the **caller's** code. This means:
- `python scripts/manage.py` runs against otter's `scripts/` directory ✅
- Condor cannot reference its own scripts — all scripts must live in the caller repo ✅
- Nested `uses: ./` inside condor resolves to condor's own workflows ✅

### 4. The Caller's Event Reaches the Called Workflow

A called workflow's `github` context is the caller's: `github.event_name` and `github.event.*` are those of the
event that started the caller. `common-pr-ci.yml` reads the PR (number, title, head SHA) from
`github.event.pull_request` and needs no input for it; its first job fails when the caller was not started by
`pull_request`. Inputs are for what the event cannot say: a project's layout and conventions.

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
pull_request (opened, reopened, synchronize, edited)
    └── common-pr-ci.yml
            ├── pull-request          → fails unless started by pull_request
            ├── pr-validation         → validates the title (default #123: type: description)
            ├── context-check         → checks: kanban.md (mandatory), architecture.md + tests.md (warnings)
            ├── context-comment       → posts PR comment if context files missing
            └── security-checks       → TruffleHog secret scan
```

Why `pull_request`, not `workflow_run` after Push-CI (#19): a `workflow_run` run is attached to the default branch,
so its result never reached the PR's checks list and could not be required; and a PR opened after its branch's last
push was never checked (Push-CI's completion found no PR, nothing re-ran). On `pull_request` the checks sit on the
PR's head commit, next to Push-CI's (a push run is on the same commit), and `edited` re-runs them on a title change.
PR-CI no longer waits for Push-CI: its two build-dependent jobs were removed. The APK size check duplicated
`kotlin-build-apk.yml`'s and, under `workflow_run`, read an empty `github.head_ref`, so it checked the latest Push-CI
run of any branch. The dependency scan ran a Gradle task (`dependencyCheckAnalyze`) no caller has had since #10 and
passed on the missing report; Push-CI's lint stage scans dependencies with OSV-Scanner.

### Context Check Rules

| File | Trigger | Level |
|------|---------|-------|
| `<contexts-dir>/kanban.md` | Any change matching `code-paths` | Mandatory (fails CI) |
| `<contexts-dir>/architecture.md` | New classes/interfaces/DI detected in those changes | Warning (comment only) |
| `<contexts-dir>/tests.md` | Any change matching `test-paths` | Warning (comment only) |

Defaults describe an Android app (`.claude/contexts`, `^app/src/`, `^app/src/(test|androidTest)/`); a caller with
another layout passes its own, e.g. Meerkat: `contexts`, Python sources, `tests/` directories.

### One Python Pipeline, Tiers by Marker

Every project's Python code (the Kotlin apps' `scripts/`, Meerkat's whole repo) goes through the same
`python-push-ci.yml`: same tools, same thresholds (pylint 7, coverage 80, line length 120). Projects differ only by
layout inputs (`scripts-dir`, `requirements`, `source-dirs`, `exclude-dirs`, `exclude-marker`).

Each tier is one `python-pytest.yml` call selecting `-m "<tier> and not <exclude-marker>"`; every project marks its
tests from the tier directory (root `conftest.py` rule, markers registered in `pytest.ini`). The per-directory tier
workflows this replaced ran only `tests/unit/{android,cli,common}/`, so tests elsewhere in a tier never ran in CI
(29 in Otter). Inputs reach the shell through `env`, never interpolated into the script, so a marker expression
cannot inject commands; space-separated inputs are split with `read -r -a`. Lint tool versions are pinned in
`python-lint-checks.yml`, so a tool release changes nothing until the pin is bumped.

A collection guard (`python-test-markers.yml`) runs before the tiers. Each tier tolerates an empty selection (a project may
have no integration_mock tests), so without it a test outside every tier directory would run nowhere and a project
with no marked tests would stay green while running nothing.

### Condor Tests Itself

`condor-lint.yml` (actionlint + shellcheck, every push), `condor-test-python.yml` (the Python pipeline on fixture
projects under `tests/fixtures/`, every push) and `condor-test-pr.yml` (the PR pipeline on Condor's own PRs). A
reusable workflow cannot be asserted to fail from its caller (`continue-on-error` is not allowed on a `uses:` job), so
the negative case runs the guard with `fail-on-violation: false` and asserts its outputs. The Kotlin pipelines have no
self-test yet (Android fixture, Gradle, emulator).

`common-pr-ci.yml` calls its children with `./` paths: they come from the same Condor commit, so a caller pinning it
to a SHA pins the whole PR pipeline. (Composite actions are the exception: `./` in a `uses:` of an action resolves
in the caller's checkout, so `check-docs-only` stays referenced as `TomasGC/Condor/...@main`.)

---

## Kotlin Pipeline Flow

```
detect-changes
    │
    ├── validation (branch, commit, TODO, large files)   ┐ parallel
    ├── lint-checks (android lint, ktlint, detekt, OWASP, TruffleHog) ┘
    │
    ├── unit (matrix: one job per unit-tasks command)
    │       └── integration-mock (matrix)
    │               └── integration-real (matrix)
    │                       ├── build-apk ──→ instrumented-tests (only if instrumented-task is set)
    │                       └── coverage
    └── (all blocked by detect-changes gate if skip-on-no-changes=true; an empty tier is skipped, not failed)
```

---

## Adding a New Language Pipeline

1. Create `.github/workflows/<lang>-<stage>.yml` per concern (reusable workflows must sit directly in `.github/workflows/`)
2. Create `<lang>-push-ci.yml` orchestrator with `uses: ./.github/workflows/<lang>-<stage>.yml`
3. Document inputs in `README.md`
4. Update this file

---

**End of Architecture Documentation**
