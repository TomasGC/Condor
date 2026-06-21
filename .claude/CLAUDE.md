# Project Instructions - Condor

**Purpose**: Reusable GitHub Actions workflow hub for TomasGC projects (and the community)
**Last Updated**: 2026-06-21

---

## Project Context

@contexts/kanban.md
@contexts/architecture.md

---

## Hard Constraints (Non-Negotiable)

### Version Control Rules

#### Commit Format

**Format**: `[project] #XXX: type: description`

- `[project]` — the consuming repo that triggered the work (e.g., `[otter]`, `[lynx]`)
- `#XXX` — issue number in that repo
- `type` — feat, fix, refactor, test, docs, chore

**Examples**:
```
[otter] #44: feat: add common PR pipeline and security checks
[otter] #44: fix: resolve context-check path for tests.md
[lynx] #12: feat: add dotnet pipeline
```

**Rules**:
- Always prefix with consuming project + issue number
- No stats (+XX lines), no implementation details, no emoji
- If change benefits all projects with no single driver: `[condor] #N: ...` using condor's own issue

**Branch naming**:
- Features: `feature/[project]-#XXX-description` (e.g., `feature/otter-#44-common-pipeline`)
- Bugfixes: `bugfix/[project]-#XXX-description`

---

### Testing Requirements

No build step — condor is pure YAML.

Validation before commit:
- YAML syntax: `yamllint .github/workflows/` (if yamllint available)
- Verify inputs/outputs referenced in orchestrators match definitions in reusables
- Check `uses: ./` paths resolve correctly within condor

---

### Documentation Rules

**Public files** (committed):
- `README.md` — pipeline usage, inputs reference, secrets table
- `.claude/CLAUDE.md` — this file
- `.claude/contexts/kanban.md` — task log
- `.claude/contexts/architecture.md` — workflow structure

**Private files** (gitignored):
- `.claude/*.local.*`
- `.claude/tmpclaude/`
- `.claude/sessions/`
- `.claude/logs/`

---

## Architecture Principles

### Workflow Design

1. **Single concern per file** — each reusable does one thing
2. **Orchestrators only aggregate** — push-ci, pr-ci, cd define order and data flow only
3. **Explicit inputs** — no free-form shell strings; use structured inputs for complex pre/post steps
4. **Cross-repo compatible** — `actions/checkout` runs in caller's repo context; scripts must live in caller's repo
5. **Secrets inherit** — orchestrators pass `secrets: inherit`; reusables declare only what they use

### Adding a New Pipeline

1. Create `<lang>/reusable/<stage>.yml` for each concern
2. Create `<lang>/push-ci.yml` orchestrator calling reusables via `./` paths
3. Document in `README.md` inputs table
4. Update `contexts/architecture.md`

---

## Communication Style

**Code/Documentation/Commits**: English (always)
**Conversation**: French or English per session

---

## Project Documentation Files

- `README.md` — public pipeline reference
- `.claude/contexts/kanban.md` — task log
- `.claude/contexts/architecture.md` — workflow structure and design decisions

---

**End of Project Instructions**
