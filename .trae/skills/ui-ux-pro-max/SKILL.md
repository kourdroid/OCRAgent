---
name: ui-ux-pro-max
description: "Use when designing interfaces, selecting colors, defining typography, or making layout decisions. Enforces design systems, accessibility standards, and data-backed UX reasoning."
---

# UI/UX Pro Max: Design System Mastery

## Overview

A performant backend is useless if the UI is unintuitive. "Good design" is not just pretty colors; it is predictability and accessibility. Stop hardcoding hex values. Every UI decision must be data-backed and justified.

**Announce at start:** "I'm using the ui-ux-pro-max skill for this design work."

## Framework Flexibility

This skill applies to:
- **Vanilla CSS** - Custom properties for tokens
- **Tailwind CSS** - Extended config with semantic tokens
- **CSS-in-JS** - Styled-components, Emotion, Stitches
- **CSS Modules** - With shared token imports

Adapt token strategy to your framework.

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/design-tokens.md` | Setting up tokens (CSS vars, Tailwind config) |
| `references/accessibility.md` | Checking WCAG compliance, ARIA patterns |
| `references/ux-laws.md` | Making layout/interaction decisions |

**Search patterns:**
- Tokens: `grep -i "color\|spacing\|typography\|shadow"`
- Accessibility: `grep -i "contrast\|aria\|focus\|keyboard"`
- UX: `grep -i "fitts\|hick\|gestalt\|miller"`

## The Cardinal Sin

```
❌ Hardcoded values scattered across components:
   Button.tsx:  background: '#3B82F6'
   Card.tsx:    background: '#3b82f6'  ← Different case!
   Header.tsx:  background: 'rgb(59, 130, 246)'

Result: Inconsistent UI, impossible to rebrand, dark mode requires touching 200 files.
```

## Token Architecture

```
Primitives → Semantic → Components
   │              │          │
   ▼              ▼          ▼
--blue-500   --color-accent  --btn-bg
(never use    (USE THESE)   (optional)
 directly)
```

Load `references/design-tokens.md` for implementation.

## Quick Rules

### Colors
- Use semantic tokens, never primitives in components
- Dark mode = change semantic tokens, not components
- Contrast: 4.5:1 text, 3:1 UI components

### Spacing
- Use scale: 4px base (4, 8, 12, 16, 24, 32, 48, 64)
- Related elements: closer together (Gestalt proximity)
- Unrelated elements: further apart

### Typography
- Max 2 font families (sans + mono typically)
- Scale: 12, 14, 16, 18, 20, 24, 30, 36, 48px
- Line height: 1.25 (headings), 1.5 (body)

### Touch Targets
- Minimum: 44×44px (WCAG), 48×48dp (Material)
- Padding trick for small icons

## UI Reasoning Framework

Before every decision:

| Question | Justification Required |
|----------|------------------------|
| Why this color? | Brand, contrast ratio, semantic meaning |
| Why this size? | Touch targets, hierarchy, reading distance |
| Why this position? | Fitts's Law, F-pattern, proximity |
| Why this spacing? | Gestalt, alignment grid |
| Why this animation? | User feedback, state clarity |

Load `references/ux-laws.md` for detailed heuristics.

## Accessibility Checklist

Before shipping:

- [ ] Contrast passes WCAG AA (4.5:1 text, 3:1 UI)
- [ ] Focus indicators visible
- [ ] Keyboard navigation works
- [ ] Touch targets 44×44px minimum
- [ ] `prefers-reduced-motion` respected
- [ ] Screen reader tested

Load `references/accessibility.md` for ARIA patterns.

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Mystery icons | Add labels or tooltips |
| Hidden scrollbars | Show scroll indicators |
| "Creative" form layouts | Standard vertical forms |
| Carousel for important content | Show all or prioritize |
| Inconsistent tokens | Centralize in design system |
