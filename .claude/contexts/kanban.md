# KANBAN - Condor

Track of work sessions and completed tasks linked to consuming project issues.

---

2026-10-06 - [condor] #15 Generic Kotlin push pipeline with test tiers as inputs
- `kotlin-gradle-tier.yml`: one test tier, one matrix job per Gradle command (JSON list input); an empty list skips the tier
- `kotlin-push-ci.yml`: validation and lint beside the unit tier; unit, integration-mock and integration-real chained; build-apk and coverage after integration-real; instrumented-tests when `instrumented-task` is set
- Inputs `unit-tasks`, `integration-mock-tasks`, `integration-real-tasks`, `instrumented-task`; `kotlin-instrumented-tests.yml` takes `test-task`. Removed `unit-job`/`mock-job` and the three tier workflows
- Verified from a throwaway Anglerfish branch pinned to the commit: unit matrix, integration tiers, coverage, build-apk and both instrumented shards green
tags: #ci #kotlin #matrix #condor
Ref: https://github.com/TomasGC/Condor/issues/15
Commit: 8c80945

---
2026-10-05 - [meerkat] #2 Run the test suites on GitHub Actions from any checkout
- `python-push-ci.yml` is the one Python pipeline of every project (Kotlin apps' scripts, Meerkat): each tier, coverage included, selects tests by marker (`<tier> and not <exclude-marker>`) through the new `python-pytest.yml`; projects differ only by layout inputs (`scripts-dir`, `requirements`, `source-dirs`, `exclude-dirs`, `exclude-marker`), thresholds are the same for all
- The per-directory tier workflows are removed: they ran only `tests/unit/{android,cli,common}/` (29 Otter unit tests never ran in CI). Breaking for Otter, Raven, Anglerfish: each must mark tests by tier directory (one issue per repo, step 1 pins Condor)
- `common-pr-ci.yml` calls its children with `./` paths (a SHA pin covers the whole PR pipeline) and forwards `contexts-dir`, `code-paths`, `test-paths`, `dependency-check`, `apk-size-check`; `common-security-checks.yml` and the context check/comment take them, defaults unchanged
- Lint tools pinned in one place (isort 9 had re-sorted imports isort 8 accepted); pip upgraded before pip-audit, which audits the runner's own pip
- Collection guard (`python-test-markers.yml`): fails on tests without a tier marker or an empty suite, so missing markers can no longer pass silently; `title-pattern` input for the PR title check
- Condor tests itself: actionlint + shellcheck on every push (six unparseable pushes of `kotlin-push-ci.yml` on 2026-10-04 went unnoticed), the Python pipeline on fixture projects, the PR pipeline on Condor's own PRs; the static check found a branch-name script injection in `common-security-checks.yml` and a dead `softprops/action-gh-release@v1` in `kotlin-cd.yml`, both fixed
- Validated end to end: Meerkat's Push-CI green on GitHub against this branch, after a Linux rehearsal of every job script
- README: every `uses:` path is the flat file GitHub resolves (`kotlin-push-ci.yml`, not `kotlin/push-ci.yml`), SHA pinning note, inputs of the new and changed workflows
tags: #python #pytest #markers #security #context-check #docs
Refs: https://github.com/TomasGC/Meerkat/issues/2, https://github.com/TomasGC/Condor/issues/8
Commits: ebb9aab, ecaf9ed, 26d7561, 62868cc, 5587017, db39438, 5072c52, 451224a, dc63df3, cbdba97
---

2026-08-06 - [otter] #36 File Type Icons and Folder Content Counts
- Added docs-only pipeline skip: push with only .md changes skips all kotlin and python pipeline jobs
- Extracted docs-only detection into shared composite action (.github/actions/check-docs-only/action.yml); called by kotlin-detect-changes and python-detect-changes via push SHA diff (git diff --name-only before..after)
- Replaced dorny/paths-filter non-docs approach (broken in nested workflow_call context — falls back to branch-vs-main comparison) with shell-based approach using github.event.before/after
tags: #ci-cd #docs-only #composite-action
Ref: https://github.com/TomasGC/otter/issues/36
Commit: c1c367e

---

2026-08-05 - [otter] #38 Enable Test Parallelization
- Removed avd-setup job: AVD snapshots unreliable across ephemeral runners (different hardware/hypervisor → QEMU state invalid)
- Each shard is now self-contained: install emulator + create AVD + cold boot + run tests on same runner
- Cache system image (reliable cross-runner, just files) but no AVD snapshot cache
- Added explicit sdkmanager --install "emulator" step (pixel4api30Setup only installs system image, not emulator binary)
- 2-shard parallel test execution via numShards/shardIndex; emulator timeout 600s per shard
tags: #instrumented-tests #emulator #caching #sharding #performance
Ref: https://github.com/TomasGC/otter/issues/38
Commit: bb57e3d

---

2026-06-23 - [otter] #44 Migrate otter CI/CD to condor and scaffold hub
- Scaffolded kotlin pipeline: push-ci, cd, nvd-refresh and reusable stages (validation, lint, unit/integration/instrumented tests, build, coverage)
- Scaffolded python pipeline: push-ci and reusable stages (detect-changes, lint, unit/integration/e2e tests, coverage)
- Added common/pr-ci.yml orchestrator and reusable workflows (check-pr-exists, pr-title-validation, context-check, security-checks)
- Replaced free-form pre-instrumented-command with structured pre-test-command + archives-local-dir + device-archives-path; fixed adb push to file-by-file loop
- Converted kotlin-nvd-refresh.yml to workflow_call to fix OWASP NVD cache bootstrap from otter context
- Updated cd.yml: hyphen suffix = pre-release; fixed PR-CI noise by adding check-pr job before condor call
tags: #scaffold #kotlin #python #common #ci-cd #pr-validation #security #owasp #nvd #adb
Ref: https://github.com/TomasGC/otter/issues/44
Commits: 611c8cc, 06c2d43

---

## Notes

- **One entry per issue** — updated each time you work on it
- **Date** — last update date
- **Title line**: `YYYY-MM-DD - [project] #ID Title`
- **Description** — bullet points describing work done (max 6 lines)
- **Tags** — `tag:` (singular) or `tags:` (plural) with # prefix
- **Ref/Refs** — link to consuming project's issue
- **Commit/Commits** — short hashes (7 chars)
- **Language**: English only
