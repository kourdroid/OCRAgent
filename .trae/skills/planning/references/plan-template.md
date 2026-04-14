# Implementation Plan Template Reference

## Plan Header

```markdown
# [Feature Name] Implementation Plan

> **For Agent:** Use systematic execution with verification between tasks.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**100-Step Stress Test:**
- Step 10 (10k users): [Schema/index considerations]
- Step 50 (High concurrency): [Connection pooling/event loop]
- Step 100 (Maintenance): [Readability/testability]

---
```

## Task Structure

### Granularity
Each step = ONE action (2-5 minutes):
- "Write the failing test" → 1 step
- "Run test to verify it fails" → 1 step
- "Implement minimal code" → 1 step
- "Run test to verify pass" → 1 step
- "Commit" → 1 step

### Task Template
```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/new-file.ts`
- Modify: `exact/path/to/existing.ts:123-145`
- Test: `tests/exact/path/to/test.ts`

**Step 1: Write the failing test**

\`\`\`typescript
import { describe, it, expect } from 'vitest';
import { functionName } from '../src/module';

describe('functionName', () => {
  it('should [specific behavior]', () => {
    // Arrange
    const input = { ... };
    
    // Act
    const result = functionName(input);
    
    // Assert
    expect(result).toEqual(expected);
  });
});
\`\`\`

**Step 2: Run test to verify it fails**

\`\`\`bash
npm test -- --grep "should [specific behavior]"
\`\`\`

Expected: FAIL with "functionName is not defined"

**Step 3: Write minimal implementation**

\`\`\`typescript
export function functionName(input: InputType): OutputType {
  // Minimal implementation to pass test
  return expected;
}
\`\`\`

**Step 4: Run test to verify it passes**

\`\`\`bash
npm test -- --grep "should [specific behavior]"
\`\`\`

Expected: PASS

**Step 5: Commit**

\`\`\`bash
git add src/module.ts tests/module.test.ts
git commit -m "feat(module): add functionName"
\`\`\`
```

---

## File Path Conventions

### Exact Paths Required
```markdown
✅ GOOD:
- Create: `src/features/auth/services/token-service.ts`
- Modify: `src/features/auth/routes/login.ts:45-67`
- Test: `tests/unit/features/auth/token-service.test.ts`

❌ BAD:
- Create: token service file
- Modify: the login route
- Test: add tests for token service
```

### Line Range References
When modifying existing files, include line ranges:
```markdown
- Modify: `src/api/users.ts:23-35` (the `createUser` function)
```

---

## Code Examples in Plans

### Complete, Copy-Paste Ready
```markdown
✅ GOOD: Full implementation
\`\`\`typescript
import { z } from 'zod';

const userSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

export function validateUser(data: unknown) {
  return userSchema.parse(data);
}
\`\`\`

❌ BAD: Placeholder
\`\`\`typescript
export function validateUser(data: unknown) {
  // Add validation logic here
}
\`\`\`
```

---

## Expected Output Format

### Commands Include Expected Results
```markdown
✅ GOOD:
**Run:** `npm test -- --grep "createUser"`
**Expected:** 
- PASS: "should create user with valid data"
- PASS: "should reject invalid email"

❌ BAD:
**Run:** `npm test`
```

---

## Commit Message Conventions

### Format
```
<type>(<scope>): <description>

[optional body]
```

### Types
| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `test` | Adding tests |
| `refactor` | Code change (no new feature/fix) |
| `docs` | Documentation |
| `chore` | Build, config, deps |

### Examples
```bash
git commit -m "feat(auth): add JWT token refresh"
git commit -m "fix(api): handle null email in user creation"
git commit -m "test(auth): add token expiration tests"
```

---

## Plan Verification Checklist

Before presenting plan:

- [ ] Every task is 2-5 minutes max
- [ ] Every file path is exact (absolute or relative from root)
- [ ] Every code block is complete (copy-paste ready)
- [ ] Every test command includes expected output
- [ ] Every task ends with commit step
- [ ] No placeholders like "add logic here"
- [ ] Dependencies are handled first
- [ ] TDD order: test → fail → implement → pass → commit
