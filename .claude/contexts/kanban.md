# KANBAN - Condor

Track of work sessions and completed tasks linked to consuming project issues.

---

2026-06-21 - [otter] #44 Migrate otter CI/CD to condor and scaffold hub
- Scaffolded kotlin pipeline: push-ci, cd, nvd-refresh and reusable stages (validation, lint, unit/integration/instrumented tests, build, coverage)
- Scaffolded python pipeline: push-ci and reusable stages (detect-changes, lint, unit/integration/e2e tests, coverage)
- Added common/pr-ci.yml orchestrator (PR title validation, context-check, security-checks)
- Added common/reusable: check-pr-exists, pr-title-validation, context-check, context-comment, security-checks
- Replaced free-form pre-instrumented-command with structured pre-test-command + archives-local-dir + device-archives-path
- Updated cd.yml: any hyphen suffix = pre-release (v*-alpha, v*-rc1)
tags: #scaffold #kotlin #python #common #ci-cd #pr-validation #security
Ref: https://github.com/TomasGC/otter/issues/44
Commit: 611c8cc

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
