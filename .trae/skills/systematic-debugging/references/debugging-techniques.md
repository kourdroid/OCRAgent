# Debugging Techniques Reference

## Binary Search for Bugs

### Git Bisect Workflow
```bash
# Start bisect
git bisect start

# Mark current commit as bad
git bisect bad HEAD

# Mark known good commit
git bisect good abc123

# Git checks out middle commit
# Test if bug exists, then:
git bisect good  # or
git bisect bad

# Repeat until found
# Git announces: "abc123 is the first bad commit"

# Return to original state
git bisect reset
```

### Binary Search in Code
```python
# Isolate bug in N function calls
# Instead of stepping through all 100 lines:

def debug_binary_search():
    # Does bug occur in first half?
    result_1 = step_1_to_50()
    check_invariant()  # Bug here? → Focus on steps 1-50
    
    result_2 = step_51_to_100()
    check_invariant()  # Bug here? → Focus on steps 51-100
```

---

## Logging for Debugging

### Strategic Log Placement
```typescript
async function processOrder(order: Order) {
  logger.info('Processing order', { orderId: order.id, items: order.items.length });
  
  try {
    const validated = validateOrder(order);
    logger.debug('Order validated', { orderId: order.id });
    
    const payment = await processPayment(validated);
    logger.info('Payment processed', { orderId: order.id, paymentId: payment.id });
    
    const shipped = await scheduleShipping(validated);
    logger.info('Order complete', { orderId: order.id, trackingId: shipped.trackingId });
    
    return shipped;
  } catch (error) {
    logger.error('Order processing failed', {
      orderId: order.id,
      error: error.message,
      stack: error.stack,
      step: getCurrentStep(),
    });
    throw error;
  }
}
```

### State Snapshots
```typescript
function debugSnapshot(label: string, state: unknown) {
  if (process.env.DEBUG === 'true') {
    console.log(`[DEBUG ${label}]`, JSON.stringify(state, null, 2));
    // Or write to file for large objects
    fs.writeFileSync(`debug-${label}-${Date.now()}.json`, JSON.stringify(state));
  }
}
```

---

## Debugger Techniques

### Conditional Breakpoints
```
// VS Code: Right-click breakpoint → Edit Breakpoint
// Condition: userId === 'abc123'
// Hit Count: 5 (break on 5th hit)
// Log Message: User {userId} at step {step} (no break, just log)
```

### Watch Expressions
```
// Add to Watch panel:
this.state
Object.keys(data)
data.items?.length ?? 0
error?.message || 'No error'
```

### Call Stack Navigation
1. Set breakpoint at error location
2. When hit, examine call stack
3. Click frames to see each caller's context
4. Identify where incorrect data originates

---

## Isolation Techniques

### Simplify Inputs
```typescript
// Original failing case
const result = process(complexObject);

// Simplify until it works
const minimal = {
  id: complexObject.id,
  // Add properties one by one until bug appears
};
const result = process(minimal);
```

### Comment Out Code
```typescript
function suspectFunction(data) {
  const step1 = doStep1(data);
  // const step2 = doStep2(step1);  // Comment out
  // const step3 = doStep3(step2);  // Comment out
  // return step3;
  return step1;  // Return early
}
// If bug disappears, it's in step2 or step3
```

### Fresh Environment
```bash
# Clear all caches
rm -rf node_modules .next .cache
npm ci  # Clean install

# Test in incognito (no extensions)
# Test with production build
npm run build && npm run start
```

---

## Race Condition Detection

### Symptoms
- Works sometimes, fails sometimes
- Works locally, fails in CI
- Works with console.log, fails without
- Works slowly, fails when fast

### Diagnosis
```typescript
// Add delays to expose race conditions
async function debugRace() {
  const result1 = await fetch('/api/1');
  console.log('Result 1:', result1);
  
  await new Promise(r => setTimeout(r, 100));  // Add delay
  
  const result2 = await fetch('/api/2');
  console.log('Result 2:', result2);
}

// Or use Promise.race to detect which resolves first
const [winner, loser] = await Promise.race([
  operationA().then(r => ['A', r]),
  operationB().then(r => ['B', r]),
]);
console.log('Winner:', winner);
```

---

## Memory Leak Detection

### Browser DevTools
1. Open DevTools → Memory tab
2. Take heap snapshot
3. Perform suspected action
4. Take another snapshot
5. Compare: Objects created vs destroyed

### Node.js
```bash
# Start with heap dump on SIGUSR2
node --heapsnapshot-signal=SIGUSR2 app.js

# Trigger dump
kill -USR2 <pid>

# Analyze .heapsnapshot file in Chrome DevTools
```

### Common Causes
| Leak Type | Cause | Fix |
|-----------|-------|-----|
| Event listeners | Not removed | `removeEventListener` in cleanup |
| Intervals | Not cleared | `clearInterval` in cleanup |
| Closures | References to large objects | Null out references |
| React refs | Component never unmounts | Check for memory on unmount |

---

## Network Debugging

### Browser DevTools Network Tab
- Filter by XHR, Fetch, WS
- Check Headers, Response, Timing
- Throttle to simulate slow network
- Block requests to test fallbacks

### cURL for API Testing
```bash
# Basic GET
curl -v https://api.example.com/users

# POST with JSON
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}'

# With auth
curl -H "Authorization: Bearer <token>" \
  https://api.example.com/protected

# Save response
curl -o response.json https://api.example.com/data
```

---

## Environment Comparison

### Checklist When Bug is Environment-Specific
| Factor | Check |
|--------|-------|
| Node version | `node --version` |
| Package versions | `npm list` |
| Environment variables | `printenv | grep APP_` |
| Database state | Compare row counts |
| Cache state | Clear and retry |
| Time/timezone | `date` and TZ env |
| Locale | `LANG` and `LC_ALL` |
