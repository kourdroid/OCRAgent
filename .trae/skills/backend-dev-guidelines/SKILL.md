---
name: backend-dev-guidelines
description: "Use when writing backend code, APIs, or services. Enforces code standards that ensure another engineer can understand your code in 5 minutes, not 5 days."
---

# Backend Development Guidelines

## Overview

Code is read 10x more than written. "Clever" code is a liability. These guidelines ensure another engineer can understand your code in 5 minutes, not 5 days. Standardization over cleverness. Explicitness over magic.

**Announce at start:** "I'm using the backend-dev-guidelines skill for this implementation."

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/error-handling.md` | Implementing error handling, exceptions, retries |
| `references/logging-observability.md` | Setting up logging, metrics, tracing |
| `scripts/code_review_checklist.py` | Running code review |

**Run scripts:**
```bash
python scripts/code_review_checklist.py                # Full checklist
python scripts/code_review_checklist.py security       # Security-focused
python scripts/code_review_checklist.py pr-review.md   # Save to file
```

## Quick Rules

### Naming
- **Functions:** verb + noun (`getUserById`, `createOrder`)
- **Booleans:** is/has/can/should prefix (`isActive`, `hasPermission`)
- **Constants:** SCREAMING_SNAKE_CASE

### Functions
- Single responsibility
- No more than 3-4 parameters
- Pure where possible (no hidden side effects)
- All paths return consistent types

### Error Handling
- Never swallow errors
- Use specific error types
- Catch at boundaries, not everywhere
- Log with context and stack trace

Load `references/error-handling.md` for patterns.

### Validation
- Validate at API boundaries (Zod, Pydantic)
- Don't trust internal calls either
- Parameterized queries only

## Project Structure

```
src/
├── domain/           # Business logic (no I/O)
├── application/      # Use cases (orchestration)
├── infrastructure/   # External concerns (DB, APIs)
├── interfaces/       # Entry points (HTTP, CLI)
└── config/           # Configuration, DI
```

**Rule:** Dependencies point inward. Domain knows nothing about DB.

## The 5-Minute Test

Can a new engineer, with no context:
- [ ] Understand what this function does in 30 seconds?
- [ ] Identify all side effects immediately?
- [ ] Know what errors can be thrown?
- [ ] Trace the data flow without running code?

If NO → code needs work.

## Logging

Load `references/logging-observability.md` for details.

Quick rules:
- Structured JSON logs
- Request IDs propagated
- No sensitive data in logs
- Log external calls with duration

## Testing

```typescript
describe('Component', () => {
  it('should [expected behavior]', () => {
    // Arrange
    const input = { ... };
    
    // Act
    const result = component.method(input);
    
    // Assert
    expect(result).toEqual(expected);
  });
});
```

## Checklist Before Commit

- [ ] Function names describe what they do
- [ ] All side effects explicit
- [ ] Error handling complete
- [ ] Input validation at boundaries
- [ ] Logs are structured
- [ ] Tests cover happy + error paths
- [ ] No hardcoded secrets
- [ ] Database queries indexed
