# Condor

Reusable GitHub Actions workflow hub. Use the full pipelines to get a complete CI/CD setup in minutes, or pick individual reusable workflows for specific needs.

---

## Usage

### Full pipelines (recommended for new projects)

Call the top-level orchestrators from your repo:

```yaml
# .github/workflows/push-ci.yml
jobs:
  kotlin-pipeline:
    uses: TomasGC/condor/.github/workflows/kotlin/push-ci.yml@main
    secrets: inherit
    with:
      pre-test-command: python scripts/manage.py create archives --rpa-only
      archives-local-dir: archives/
      device-archives-path: /sdcard/myapp
      app-name: myapp

  python-pipeline:
    uses: TomasGC/condor/.github/workflows/python/push-ci.yml@main
    with:
      skip-on-no-changes: true
```

```yaml
# .github/workflows/pr-ci.yml
jobs:
  pr-checks:
    uses: TomasGC/condor/.github/workflows/common/pr-ci.yml@main
    secrets: inherit
    with:
      push-ci-conclusion: ${{ github.event.workflow_run.conclusion }}
      head-branch: ${{ github.event.workflow_run.head_branch }}
      head-sha: ${{ github.event.workflow_run.head_sha }}
```

```yaml
# .github/workflows/cd.yml
jobs:
  release:
    uses: TomasGC/condor/.github/workflows/kotlin/cd.yml@main
    secrets: inherit
    with:
      app-name: myapp
```

### Individual reusables (pick what you need)

```yaml
# PR title validation only
jobs:
  validate-title:
    uses: TomasGC/condor/.github/workflows/common/reusable/pr-title-validation.yml@main
    with:
      pr-title: ${{ github.event.pull_request.title }}
```

```yaml
# Security checks only
jobs:
  security:
    uses: TomasGC/condor/.github/workflows/common/reusable/security-checks.yml@main
    with:
      head-sha: ${{ github.sha }}
```

---

## Available Workflows

### Common

| Workflow | Description |
|----------|-------------|
| `common/pr-ci.yml` | Full PR validation pipeline (title, context files, security) |
| `common/reusable/check-pr-exists.yml` | Find open PR for a branch |
| `common/reusable/pr-title-validation.yml` | Validate `#123: type: description` format |
| `common/reusable/context-check.yml` | Verify `.claude/contexts/` files updated with code changes |
| `common/reusable/context-comment.yml` | Post PR comment listing missing context files |
| `common/reusable/security-checks.yml` | OWASP dependency scan + TruffleHog + APK size check |

### Kotlin / Android

| Workflow | Description |
|----------|-------------|
| `kotlin/push-ci.yml` | Full Kotlin pipeline (validation → lint → tests → build → coverage → instrumented) |
| `kotlin/cd.yml` | Release pipeline (unit tests + signed APK + GitHub Release) |
| `kotlin/nvd-refresh.yml` | Scheduled NVD database refresh for OWASP dependency checks |
| `kotlin/reusable/validation.yml` | Branch name, commit format, TODO check, large files |
| `kotlin/reusable/lint-checks.yml` | Android lint, ktlint, detekt, OWASP, TruffleHog |
| `kotlin/reusable/unit-tests.yml` | JVM unit + integration tests |
| `kotlin/reusable/integration-mock.yml` | Integration tests with mocked subprocess |
| `kotlin/reusable/integration-real.yml` | Integration tests against real archives |
| `kotlin/reusable/build-apk.yml` | Debug APK build + size check |
| `kotlin/reusable/coverage.yml` | Kover coverage report + threshold enforcement |
| `kotlin/reusable/instrumented-tests.yml` | Android emulator tests + archive push |
| `kotlin/reusable/detect-changes.yml` | Detect Kotlin/Gradle file changes |

### Python

| Workflow | Description |
|----------|-------------|
| `python/push-ci.yml` | Full Python pipeline (detect-changes → lint → tests → coverage) |
| `python/reusable/detect-changes.yml` | Detect Python script file changes |
| `python/reusable/lint-checks.yml` | flake8, black, isort |
| `python/reusable/unit-tests.yml` | pytest unit tests |
| `python/reusable/integration-mock.yml` | Integration tests with FakeSubprocessRunner |
| `python/reusable/integration-real.yml` | Integration tests with real tools |
| `python/reusable/coverage.yml` | pytest coverage + threshold enforcement |
| `python/reusable/e2e-tests.yml` | End-to-end tests |

---

## Inputs Reference

### `kotlin/push-ci.yml`

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `skip-on-no-changes` | boolean | `false` | Skip pipeline if no Kotlin/Gradle files changed |
| `java-version` | string | `21` | JDK version |
| `python-version` | string | `3.12` | Python version (for archive generation) |
| `pre-test-command` | string | `''` | Command to run before each JVM test job (e.g. generate test archives) |
| `archives-local-dir` | string | `''` | Local directory with archives to push to device |
| `device-archives-path` | string | `''` | Device path where archives are pushed |
| `coverage-threshold` | number | `80` | Minimum coverage percentage |
| `apk-size-limit-mb` | number | `50` | Maximum APK size in MB |
| `app-name` | string | `app` | App name for coverage badge and artifact naming |
| `retention-days` | number | `7` | Artifact retention days |

### `kotlin/cd.yml`

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `app-name` | string | ✅ | App name for APK filename (e.g. `otter`) |
| `java-version` | string | — | JDK version (default: `21`) |

**Tag conventions**: `v1.0.0` = stable release, `v1.0.0-alpha` / `v1.0.0-rc1` = pre-release (any hyphen suffix)

### `python/push-ci.yml`

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `skip-on-no-changes` | boolean | `false` | Skip pipeline if no Python files changed |
| `python-version` | string | `3.12` | Python version |

### `common/pr-ci.yml`

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `push-ci-conclusion` | string | ✅ | Push-CI conclusion (`success`/`failure`/`cancelled`) |
| `head-branch` | string | ✅ | Head branch of the push |
| `head-sha` | string | ✅ | Head SHA for checkout |

### `common/reusable/context-check.yml`

Checks that `.claude/contexts/` files are updated alongside code changes:

| File | Requirement |
|------|-------------|
| `kanban.md` | **Mandatory** — any `app/src/` change |
| `architecture.md` | Warning — when new classes/interfaces/DI detected |
| `tests.md` | Warning — when `app/src/test/` or `app/src/androidTest/` changed |

---

## Required Secrets

| Secret | Used by | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | All workflows | Standard GitHub token (auto-provided) |
| `KEYSTORE_PASSWORD` | `kotlin/cd.yml` | Android release keystore password |
| `KEY_PASSWORD` | `kotlin/cd.yml` | Android release key password |
| `GIST_SECRET` | `kotlin/reusable/coverage.yml` | Token for updating coverage badge gist |
| `NVD_API_KEY` | `kotlin/nvd-refresh.yml` | NVD API key for OWASP dependency check |
