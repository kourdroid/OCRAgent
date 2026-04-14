# Accessibility Standards Reference (WCAG 2.1 AA)

## Color Contrast Requirements

| Element Type | Minimum Ratio | Example |
|--------------|---------------|---------|
| Body text | 4.5:1 | Dark gray on white |
| Large text (18px+ or 14px bold) | 3:1 | Medium gray on white |
| UI components (buttons, inputs) | 3:1 | Border color vs background |
| Focus indicators | 3:1 | Focus ring vs background |
| Icons (informational) | 3:1 | Icon color vs background |

### Contrast Checking Tools
- Browser DevTools (Styles panel shows contrast)
- WebAIM Contrast Checker
- Stark (Figma plugin)

---

## Keyboard Navigation

### Focus Order
- Tab order follows visual order (left-to-right, top-to-bottom)
- Skip links for content-heavy pages
- No keyboard traps (can always tab away)

### Focus Visibility
```css
/* ✅ CORRECT: Visible focus indicator */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Remove default only if custom is better */
:focus:not(:focus-visible) {
  outline: none;
}

/* ❌ WRONG: Never do this without replacement */
*:focus { outline: none; }
```

### Keyboard Shortcuts
| Action | Key |
|--------|-----|
| Activate button/link | Enter or Space |
| Close modal | Escape |
| Navigate menu | Arrow keys |
| Submit form | Enter |

---

## Semantic HTML

### Landmark Regions
```html
<header role="banner">
  <nav role="navigation" aria-label="Main">...</nav>
</header>

<main role="main">
  <article>...</article>
  <aside role="complementary">...</aside>
</main>

<footer role="contentinfo">...</footer>
```

### Heading Hierarchy
```html
<!-- ✅ CORRECT: Single H1, sequential headings -->
<h1>Page Title</h1>
  <h2>Section 1</h2>
    <h3>Subsection 1.1</h3>
  <h2>Section 2</h2>

<!-- ❌ WRONG: Skipped levels, multiple H1s -->
<h1>Title</h1>
<h1>Another Title</h1>
<h3>Skipped H2</h3>
```

---

## ARIA Patterns

### Interactive Elements
```html
<!-- Button with loading state -->
<button 
  aria-busy="true" 
  aria-label="Submitting form"
  disabled
>
  <span aria-hidden="true">⏳</span>
  Submitting...
</button>

<!-- Toggle button -->
<button 
  aria-pressed="true" 
  aria-label="Dark mode enabled"
>
  🌙
</button>

<!-- Expandable section -->
<button 
  aria-expanded="false" 
  aria-controls="section1"
>
  Show Details
</button>
<div id="section1" hidden>...</div>
```

### Forms
```html
<!-- ✅ CORRECT: Labeled inputs with errors -->
<div>
  <label for="email">Email</label>
  <input 
    id="email"
    type="email"
    aria-describedby="email-error email-hint"
    aria-invalid="true"
  />
  <span id="email-hint">We'll never share your email</span>
  <span id="email-error" role="alert">Invalid email format</span>
</div>

<!-- ❌ WRONG: No label, placeholder as label -->
<input type="email" placeholder="Email" />
```

### Live Regions
```html
<!-- Polite: Announces when idle -->
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

<!-- Assertive: Interrupts immediately (use sparingly) -->
<div aria-live="assertive" role="alert">
  {errorMessage}
</div>
```

---

## Motion and Animation

### Reduce Motion
```css
/* Default: Allow animations */
.animated {
  transition: transform 0.3s ease;
}

/* Reduce for users who prefer it */
@media (prefers-reduced-motion: reduce) {
  .animated {
    transition: none;
  }
  
  /* Or use reduced animation */
  .animated {
    transition: opacity 0.1s ease; /* Fade only */
  }
}
```

### Pause Controls
- Carousels: Auto-pause on hover/focus
- Videos: Provide play/pause controls
- Auto-playing content: Maximum 5 seconds before stopping

---

## Touch Targets

### Minimum Sizes
| Platform | Minimum | Recommended |
|----------|---------|-------------|
| Mobile (WCAG) | 44×44px | 48×48px |
| iOS (Apple HIG) | 44×44pt | 48×48pt |
| Android (Material) | 48×48dp | 56×56dp |

### Implementation
```css
/* ✅ Ensure clickable area even for small visual */
.icon-button {
  /* Visual size */
  width: 24px;
  height: 24px;
  
  /* Touch target */
  padding: 12px;
  margin: -12px;
  
  /* Or use pseudo-element */
  position: relative;
}

.icon-button::before {
  content: '';
  position: absolute;
  inset: -12px;
}
```

---

## Screen Reader Testing Checklist

- [ ] All images have alt text (or empty alt for decorative)
- [ ] All form inputs have labels
- [ ] Error messages are announced (aria-live or role="alert")
- [ ] Modal focus is trapped inside
- [ ] Modal closes with Escape key
- [ ] Skip link available for main content
- [ ] Page title describes current page
- [ ] Headings form logical outline
- [ ] Links have descriptive text (not "click here")
- [ ] Tables have headers and caption
