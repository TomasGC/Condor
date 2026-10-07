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
    uses: TomasGC/Condor/.github/workflows/kotlin-push-ci.yml@main
    secrets: inherit
    with:
      pre-test-command: python scripts/manage.py create archives --rpa-only
      archives-local-dir: archives/
      device-archives-path: /sdcard/myapp
      app-name: myapp

  python-pipeline:
    uses: TomasGC/Condor/.github/workflows/python-push-ci.yml@main
    with:
      skip-on-no-changes: true
```

The Python pipeline is the same for every project; only the layout inputs differ. A repo whose Python code
lives at the root with tests next to each component, for example:

```yaml
  python-pipeline:
    uses: TomasGC/Condor/.github/workflows/python-push-ci.yml@<sha>
    with:
      scripts-dir: .
      requirements: scripts/requirements.txt tools/requirements.txt
      source-dirs: agents scripts skills
      exclude-dirs: fixtures
      exclude-marker: live_ai
```

```yaml
# .github/workflows/pr-ci.yml
name: PR-CI

on:
  pull_request:
    types: [opened, reopened, synchronize, edited]   # edited: a title change re-runs the checks

permissions:
  contents: read
  pull-requests: write   # context comment

concurrency:
  group: pr-ci-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  pr-checks:
    uses: TomasGC/Condor/.github/workflows/common-pr-ci.yml@main
    # Non-Android project: its own context dir and code paths
    # with:
    #   contexts-dir: contexts
    #   code-paths: '\.py$'
    #   test-paths: '(^|/)tests/'
```

PR-CI runs on the pull request itself: its checks sit on the PR's head commit, in the PR's checks list, so branch
protection can require them next to Push-CI's (the push pipeline's checks are on the same commit). A PR opened after
its branch's last push is checked when it opens. PR-CI does not wait for Push-CI: none of its checks reads the build.

```yaml
# .github/workflows/cd.yml
jobs:
  release:
    uses: TomasGC/Condor/.github/workflows/kotlin-cd.yml@main
    secrets: inherit
    with:
      app-name: myapp
```

### Individual reusables (pick what you need)

```yaml
# PR title validation only
jobs:
  validate-title:
    uses: TomasGC/Condor/.github/workflows/common-pr-title-validation.yml@main
    with:
      pr-title: ${{ github.event.pull_request.title }}
```

```yaml
# Secret scan only
jobs:
  security:
    uses: TomasGC/Condor/.github/workflows/common-security-checks.yml@main
    with:
      head-sha: ${{ github.event.pull_request.head.sha }}
```

```yaml
# One pytest run per test tier, any project layout
jobs:
  unit:
    uses: TomasGC/Condor/.github/workflows/python-pytest.yml@<sha>
    with:
      requirements: scripts/requirements.txt requirements-test.txt
      marker: unit and not live_ai
```

Reusable workflows must sit directly in `.github/workflows/` (GitHub does not resolve subdirectories), so every
file is flat and named `<language>-<stage>.yml`. Pin a caller to a commit SHA (`@<sha>`) for reproducible runs;
`@main` follows every change.

---

## Available Workflows

### Common

| Workflow | Description |
|----------|-------------|
| `common-pr-ci.yml` | Full PR validation pipeline (title, context files, secret scan), called from a `pull_request` workflow |
| `common-pr-title-validation.yml` | Validate `#123: type: description` format |
| `common-context-check.yml` | Verify context files (default `.claude/contexts/`) updated with code changes |
| `common-context-comment.yml` | Post PR comment listing missing context files |
| `common-security-checks.yml` | TruffleHog secret scan of the PR's changes |

### Kotlin / Android

| Workflow | Description |
|----------|-------------|
| `kotlin-push-ci.yml` | Full Kotlin pipeline: validation and lint beside the unit tier; unit, integration-mock and integration-real tiers chained; build, coverage, instrumented |
| `kotlin-cd.yml` | Release pipeline (unit tests + signed APK + GitHub Release) |
| `kotlin-nvd-refresh.yml` | Scheduled NVD database refresh for OWASP dependency checks |
| `kotlin-validation.yml` | Branch name, commit format, TODO check, large files |
| `kotlin-lint-checks.yml` | Android lint, ktlint, detekt, OWASP, TruffleHog |
| `kotlin-gradle-tier.yml` | One test tier: one matrix job per Gradle command, an empty list skips the tier |
| `kotlin-build-apk.yml` | Debug APK build + size check |
| `kotlin-coverage.yml` | Kover coverage report + threshold enforcement |
| `kotlin-instrumented-tests.yml` | Android emulator tests + archive push |
| `kotlin-detect-changes.yml` | Detect Kotlin/Gradle file changes |

