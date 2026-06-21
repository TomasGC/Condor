# Architecture - Condor

**Purpose**: Workflow structure, design decisions, and cross-repo usage patterns
**Last Updated**: 2026-06-21

---

## Repository Structure

```
.github/workflows/
├── common/
│   ├── pr-ci.yml                          # Orchestrator: full PR validation pipeline
│   └── reusable/
│       ├── check-pr-exists.yml            # Find open PR for a branch + extract title/number
│       ├── pr-title-validation.yml        # Validate #123: type: description format
│       ├── context-check.yml              # Verify .claude/contexts/ updated with code changes
│       ├── context-comment.yml            # Post PR comment for missing context files
│       └── security-checks.yml            # OWASP dependency scan + TruffleHog + APK size
├── kotlin/
│   ├── push-ci.yml                        # Orchestrator: full Kotlin pipeline
│   ├── cd.yml                             # Orchestrator: release pipeline
│   ├── nvd-refresh.yml                    # Scheduled NVD database refresh (OWASP)
│   └── reusable/
│       ├── detect-changes.yml             # Detect Kotlin/Gradle file changes
│       ├── validation.yml                 # Branch name, commit format, TODO, large files
│       ├── lint-checks.yml                # Android lint, ktlint, detekt, OWASP, TruffleHog
│       ├── unit-tests.yml                 # JVM unit + integration-mock + integration-real
│       ├── integration-mock.yml           # Integration tests with mocked subprocess
│       ├── integration-real.yml           # Integration tests against real archives
│       ├── build-apk.yml                  # Debug APK build + size check
│       ├── coverage.yml                   # Kover coverage report + threshold enforcement
│       └── instrumented-tests.yml         # Android emulator tests + archive push
└── python/
    ├── push-ci.yml                        # Orchestrator: full Python pipeline
    └── reusable/
        ├── detect-changes.yml             # Detect Python file changes
        ├── lint-checks.yml                # flake8, black, isort
        ├── unit-tests.yml                 # pytest unit tests
        ├── integration-mock.yml           # Integration tests with FakeSubprocessRunner
        ├── integration-real.yml           # Integration tests with real tools
        ├── coverage.yml                   # pytest coverage + threshold enforcement
        └── e2e-tests.yml                  # End-to-end tests
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

### 5. Pre-Release Detection

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
