---
name: planning
description: "Use when starting multi-step tasks, building features, or implementing changes. Creates detailed implementation plans with TDD, exact file paths, and bite-sized tasks before touching code."
---

# Planning Implementation Work

## Overview

Transform requirements into comprehensive implementation plans. Create detailed, step-by-step guides assuming the engineer has zero codebase context. Document everything: exact file paths, complete code, expected test outputs, and frequent commits.

**Announce at start:** "I'm using the planning skill to create the implementation plan."

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/plan-template.md` | Creating new implementation plan |

## When to Use

- **After brainstorming** - When design is validated
- **Multi-step implementation** - More than one component
- **Feature development** - New functionality
- **Complex bug fixes** - Coordinated changes across files

**Skip for:** Single-file edits, obvious quick fixes.

## The Process

### 1. Context Gathering
- Review existing codebase structure
- Identify affected files and dependencies
- Understand testing patterns

### 2. Plan Creation

Load `references/plan-template.md` for full template.

**Key requirements:**
- Each task = 2-5 minutes
- Exact file paths always
- Complete code (no placeholders)
- TDD: test → fail → implement → pass → commit

### 3. 100-Step Stress Test

| Step | Scale | Questions |
|------|-------|-----------|
| 10 | 10k users | Schema/index valid? |
| 50 | High concurrency | Connection pooling? |
| 100 | Maintenance | Readable in 2 years? |

## Task Structure (Quick)

```markdown
### Task N: [Component]

**Files:** Create/Modify/Test with exact paths

**Step 1:** Write failing test
**Step 2:** Run → verify FAIL
**Step 3:** Implement minimal code
**Step 4:** Run → verify PASS
**Step 5:** Commit
```

## Output

Save plans to: `docs/plans/YYYY-MM-DD-<feature>.md`

## Iron Rules

1. **DRY** - Don't Repeat Yourself
2. **YAGNI** - Remove unnecessary features
3. **TDD** - RED-GREEN-REFACTOR every task
4. **Frequent commits** - One logical change each
5. **Exact paths** - Full file paths always
6. **Complete code** - Never "add logic here"
