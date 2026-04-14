---
name: senior-architect
description: "Use when designing system architecture, selecting databases, planning microservices, or decoupling business logic from infrastructure. Applies Hexagonal Architecture, CQRS, and Event Sourcing patterns."
---

# Senior Architect: System Design Mastery

## Overview

You cannot scale a system built on hopes and dreams. This skill enforces patterns that decouple your logic from your infrastructure, preventing the fatal mistake of coupling database schemas to API responses.

**Announce at start:** "I'm using the senior-architect skill for this system design."

## When to Use

- **New system design** - Greenfield architecture decisions
- **Database selection** - Choosing the right data store
- **Scaling bottlenecks** - Current architecture can't handle load
- **Service decomposition** - Breaking monoliths into services

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/database-selection.md` | Choosing or evaluating databases |
| `references/architecture-patterns.md` | Implementing Hexagonal/CQRS/Event Sourcing |

**Search patterns for references:**
- Database: `grep -i "postgresql\|cassandra\|redis\|consistency"` 
- Patterns: `grep -i "hexagonal\|cqrs\|event sourcing\|saga"`

## The Process

### 1. Understand the Problem Domain
- What are the core business entities?
- What operations must be transactional?
- What are the read/write patterns?

### 2. Apply the 100-Step Projection

| Step | Scale | Questions |
|------|-------|-----------|
| 10 | 10k users | Does schema support sharding? Index strategy? |
| 50 | High concurrency | Connection pooling? Event loop blocked? |
| 100 | Maintenance | Can a junior understand this in 2 years? |

### 3. Select Architecture Pattern
- **Simple CRUD**: Skip complexity, use direct database access
- **Complex domains**: Hexagonal Architecture (see `references/architecture-patterns.md`)
- **Read/write separation needed**: CQRS
- **Audit trail required**: Event Sourcing

### 4. Select Database
Load `references/database-selection.md` and apply decision matrix.

**Quick rule:** If unsure, PostgreSQL is correct 90% of the time.

### 5. Design for Failure
- What happens when each component fails?
- How do we detect failures?
- What's the recovery strategy?

## Output Format

When using this skill, produce:

1. **Architecture Decision Record (ADR)**
   - Context, Decision, Consequences

2. **System Diagram** (Mermaid)
   - Component boundaries
   - Data flow direction
   - Sync vs async communication

3. **Failure Mode Analysis**
   - Component failure scenarios
   - Recovery strategies

## Anti-Patterns to Reject

| Anti-Pattern | Alternative |
|--------------|-------------|
| Distributed Monolith | True service boundaries |
| Shared Database | Database per service |
| Synchronous Chains | Async messaging |
| Premature Microservices | Start monolith, extract later |
