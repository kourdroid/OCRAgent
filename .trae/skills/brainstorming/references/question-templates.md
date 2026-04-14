# Brainstorming Question Templates

## Phase 2: Socratic Dialogue

### Question Types (Prefer in Order)

#### 1. Multiple Choice (Easiest to Answer)
```
For the authentication flow, which approach fits your needs?
A) OAuth2 with social providers (Google, GitHub)
B) Email/password with MFA
C) SSO integration with existing identity provider
D) Magic link (passwordless)
```

```
What's the primary access pattern for this data?
A) Read-heavy (10:1 read/write ratio)
B) Write-heavy (events, logs, time-series)
C) Balanced with complex queries
D) Real-time collaborative editing
```

```
How should the system handle failures?
A) Fail fast, show error immediately
B) Retry silently, show error after retries
C) Queue for later, optimistic UI
D) Graceful degradation, fallback content
```

#### 2. Binary (Clear Decision)
```
Should this component support offline mode?
```

```
Is real-time updates a requirement, or is polling acceptable?
```

```
Do we need to support multiple tenants in this system?
```

```
Should users be able to undo this action?
```

#### 3. Scale (Quantifying Priorities)
```
On a scale of 1-10, how important is:
- Real-time updates vs. implementation simplicity?
- Data consistency vs. availability during network issues?
- Feature completeness vs. time to market?
```

#### 4. Open-ended (Only When Necessary)
```
What's the ideal user experience when they first land on this page?
```

```
What are the three most important things a user must be able to do?
```

```
What existing systems does this need to integrate with?
```

---

## Focus Areas

### Purpose Questions
- What problem does this solve?
- Who is the primary user?
- What does success look like?
- How will we measure success?

### Constraints Questions
- What's the timeline?
- What's the team size/composition?
- What existing infrastructure must be used?
- What's the budget for third-party services?

### Success Criteria Questions
- How do we know it's working?
- What's the acceptable latency?
- What's the target availability?
- What metrics will we track?

### Non-goals Questions (YAGNI)
- What are we explicitly NOT building?
- What can be deferred to v2?
- What features are nice-to-have vs. must-have?

---

## Phase 3: Approach Options Template

```markdown
## Approach Options

### Option A: [Name] ⭐ Recommended

**What:** [2 sentences explaining the approach]

**Trade-offs:**
| Pros | Cons |
|------|------|
| [Pro 1] | [Con 1] |
| [Pro 2] | [Con 2] |

**100-Step Projection:**
- Step 10 (10k users): [Assessment]
- Step 50 (High concurrency): [Assessment]
- Step 100 (Maintenance): [Assessment]

**Why I recommend this:** [1-2 sentences with reasoning]

---

### Option B: [Name]

**What:** [2 sentences]

**Trade-offs:**
| Pros | Cons |
|------|------|
| [Pro 1] | [Con 1] |
| [Pro 2] | [Con 2] |

**100-Step Projection:**
- Step 10: [Assessment]
- Step 50: [Assessment]
- Step 100: [Assessment]

---

### Option C: [Name] (if applicable)

[Same structure]
```

---

## Phase 4: Design Presentation Template

Present in 200-300 word sections:

### Section 1: Architecture Overview
```markdown
## Architecture Overview

[Diagram or ASCII art showing high-level components]

**Components:**
- **[Component A]:** [One sentence purpose]
- **[Component B]:** [One sentence purpose]
- **[Component C]:** [One sentence purpose]

**Key decisions:**
- [Decision 1 and brief rationale]
- [Decision 2 and brief rationale]

---
*Does this architecture align with what you had in mind?*
```

### Section 2: Data Model
```markdown
## Data Model

**Entities:**
- **User:** id, email, name, createdAt
- **Order:** id, userId, status, total, createdAt
- **OrderItem:** id, orderId, productId, quantity, price

**Relationships:**
- User → Orders (1:many)
- Order → OrderItems (1:many)

**Consistency requirements:**
- [Strong/Eventual] consistency for [what]
- [Rationale for choice]

---
*Does this data model cover the requirements?*
```

### Section 3: Component Details
```markdown
## [Component Name] Details

**Responsibility:** [What this component does]

**Inputs:**
- [Input 1 and source]
- [Input 2 and source]

**Outputs:**
- [Output 1 and destination]

**Internal logic:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Error handling:**
- [Error case 1]: [How handled]
- [Error case 2]: [How handled]

---
*Any concerns about this component?*
```

---

## Design Document Output Template

Save to: `docs/plans/YYYY-MM-DD-<topic>-design.md`

```markdown
# [Feature Name] Design Document

**Date:** YYYY-MM-DD
**Status:** Draft | Review | Approved
**Author:** [Name/Agent]

## Problem Statement

[What problem are we solving? Who is affected?]

## Goals

- [Goal 1]
- [Goal 2]

## Non-Goals

- [Explicitly not doing X]
- [Deferring Y to later]

## Solution Overview

[High-level description of the solution]

## Architecture

[Diagrams and component descriptions]

## Data Model

[Entity definitions and relationships]

## API Design

[Endpoint specifications if applicable]

## Error Handling

[How errors are handled]

## Testing Strategy

[What and how to test]

## Rollout Plan

[How this will be deployed]

## Open Questions

- [Question 1]
- [Question 2]
```
