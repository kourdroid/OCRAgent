---
name: react-best-practices
description: "Use when building React components, optimizing renders, preventing hydration issues, or improving frontend performance. Enforces patterns that respect the browser's main thread."
---

# React Best Practices: Performance Mastery

## Overview

"Best performance" means respecting the browser's main thread. A React state update triggers reconciliation. Careless updates force the V8 engine to recalculate layout and repaint unchanged pixels. This causes jank and battery drain.

**Announce at start:** "I'm using the react-best-practices skill for this component."

## Framework Flexibility

This skill applies to:
- **React** (Vite, CRA, custom)
- **Next.js** (App Router, Pages Router)
- **Remix**, **Gatsby**, **Expo** (React Native)

Adapt patterns to your framework's conventions.

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/react-nextjs-patterns.md` | Implementing hydration, data fetching, server components |
| `references/anti-patterns.md` | Debugging render issues, reviewing code |

**Search patterns:**
- Hydration: `grep -i "hydration\|ssr\|server component"`
- Memoization: `grep -i "usememo\|usecallback\|react.memo"`

## Quick Rules

### Render Optimization
1. **No inline objects in JSX** - `style={{}}` creates new ref
2. **No inline callbacks to memo'd children** - Use useCallback
3. **Keys must be stable IDs** - Never array indices
4. **Derived state = compute, don't store** - No useState for transforms

### State Placement Hierarchy
```
URL State     → Shareable, bookmarkable (searchParams)
Server State  → React Query/SWR (cached, revalidated)
Global UI     → Zustand/Jotai (theme, preferences)
Local State   → useState (component-specific)
Derived       → Compute during render
```

### Memoization Decision
```
Should I memo this?
  │
  ├─► Expensive calculation (>1ms)? → useMemo
  ├─► Reference passed to memo'd child? → useMemo/useCallback
  └─► Otherwise? → Don't memo (overhead > benefit)
```

## Hydration: The Silent Killer

**Problem:** Server renders X, client renders Y → React discards HTML → TTI doubles.

**Common triggers:**
- `Date.now()`, `Math.random()` 
- `window` / `document` access
- Browser locale differences

**Fix:** Defer client-only content with useEffect + mounted check.

See `references/react-nextjs-patterns.md` for implementation.

## Component Structure

```typescript
// 1. Types
interface Props { ... }

// 2. Component
export function Component({ data }: Props) {
  // 3. Hooks (consistent order)
  const router = useRouter();
  const [state, setState] = useState(initial);
  const derived = useMemo(() => compute(data), [data]);
  
  // 4. Handlers (memoized if passed to children)
  const handleClick = useCallback(() => { ... }, [deps]);
  
  // 5. Effects (last, before render)
  useEffect(() => { ... }, [dep]);
  
  // 6. Early returns
  if (!data) return <Skeleton />;
  
  // 7. Main render
  return <div>...</div>;
}
```

## Performance Checklist

Before shipping:

- [ ] No inline objects (`style={{}}`, `options={{}}`)
- [ ] No inline callbacks to memo'd children
- [ ] Keys are stable IDs
- [ ] Expensive calculations in useMemo
- [ ] No derived state in useState
- [ ] Images have width/height (no layout shift)
- [ ] Long lists virtualized (>100 items)
- [ ] Tested for hydration mismatches

## Profiling Workflow

1. **React DevTools Profiler** - Find slow components
2. **Chrome Performance** - Long tasks, layout thrashing
3. **Lighthouse** - TTI, TBT, CLS

**Measure first. Never optimize based on intuition.**
