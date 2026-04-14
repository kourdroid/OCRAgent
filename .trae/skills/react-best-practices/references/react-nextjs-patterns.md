# React/Next.js Performance Patterns

## Framework Compatibility

This reference applies to:
- **React** (Vite, CRA, custom setups)
- **Next.js** (App Router and Pages Router)
- **Remix** (React-based, different data patterns)
- **Gatsby** (Static generation focus)

Adapt patterns to your framework's conventions.

---

## Hydration Mismatch Prevention

### The Problem
Server HTML differs from client render → React discards HTML → Double render → TTI doubles.

### Next.js App Router
```typescript
// ✅ Use 'use client' only where needed
'use client';

import { useState, useEffect } from 'react';

export function ClientOnlyComponent() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!mounted) return <Skeleton />;
  
  // Safe to use browser APIs
  return <div>{window.innerWidth}</div>;
}
```

### Dynamic Import (SSR disabled)
```typescript
// Next.js
import dynamic from 'next/dynamic';

const Chart = dynamic(() => import('./Chart'), { 
  ssr: false,
  loading: () => <ChartSkeleton />
});

// Vite/React
import { lazy, Suspense } from 'react';
const Chart = lazy(() => import('./Chart'));

function Dashboard() {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <Chart />
    </Suspense>
  );
}
```

### Common Hydration Triggers
| Cause | Fix |
|-------|-----|
| `Date.now()` or `new Date()` | Server/client time differs → useEffect |
| `Math.random()` | Different values → seed or useEffect |
| `window` / `document` | Undefined on server → useEffect check |
| Browser locale | Format server-side or defer |
| Extension injected elements | Can't prevent, handle gracefully |

---

## Memoization Patterns

### React.memo with Custom Comparison
```typescript
interface Item {
  id: string;
  name: string;
  metadata: Record<string, unknown>;
}

const MemoizedItem = React.memo(function Item({ item }: { item: Item }) {
  return <div>{item.name}</div>;
}, (prevProps, nextProps) => {
  // Only re-render if id or name changes
  return prevProps.item.id === nextProps.item.id 
      && prevProps.item.name === nextProps.item.name;
});
```

### useMemo Decision Tree
```
Should I useMemo this?
       │
       ├─► Is it an expensive calculation (>1ms)?
       │   └─► YES → useMemo
       │
       ├─► Is it a reference passed to memo'd child?
       │   └─► YES → useMemo
       │
       └─► Is it a dependency of useEffect/useCallback?
           └─► YES (and reference changes) → useMemo
           
Otherwise: Don't useMemo (overhead > benefit)
```

### useCallback When Required
```typescript
// ✅ REQUIRED: Passed to memo'd child
const MemoChild = React.memo(function Child({ onClick }: { onClick: () => void }) {
  return <button onClick={onClick}>Click</button>;
});

function Parent() {
  const handleClick = useCallback(() => {
    dispatch({ type: 'INCREMENT' });
  }, [dispatch]);
  
  return <MemoChild onClick={handleClick} />;
}
```

---

## Next.js Specific Patterns

### Server Components (App Router)
```typescript
// app/users/page.tsx - Server Component by default
async function UsersPage() {
  // Direct database access, no API needed
  const users = await db.user.findMany();
  
  return (
    <div>
      {users.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
      {/* Client component for interactivity */}
      <AddUserButton />
    </div>
  );
}

// components/AddUserButton.tsx - Client Component
'use client';
export function AddUserButton() {
  const [open, setOpen] = useState(false);
  return <button onClick={() => setOpen(true)}>Add User</button>;
}
```

### Data Fetching Patterns
```typescript
// Next.js 13+ App Router
async function ProductPage({ params }: { params: { id: string } }) {
  const product = await getProduct(params.id);
  
  return (
    <div>
      <ProductDetails product={product} />
      <Suspense fallback={<ReviewsSkeleton />}>
        <Reviews productId={params.id} />
      </Suspense>
    </div>
  );
}

// Streaming with Suspense
async function Reviews({ productId }: { productId: string }) {
  const reviews = await getReviews(productId); // Can be slow
  return <ReviewList reviews={reviews} />;
}
```

### Route Segment Config
```typescript
// Static generation
export const dynamic = 'force-static';

// Dynamic (SSR)
export const dynamic = 'force-dynamic';

// Revalidation
export const revalidate = 3600; // Revalidate every hour
```

---

## State Management Patterns

### URL State (Recommended for Filters/Pagination)
```typescript
// Next.js App Router
'use client';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

function FilterPanel() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set(key, value);
    router.push(`${pathname}?${params.toString()}`);
  };
  
  return (
    <select onChange={(e) => updateFilter('category', e.target.value)}>
      <option value="all">All</option>
      <option value="electronics">Electronics</option>
    </select>
  );
}
```

### Server State (React Query / SWR)
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

function UserProfile({ userId }: { userId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
    staleTime: 5 * 60 * 1000, // Consider fresh for 5 minutes
  });
  
  if (isLoading) return <Skeleton />;
  return <div>{data.name}</div>;
}

function UpdateProfileButton() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
  
  return <button onClick={() => mutation.mutate(newData)}>Update</button>;
}
```

---

## List Virtualization

### For Long Lists (>100 items)
```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50, // Estimated row height
  });
  
  return (
    <div ref={parentRef} style={{ height: 400, overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: virtualRow.start,
              height: virtualRow.size,
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Image Optimization

### Next.js Image
```typescript
import Image from 'next/image';

function ProductImage({ src, alt }: { src: string; alt: string }) {
  return (
    <Image
      src={src}
      alt={alt}
      width={400}
      height={300}
      placeholder="blur"
      blurDataURL={generateBlurDataURL()}
      priority={false} // Set true for above-fold images
    />
  );
}
```

### Generic React (with srcset)
```typescript
function ResponsiveImage({ src, alt }: { src: string; alt: string }) {
  return (
    <img
      src={src}
      alt={alt}
      srcSet={`
        ${src}?w=400 400w,
        ${src}?w=800 800w,
        ${src}?w=1200 1200w
      `}
      sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px"
      loading="lazy"
      decoding="async"
      width={400}
      height={300}
    />
  );
}
```
