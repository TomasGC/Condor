# KANBAN - Condor

Track of work sessions and completed tasks linked to consuming project issues.

---

2026-10-04 - [anglerfish] #53 Discover JVM test tiers from Gradle source sets
- `discover-test-tiers` composite action (read-only Gradle init script) lists test tasks with their test source counts; the Kotlin push pipeline creates one JVM job per task that has tests, and the instrumented job only when a connected task has tests
- Removed the `unit-job` / `mock-job` inputs and the unit, integration-mock and integration-real workflows; the `-DtestType` filter path is gone
- Verified by discovery against Anglerfish only; Raven's and Otter's job lists change on their next run, Raven's caller must drop `unit-job`/`mock-job` (PR #2 open)
tags: #ci-cd #discovery #test-tiers
Ref: https://github.com/TomasGC/Anglerfish/issues/53
Commit: a3832d9

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