### Python

| Workflow | Description |
|----------|-------------|
| `python-push-ci.yml` | The Python pipeline of every project: detect-changes → lint → unit → integration_mock → integration_real → coverage + e2e |
| `python-detect-changes.yml` | Detect Python file changes (code, requirements, tool settings) |
| `python-lint-checks.yml` | flake8, black, isort, pylint, mypy, bandit, pip-audit, vulture |
| `python-pytest.yml` | One pytest run: working directory, requirement files, marker expression, extra args; each test tier is one call |
| `python-coverage.yml` | unit + integration_mock + integration_real coverage, 80% gate |
| `python-test-markers.yml` | Collection guard: fails when tests carry no tier marker or the suite collects nothing |

Each tier is selected by its pytest marker (`-m "<tier> and not <exclude-marker>"`), so a project marks every test
with its tier: a root `conftest.py` that applies the tier directory (`tests/<tier>/`) as the marker, and the four
markers (`unit`, `integration_mock`, `integration_real`, `e2e`) registered in `pytest.ini`. The collection guard
(`python-test-markers.yml`) runs before the tiers and fails when a test carries no tier marker, since no tier job
would run it, or when nothing is collected at all.

---

## Inputs Reference

### `kotlin-push-ci.yml`

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `skip-on-no-changes` | boolean | `false` | Skip pipeline if no Kotlin/Gradle files changed |
| `unit-tasks` | string | `'[]'` | JSON array of Gradle commands for the unit tier, e.g. `[":core:test", ":app:testDebugUnitTest"]` |
| `integration-mock-tasks` | string | `'[]'` | JSON array of Gradle commands for the integration-mock tier |
| `integration-real-tasks` | string | `'[]'` | JSON array of Gradle commands for the integration-real tier |
| `instrumented-task` | string | `''` | Gradle task for the instrumented tests; empty skips the tier |
| `java-version` | string | `21` | JDK version |
| `python-version` | string | `3.12` | Python version (for archive generation) |
| `pre-test-command` | string | `''` | Command to run before each JVM test job (e.g. generate test archives) |
| `archives-local-dir` | string | `''` | Local directory with archives to push to device |
| `device-archives-path` | string | `''` | Device path where archives are pushed |
| `coverage-threshold` | number | `80` | Minimum coverage percentage |
| `apk-size-limit-mb` | number | `50` | Maximum APK size in MB |
| `app-name` | string | `app` | App name for coverage badge and artifact naming |
| `retention-days` | number | `7` | Artifact retention days |

### `kotlin-cd.yml`

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `app-name` | string | ✅ | App name for APK filename (e.g. `otter`) |
| `java-version` | string | — | JDK version (default: `21`) |

**Tag conventions**: `v1.0.0` = stable release, `v1.0.0-alpha` / `v1.0.0-rc1` = pre-release (any hyphen suffix)

### `python-push-ci.yml`

Inputs describe the layout only. Python 3.12, line length 120, pylint 7, coverage 80% are the same for every
project; a project's own tool settings (`.flake8`, `pyproject.toml`) are read too. The lint tools are pinned
(`*_VERSION` in `python-lint-checks.yml`): a new release cannot change every project's verdict at once, and a
project formats locally with the same versions.

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `skip-on-no-changes` | boolean | `true` | Skip pipeline if no Python file, requirement file or tool setting changed |
| `scripts-dir` | string | `scripts` | Directory the tools and pytest run from; `.` for the repo root |
| `requirements` | string | `requirements-test.txt` | Requirement files, space-separated, relative to `scripts-dir` |
| `source-dirs` | string | `src` | Source directories: linted, type-checked, scanned, measured by coverage (tests/ is linted too) |
| `exclude-dirs` | string | `''` | Directory names never linted, e.g. deliberately flawed test fixtures |
| `exclude-marker` | string | `local_only` | Marker of tests needing a local-only resource; deselected in every tier and in coverage |

