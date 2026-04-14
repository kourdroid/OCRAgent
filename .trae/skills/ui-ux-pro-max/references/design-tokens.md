# Design Tokens Reference

## Token Architecture

Design tokens work in layers:
1. **Primitives** - Raw values (never use directly in components)
2. **Semantic** - Purpose-driven tokens (USE THESE)
3. **Component** - Optional component-specific overrides

---

## CSS Custom Properties (Vanilla CSS)

### Color Tokens
```css
:root {
  /* Primitives - Raw palette */
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;
  
  --blue-50: #eff6ff;
  --blue-500: #3b82f6;
  --blue-600: #2563eb;
  --blue-700: #1d4ed8;
  
  --red-50: #fef2f2;
  --red-500: #ef4444;
  --red-600: #dc2626;
  
  --green-50: #f0fdf4;
  --green-500: #22c55e;
  --green-600: #16a34a;
  
  /* Semantic - USE THESE */
  --color-bg-primary: var(--gray-50);
  --color-bg-secondary: white;
  --color-bg-tertiary: var(--gray-100);
  
  --color-text-primary: var(--gray-900);
  --color-text-secondary: var(--gray-600);
  --color-text-tertiary: var(--gray-400);
  
  --color-border: var(--gray-200);
  --color-border-hover: var(--gray-300);
  
  --color-accent: var(--blue-500);
  --color-accent-hover: var(--blue-600);
  
  --color-error: var(--red-500);
  --color-error-bg: var(--red-50);
  
  --color-success: var(--green-500);
  --color-success-bg: var(--green-50);
}

/* Dark mode */
[data-theme="dark"] {
  --color-bg-primary: var(--gray-900);
  --color-bg-secondary: var(--gray-800);
  --color-bg-tertiary: var(--gray-700);
  
  --color-text-primary: var(--gray-50);
  --color-text-secondary: var(--gray-300);
  --color-text-tertiary: var(--gray-500);
  
  --color-border: var(--gray-700);
  --color-border-hover: var(--gray-600);
}
```

### Spacing Tokens
```css
:root {
  --space-0: 0;
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-20: 5rem;     /* 80px */
  --space-24: 6rem;     /* 96px */
}
```

### Typography Tokens
```css
:root {
  /* Font families */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  /* Font sizes */
  --text-xs: 0.75rem;     /* 12px */
  --text-sm: 0.875rem;    /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 1.875rem;   /* 30px */
  --text-4xl: 2.25rem;    /* 36px */
  --text-5xl: 3rem;       /* 48px */
  
  /* Line heights */
  --leading-tight: 1.25;
  --leading-snug: 1.375;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
  --leading-loose: 2;
  
  /* Font weights */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
}
```

### Border Radius
```css
:root {
  --radius-none: 0;
  --radius-sm: 0.125rem;  /* 2px */
  --radius-md: 0.375rem;  /* 6px */
  --radius-lg: 0.5rem;    /* 8px */
  --radius-xl: 0.75rem;   /* 12px */
  --radius-2xl: 1rem;     /* 16px */
  --radius-full: 9999px;
}
```

### Shadows
```css
:root {
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}
```

---

## Tailwind CSS Configuration

### tailwind.config.js
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class', // or 'media'
  theme: {
    extend: {
      colors: {
        // Semantic colors referencing Tailwind palette
        primary: {
          DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',
          hover: 'rgb(var(--color-primary-hover) / <alpha-value>)',
        },
        background: 'rgb(var(--color-bg) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        // Custom spacing if needed
        '18': '4.5rem',
        '22': '5.5rem',
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
};
```

### CSS Variables for Tailwind
```css
/* globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --color-primary: 59 130 246;       /* blue-500 RGB */
    --color-primary-hover: 37 99 235;  /* blue-600 RGB */
    --color-bg: 249 250 251;           /* gray-50 RGB */
    --color-surface: 255 255 255;      /* white RGB */
  }
  
  .dark {
    --color-bg: 17 24 39;              /* gray-900 RGB */
    --color-surface: 31 41 55;         /* gray-800 RGB */
  }
}
```

---

## Token Naming Conventions

| Category | Naming Pattern | Example |
|----------|---------------|---------|
| Background | `--color-bg-{role}` | `--color-bg-primary` |
| Text | `--color-text-{role}` | `--color-text-secondary` |
| Border | `--color-border-{state}` | `--color-border-hover` |
| Spacing | `--space-{scale}` | `--space-4` |
| Typography | `--text-{size}` | `--text-lg` |
| Shadow | `--shadow-{size}` | `--shadow-md` |

---

## Component Tokens Example

```css
/* Button-specific tokens */
.btn {
  --btn-padding-x: var(--space-4);
  --btn-padding-y: var(--space-2);
  --btn-radius: var(--radius-md);
  --btn-font-size: var(--text-sm);
  --btn-font-weight: var(--font-medium);
  
  padding: var(--btn-padding-y) var(--btn-padding-x);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-size);
  font-weight: var(--btn-font-weight);
}

.btn-lg {
  --btn-padding-x: var(--space-6);
  --btn-padding-y: var(--space-3);
  --btn-font-size: var(--text-base);
}
```
