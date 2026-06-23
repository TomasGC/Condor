# KANBAN - Condor

Track of work sessions and completed tasks linked to consuming project issues.

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