mypy runs on the source dirs without `--exclude` (on the command line it would replace the project's own
setting): a project whose source dirs also hold tests or fixtures excludes them in its mypy config.

### `common-pr-ci.yml`

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `title-pattern` | string | — | Passed to `common-pr-title-validation.yml`: extended regex the title must match; empty keeps `#123: type: description` |
| `contexts-dir` | string | — | Passed to `common-context-check.yml` / `common-context-comment.yml` (default `.claude/contexts`) |
| `code-paths`, `test-paths` | string | — | Passed to `common-context-check.yml` (defaults: Android `app/src/` layout) |

The PR (number, title, head commit) comes from the `pull_request` event; a call from any other event fails its first
job. Its child workflows are called with `./` paths, so pinning `common-pr-ci.yml` to a SHA pins the whole PR pipeline.

### `python-pytest.yml`

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `python-version` | string | `3.12` | Python version |
| `working-directory` | string | `.` | Directory pytest runs from |
| `requirements` | string | `''` | Requirement files, space- or newline-separated, relative to `working-directory`; empty installs pytest only |
| `marker` | string | `''` | Marker expression for `-m` (e.g. `unit and not live_ai`) |
| `extra-args` | string | `''` | Extra pytest arguments, split on whitespace (no quoting) |
| `allow-no-tests` | boolean | `false` | Treat "no tests collected" (exit code 5) as success |

### `common-security-checks.yml`

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `head-sha` | string | `''` | Commit to scan; empty uses `github.sha` |

Dependency vulnerabilities are scanned in Push-CI's lint stage (OSV-Scanner), the APK size in `kotlin-build-apk.yml`
(`apk-size-limit-mb`).

### `common-context-check.yml`

Checks that the context files are updated alongside code changes:

| File | Requirement |
|------|-------------|
| `kanban.md` | **Mandatory** — any change matching `code-paths` |
| `architecture.md` | Warning — when new classes/interfaces/DI detected in those changes |
| `tests.md` | Warning — when a change matches `test-paths` |

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `head-sha` | string | — | Commit to check (required) |
| `contexts-dir` | string | `.claude/contexts` | Directory holding the three files |
| `code-paths` | string | `^app/src/` | Extended regex for changed files that count as code |
| `test-paths` | string | `^app/src/(test\|androidTest)/` | Extended regex for changed files that count as tests |

`common-context-comment.yml` takes the same `contexts-dir`, so its comment names the right files.

### `python-test-markers.yml`

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `scripts-dir` | string | `scripts` | Directory pytest runs from |
| `requirements` | string | `requirements-test.txt` | Requirement files, space-separated |
| `fail-on-violation` | boolean | `true` | `false` reports `total-count` and `unmarked-count` (outputs) without failing |

---

## Testing Condor

Condor runs its own pipelines on itself:

| Workflow | Trigger | Checks |
|----------|---------|--------|
| `condor-lint.yml` | every push | actionlint + shellcheck (warnings and up) on every workflow |
| `condor-test-python.yml` | every push | `python-push-ci.yml` on `tests/fixtures/python-project` (all gates, four tiers, coverage; a `local_only` test fails if it ever runs) and the collection guard on `tests/fixtures/python-project-unmarked` |
| `condor-test-pr.yml` | Condor's PRs | `common-pr-ci.yml` on the PR itself, called like the caller template: title (`#N: type: description`), context files, secret scan |

The Kotlin pipelines are not self-tested yet: that needs an Android fixture project, Gradle and an emulator.

---

## Required Secrets

| Secret | Used by | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | All workflows | Standard GitHub token (auto-provided) |
| `KEYSTORE_PASSWORD` | `kotlin-cd.yml` | Android release keystore password |
| `KEY_PASSWORD` | `kotlin-cd.yml` | Android release key password |
| `GIST_SECRET` | `kotlin-coverage.yml` | Token for updating coverage badge gist |
| `NVD_API_KEY` | `kotlin-nvd-refresh.yml` | NVD API key for OWASP dependency check |
