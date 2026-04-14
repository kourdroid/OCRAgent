# UX Laws and Heuristics Reference

## Fitts's Law

**Time to reach target = Distance / Size**

### Implications
| Principle | Application |
|-----------|-------------|
| Large targets are faster | Primary actions should be larger |
| Near targets are faster | Related actions should be grouped |
| Edges are infinite | Menus at edges require less precision |
| Corners are special | Most accessible points on screen |

### Application
```
PRIMARY BUTTON: Large, prominent, close to content
┌─────────────────────────────────────────────────┐
│  Form content...                                │
│                                                 │
│  [         Submit (Full Width)         ]        │
└─────────────────────────────────────────────────┘

DESTRUCTIVE BUTTON: Smaller, intentional friction
┌─────────────────────────────────────────────────┐
│  Are you sure?                                  │
│                                                 │
│  [     Cancel (Large)     ]    [Delete (Small)] │
└─────────────────────────────────────────────────┘
```

---

## Hick's Law

**Decision time = log₂(n + 1)** where n = number of choices

### Implications
- More options = slower decisions
- Group related options to reduce perceived complexity
- Progressive disclosure reduces cognitive load

### Application
```
❌ OVERWHELMING: 12 options at once
┌─────────────────────────────────────────────────┐
│  [A] [B] [C] [D] [E] [F] [G] [H] [I] [J] [K] [L]│
└─────────────────────────────────────────────────┘

✅ PROGRESSIVE DISCLOSURE
┌─────────────────────────────────────────────────┐
│  [Primary A]  [Primary B]  [More Options ▼]     │
└─────────────────────────────────────────────────┘
```

---

## Gestalt Principles

### Proximity
Elements close together are perceived as related.

```
RELATED (grouped)         UNRELATED (separated)
┌─────────────────┐       ┌─────────────────┐
│ Label           │       │ Label           │
│ [Input field]   │       │                 │
│ Helper text     │       │                 │
└─────────────────┘       │ [Input field]   │
                          │                 │
                          │ Helper text     │
                          └─────────────────┘
```

### Similarity
Similar elements are perceived as related.

```
GROUPED BY COLOR          GROUPED BY SHAPE
● ● ● ○ ○ ○               ● ■ ● ■ ● ■
```

### Continuity
Eyes follow smooth paths.

### Closure
Minds complete incomplete shapes.

### Figure-Ground
Elements are perceived as either foreground or background.

---

## Miller's Law

**Working memory holds 7 ± 2 items**

### Implications
- Chunk phone numbers: 555-123-4567 not 5551234567
- Limit navigation items to 5-7
- Paginate when more than 7 items need comparison

---

## Jakob's Law

**Users spend most time on OTHER sites**

### Implications
- Follow conventions (logo top-left, nav at top)
- Standard patterns reduce learning curve
- Innovation in function, not in basic interaction

---

## Peak-End Rule

**Users judge experience by peak moment and end**

### Implications
- Make checkout/completion feel rewarding
- End flows with positive confirmation
- Handle errors gracefully (peaks can be negative)

---

## Aesthetic-Usability Effect

**Attractive things are perceived as easier to use**

### Implications
- Visual polish increases trust
- Users forgive minor usability issues if design is beautiful
- First impressions matter significantly

---

## Doherty Threshold

**Response time < 400ms feels instantaneous**

### Implications
| Response Time | Perception |
|---------------|------------|
| < 100ms | Instant |
| 100-400ms | Fast |
| 400ms-1s | Noticeable delay |
| > 1s | Show loading indicator |
| > 10s | Keep user informed of progress |

---

## Serial Position Effect

**First and last items are remembered best**

### Implications
- Put important items at start and end of lists
- Middle items get least attention
- Navigation: Home first, CTA last

---

## Von Restorff Effect (Isolation Effect)

**Unique items are remembered better**

### Implications
- Make CTAs visually distinct
- Highlight important information differently
- Use contrast to draw attention

---

## Decision Matrix Template

Use when evaluating UI choices:

| Criterion | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Fitts compliance | 3 | 4 | 3 | 2 |
| Hick compliance | 2 | 3 | 4 | 3 |
| Accessibility | 3 | 4 | 2 | 4 |
| Convention match | 2 | 3 | 4 | 3 |
| **Weighted Total** | | **35** | **31** | **29** |

Score 1-5, multiply by weight, sum totals.
