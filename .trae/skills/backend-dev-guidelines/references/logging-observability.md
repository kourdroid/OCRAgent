# Logging and Observability Reference

## Structured Logging

### Logger Setup (TypeScript)
```typescript
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  base: {
    service: process.env.SERVICE_NAME || 'api',
    env: process.env.NODE_ENV || 'development',
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

// Create child logger with context
export function createLogger(context: Record<string, unknown>) {
  return logger.child(context);
}

// Usage
const requestLogger = createLogger({ requestId: req.id, userId: user.id });
requestLogger.info('Processing request');
```

---

## Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| **fatal** | App is crashing | Database connection lost, can't recover |
| **error** | Operation failed, needs attention | Payment failed, user data not saved |
| **warn** | Potential issue, degraded service | Cache miss rate high, retrying operation |
| **info** | Business events, state changes | User registered, order placed, job started |
| **debug** | Development context | SQL queries, request details, variable values |
| **trace** | Very detailed, rarely used | Function entry/exit, loop iterations |

---

## What to Log

### ✅ LOG: Request Boundaries
```typescript
// Request start
logger.info('Incoming request', {
  method: req.method,
  path: req.path,
  query: req.query,
  requestId: req.id,
  userAgent: req.headers['user-agent'],
  ip: req.ip,
});

// Request end
logger.info('Request completed', {
  requestId: req.id,
  statusCode: res.statusCode,
  durationMs: Date.now() - startTime,
});
```

### ✅ LOG: Business Events
```typescript
logger.info('Order created', {
  orderId: order.id,
  userId: order.userId,
  itemCount: order.items.length,
  totalAmount: order.total,
});

logger.info('Payment processed', {
  orderId: order.id,
  paymentId: payment.id,
  provider: payment.provider,
  status: payment.status,
});
```

### ✅ LOG: Errors with Context
```typescript
logger.error('Payment failed', {
  orderId: order.id,
  userId: order.userId,
  provider: 'stripe',
  errorCode: error.code,
  errorMessage: error.message,
  stack: error.stack,
});
```

### ✅ LOG: External Service Calls
```typescript
const start = Date.now();
try {
  const response = await externalApi.call(params);
  logger.info('External API call succeeded', {
    service: 'inventory',
    endpoint: '/check-stock',
    durationMs: Date.now() - start,
    statusCode: response.status,
  });
} catch (error) {
  logger.error('External API call failed', {
    service: 'inventory',
    endpoint: '/check-stock',
    durationMs: Date.now() - start,
    error: error.message,
  });
}
```

### ❌ DON'T LOG: Sensitive Data
```typescript
// NEVER DO THIS
logger.info('User created', {
  email: user.email,
  password: user.password,     // ❌ NEVER
  creditCard: user.cardNumber, // ❌ NEVER
  ssn: user.socialSecurity,    // ❌ NEVER
});

// Mask sensitive data
logger.info('User created', {
  email: maskEmail(user.email), // jo***@example.com
  hasCard: !!user.cardNumber,   // true/false only
});
```

---

## Request ID Propagation

### Middleware
```typescript
import { randomUUID } from 'crypto';
import { AsyncLocalStorage } from 'async_hooks';

// Store for request context
export const requestContext = new AsyncLocalStorage<{ requestId: string }>();

// Middleware
export function requestIdMiddleware(req: Request, res: Response, next: NextFunction) {
  const requestId = req.headers['x-request-id'] as string || randomUUID();
  req.id = requestId;
  res.setHeader('x-request-id', requestId);
  
  requestContext.run({ requestId }, () => next());
}

// Access anywhere in the request
function getCurrentRequestId(): string | undefined {
  return requestContext.getStore()?.requestId;
}
```

---

## Metrics

### Key Metrics to Track

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `db_query_duration_seconds` | Histogram | Database query latency |
| `external_api_requests_total` | Counter | External API calls by service, status |
| `queue_jobs_total` | Counter | Background jobs by type, status |
| `queue_job_duration_seconds` | Histogram | Job processing time |

### RED Method
- **R**ate: Requests per second
- **E**rrors: Error rate (errors/requests)
- **D**uration: Latency percentiles (p50, p95, p99)

### USE Method (for resources)
- **U**tilization: How busy is the resource?
- **S**aturation: How much work is queued?
- **E**rrors: Error rate

---

## Tracing

### OpenTelemetry Setup
```typescript
import { trace, SpanKind, SpanStatusCode } from '@opentelemetry/api';

const tracer = trace.getTracer('my-service');

async function processOrder(orderId: string) {
  return tracer.startActiveSpan('processOrder', {
    kind: SpanKind.INTERNAL,
    attributes: { 'order.id': orderId },
  }, async (span) => {
    try {
      const order = await getOrder(orderId);
      span.setAttributes({ 'order.total': order.total });
      
      await tracer.startActiveSpan('processPayment', async (paymentSpan) => {
        try {
          await processPayment(order);
        } finally {
          paymentSpan.end();
        }
      });
      
      span.setStatus({ code: SpanStatusCode.OK });
      return order;
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

---

## Health Checks

```typescript
// GET /health
export async function healthCheck() {
  const checks = await Promise.allSettled([
    checkDatabase(),
    checkRedis(),
    checkExternalApi(),
  ]);
  
  const results = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    checks: {
      database: checks[0].status === 'fulfilled' ? 'up' : 'down',
      redis: checks[1].status === 'fulfilled' ? 'up' : 'down',
      externalApi: checks[2].status === 'fulfilled' ? 'up' : 'down',
    },
  };
  
  const isHealthy = Object.values(results.checks).every(v => v === 'up');
  results.status = isHealthy ? 'healthy' : 'unhealthy';
  
  return { status: isHealthy ? 200 : 503, body: results };
}
```
