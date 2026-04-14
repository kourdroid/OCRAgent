---
name: systematic-debugging
description: "Use when debugging any issue - errors, failures, unexpected behavior. Enforces 4-phase root cause analysis instead of symptom-fixing. Prevents bugs from returning in mutated forms."
---

# Systematic Debugging: Root Cause Mastery

## Overview

A bug in production costs 100x more than in development. Do not just "fix" bugs. Trace the root cause. If you fix a symptom but leave the cause, the bug will return in a mutated form.

**Announce at start:** "I'm using the systematic-debugging skill to trace this issue."

## Bundled Resources

| File | Use When |
|------|----------|
| `references/debugging-techniques.md` | Need specific technique (git bisect, logging, isolation) |
| `scripts/generate_bug_report.py` | Creating bug report with environment info |

**Run script:**
```bash
python scripts/generate_bug_report.py bug-report.md
```

## The 4-Phase Process

```
REPRODUCE → ISOLATE → FIX → VERIFY
```

### Phase 1: Reproduce
You cannot fix what you cannot reproduce.

- [ ] Document exact steps to trigger
- [ ] Note environment (OS, versions, config)
- [ ] Create minimal reproduction case
- [ ] Determine frequency (always? intermittent?)

### Phase 2: Isolate
Narrow scope to the exact cause.

**Techniques:**
- **Binary search** - Comment out half the code
- **Git bisect** - Find breaking commit
- **Simplify inputs** - Remove variables until bug disappears
- **Fresh environment** - Rule out cache/state

**The 5 Whys:**
```
Problem: API returns 500
  Why? → Database query throws exception
    Why? → Column 'email' is null
      Why? → Form validation passed but email was empty
        Why? → Validation runs before autocomplete fills field
          Why? → Race condition between autocomplete and validation

Root Cause: Race condition (not "API returns 500")
```

### Phase 3: Fix
Target root cause, not symptom.

**REQUIRED: Test first**
```typescript
// Write test that FAILS before fix
it('should wait for autocomplete before validating', async () => {
  // Arrange → Act → Assert (currently fails)
});

// Then implement minimal fix
// Then run test (should pass)
```

**Minimal fix principle:**
- Fix ONLY the bug
- No refactoring in same commit
- Clear, visible change

### Phase 4: Verify & Prevent

- [ ] Original reproduction steps no longer trigger bug
- [ ] Regression test passes
- [ ] Existing tests still pass
- [ ] Defense-in-depth added (validation, logging, monitoring)

## The Fatal Mistakes

| Mistake | Why It's Fatal | Alternative |
|---------|----------------|-------------|
| Try-catch that swallows | Hides real error | Fix cause, log error |
| `setTimeout` for race condition | Doesn't fix race | Use proper synchronization |
| "Works on my machine" | Env difference IS the bug | Reproduce in CI/staging |
| "Can't reproduce, closing" | Bug will return | Invest more in reproduction |

## Documentation Template

After fixing, document:

```markdown
## Bug: [Brief Description]
**Root Cause:** [Technical explanation]
**Fix:** [What changed and why]
**Regression Test:** tests/path/test.ts::testName
**Prevention:** [What guards were added]
```

## Quick Reference

Load `references/debugging-techniques.md` for:
- Git bisect workflow
- Strategic logging patterns
- Race condition detection
- Memory leak diagnosis
- Network debugging
