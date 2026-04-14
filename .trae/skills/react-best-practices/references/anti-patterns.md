# Component Anti-Patterns Reference

## Render Cascade Issues

### Problem: Inline Objects
```typescript
// ❌ BAD: New object reference every render
function Parent() {
  return <Child style={{ color: 'red' }} />;
}

// ✅ GOOD: Stable reference
const redStyle = { color: 'red' };
function Parent() {
  return <Child style={redStyle} />;
}

// ✅ GOOD: If dynamic, use useMemo
function Parent({ color }: { color: string }) {
  const style = useMemo(() => ({ color }), [color]);
  return <Child style={style} />;
}
```

### Problem: Inline Callbacks
```typescript
// ❌ BAD: New function every render
function List({ items }: { items: Item[] }) {
  return items.map(item => (
    <Item 
      key={item.id} 
      onClick={() => selectItem(item.id)}  // New ref!
    />
  ));
}

// ✅ GOOD: Move handler to child
function List({ items }: { items: Item[] }) {
  return items.map(item => (
    <Item 
      key={item.id} 
      item={item}
      onSelect={selectItem}
    />
  ));
}

function Item({ item, onSelect }) {
  const handleClick = useCallback(() => {
    onSelect(item.id);
  }, [item.id, onSelect]);
  
  return <button onClick={handleClick}>{item.name}</button>;
}
```

### Problem: Array Index as Key
```typescript
// ❌ BAD: Breaks reconciliation on reorder
items.map((item, index) => <Item key={index} {...item} />)

// ✅ GOOD: Stable unique ID
items.map(item => <Item key={item.id} {...item} />)
```

---

## State Anti-Patterns

### Problem: Derived State in useState
```typescript
// ❌ BAD: Duplicate source of truth
function FilteredList({ items, filter }) {
  const [filteredItems, setFilteredItems] = useState(
    items.filter(i => i.includes(filter))
  );
  
  useEffect(() => {
    setFilteredItems(items.filter(i => i.includes(filter)));
  }, [items, filter]);
  
  return <List items={filteredItems} />;
}

// ✅ GOOD: Compute during render
function FilteredList({ items, filter }) {
  const filteredItems = useMemo(
    () => items.filter(i => i.includes(filter)),
    [items, filter]
  );
  
  return <List items={filteredItems} />;
}
```

### Problem: useEffect for Transformation
```typescript
// ❌ BAD: Extra render cycle
function UserProfile({ user }) {
  const [fullName, setFullName] = useState('');
  
  useEffect(() => {
    setFullName(`${user.firstName} ${user.lastName}`);
  }, [user]);
  
  return <h1>{fullName}</h1>;
}

// ✅ GOOD: Just compute it
function UserProfile({ user }) {
  const fullName = `${user.firstName} ${user.lastName}`;
  return <h1>{fullName}</h1>;
}
```

---

## Context Anti-Patterns

### Problem: Single Giant Context
```typescript
// ❌ BAD: Any change re-renders all consumers
const AppContext = createContext({
  user: null,
  theme: 'light',
  cart: [],
  notifications: [],
  // ... 20 more pieces of state
});

// ✅ GOOD: Split by update frequency
const UserContext = createContext(null);
const ThemeContext = createContext('light');
const CartContext = createContext([]);
```

### Problem: Object Value in Provider
```typescript
// ❌ BAD: New object every render
function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

// ✅ GOOD: Memoize the value
function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const value = useMemo(() => ({ user, setUser }), [user]);
  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}
```

---

## Hook Anti-Patterns

### Problem: Missing Dependencies
```typescript
// ❌ BAD: Stale closure
function Chat({ roomId }) {
  const [messages, setMessages] = useState([]);
  
  useEffect(() => {
    const unsubscribe = subscribe(roomId, (msg) => {
      setMessages([...messages, msg]); // `messages` is stale!
    });
    return unsubscribe;
  }, [roomId]); // Missing `messages`
}

// ✅ GOOD: Use updater function
useEffect(() => {
  const unsubscribe = subscribe(roomId, (msg) => {
    setMessages(prev => [...prev, msg]);
  });
  return unsubscribe;
}, [roomId]);
```

### Problem: Unnecessary useEffect
```typescript
// ❌ BAD: Effect for props sync
function Child({ value, onChange }) {
  useEffect(() => {
    onChange(transformValue(value));
  }, [value, onChange]);
}

// ✅ GOOD: Transform in parent
function Parent() {
  const transformedValue = transformValue(value);
  return <Child value={transformedValue} />;
}
```

---

## Prop Drilling Solutions

### Pattern: Component Composition
```typescript
// ❌ BAD: Drilling through 5 levels
<Level1 user={user}>
  <Level2 user={user}>
    <Level3 user={user}>
      <Level4 user={user}>
        <UserAvatar user={user} />

// ✅ GOOD: Pass component as prop
function Layout({ header }) {
  return <div>{header}</div>;
}

<Layout header={<UserAvatar user={user} />} />
```

### Pattern: Render Props / Children
```typescript
function AuthGuard({ children }) {
  const { user } = useAuth();
  if (!user) return <LoginPrompt />;
  return typeof children === 'function' ? children(user) : children;
}

// Usage
<AuthGuard>
  {(user) => <Dashboard user={user} />}
</AuthGuard>
```
