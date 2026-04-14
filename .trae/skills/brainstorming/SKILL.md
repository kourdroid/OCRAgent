---
name: brainstorming
description: "Use before any creative work - creating features, building components, adding functionality, designing systems. Explores user intent and requirements through Socratic dialogue before implementation."
---

# Brainstorming Ideas Into Designs

## Overview

Transform vague ideas into fully-formed designs through collaborative dialogue. Start by understanding the problem space, explore approaches, then present the design incrementally for validation.

**Announce at start:** "I'm using the brainstorming skill to explore this idea."

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/question-templates.md` | Need question examples or design doc template |

## When to Use

- **New feature requests** - Before writing any code
- **Architecture decisions** - System design, data modeling
- **Problem exploration** - When user's intent isn't fully clear
- **Multiple approaches exist** - Need to evaluate trade-offs

**Skip for:** Bug fixes, direct implementation requests.

## The Process

```
CONTEXT → QUESTIONS → APPROACHES → DESIGN
```

### Phase 1: Context
Before asking anything:
- Review codebase structure
- Check recent commits
- Read existing docs
- Identify constraints

### Phase 2: Socratic Dialogue

**The One-Question Rule:** Ask ONE question per message.

**Question priority:**
1. **Multiple choice** - Easiest to answer
2. **Binary** - Clear yes/no decision
3. **Scale** - Quantify priorities (1-10)
4. **Open-ended** - Only when necessary

**Focus areas:**
- Purpose (what problem?)
- Constraints (time, team, tech)
- Success criteria (how measure?)
- Non-goals (what NOT building?)

Load `references/question-templates.md` for examples.

### Phase 3: Approach Options

Present 2-3 approaches:
```markdown
### Option A: [Name] ⭐ Recommended

**What:** [2 sentences]

**Trade-offs:**
| Pros | Cons |
|------|------|
| Fast | Less flexible |

**Why I recommend:** [1-2 sentences]
```

### Phase 4: Design Presentation

Present in 200-300 word sections:
1. Architecture Overview
2. Data Model
3. Component Breakdown
4. Error Handling
5. Testing Strategy

**After each section ask:**
> "Does this align with what you had in mind?"

## The Kleppmann/Martin Lens

Apply to every design:

| Perspective | Questions |
|-------------|-----------|
| **Consistency** | Strong vs eventual needed? |
| **Partitioning** | How does data divide? |
| **Boundaries** | Clear separation of concerns? |
| **Dependencies** | All pointing inward? |

## After the Design

Save to: `docs/plans/YYYY-MM-DD-<topic>-design.md`

Then offer:
- A) **Create Implementation Plan** → Use planning skill
- B) **Pause Here** → Design saved for later
- C) **Iterate Further** → Explore specific areas

## Key Principles

- One question at a time
- Multiple choice preferred
- YAGNI ruthlessly
- Always propose alternatives
- Validate incrementally
