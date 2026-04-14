# Error Handling Patterns Reference

## Error Hierarchy

### Base Error Class (TypeScript)
```typescript
export class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500,
    public readonly isOperational: boolean = true,
    public readonly context?: Record<string, unknown>
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
  
  toJSON() {
    return {
      error: {
        code: this.code,
        message: this.message,
        ...(process.env.NODE_ENV === 'development' && { stack: this.stack }),
      },
    };
  }
}
```

### Specific Error Types
```typescript
// Client errors (4xx)
export class ValidationError extends AppError {
  constructor(
    message: string,
    public readonly fields: Record<string, string>
  ) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} not found: ${id}`, 'NOT_FOUND', 404);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required') {
    super(message, 'UNAUTHORIZED', 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message = 'Insufficient permissions') {
    super(message, 'FORBIDDEN', 403);
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 'CONFLICT', 409);
  }
}

export class RateLimitError extends AppError {
  constructor(retryAfter: number) {
    super('Too many requests', 'RATE_LIMITED', 429, true, { retryAfter });
  }
}

// Server errors (5xx)
export class InternalError extends AppError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'INTERNAL_ERROR', 500, false, context);
  }
}

export class ServiceUnavailableError extends AppError {
  constructor(service: string) {
    super(`Service unavailable: ${service}`, 'SERVICE_UNAVAILABLE', 503);
  }
}
```

---

## Error Boundary Pattern

### Express/Koa Middleware
```typescript
// Global error handler middleware
export function errorHandler(
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
) {
  // Log all errors
  logger.error('Request error', {
    error: error.message,
    stack: error.stack,
    path: req.path,
    method: req.method,
    requestId: req.id,
  });
  
  // Handle known errors
  if (error instanceof AppError && error.isOperational) {
    return res.status(error.statusCode).json(error.toJSON());
  }
  
  // Handle validation errors from Zod
  if (error instanceof z.ZodError) {
    return res.status(400).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid request data',
        fields: error.flatten().fieldErrors,
      },
    });
  }
  
  // Unknown error - don't leak details
  return res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
    },
  });
}
```

### Next.js API Route
```typescript
// lib/api-handler.ts
type Handler = (req: NextRequest) => Promise<NextResponse>;

export function withErrorHandling(handler: Handler): Handler {
  return async (req: NextRequest) => {
    try {
      return await handler(req);
    } catch (error) {
      logger.error('API error', { error, path: req.url });
      
      if (error instanceof AppError && error.isOperational) {
        return NextResponse.json(error.toJSON(), { status: error.statusCode });
      }
      
      return NextResponse.json(
        { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' } },
        { status: 500 }
      );
    }
  };
}

// Usage
export const GET = withErrorHandling(async (req) => {
  const user = await getUser(req.params.id);
  return NextResponse.json(user);
});
```

---

## Result Pattern (No Exceptions)

### Result Type
```typescript
type Result<T, E = Error> = 
  | { success: true; data: T }
  | { success: false; error: E };

// Constructors
const ok = <T>(data: T): Result<T, never> => ({ success: true, data });
const err = <E>(error: E): Result<never, E> => ({ success: false, error });

// Usage
async function getUser(id: string): Promise<Result<User, NotFoundError>> {
  const user = await db.user.findUnique({ where: { id } });
  if (!user) {
    return err(new NotFoundError('User', id));
  }
  return ok(user);
}

// Handling
const result = await getUser('123');
if (!result.success) {
  // TypeScript knows result.error is NotFoundError
  console.log(result.error.message);
  return;
}
// TypeScript knows result.data is User
console.log(result.data.name);
```

---

## Try-Catch Guidelines

### ✅ DO: Catch Specific Errors
```typescript
try {
  await sendEmail(to, subject, body);
} catch (error) {
  if (error instanceof EmailDeliveryError) {
    logger.warn('Email delivery failed, queuing for retry', { to, error });
    await queue.add('retry-email', { to, subject, body });
    return;
  }
  if (error instanceof InvalidEmailError) {
    throw new ValidationError('Invalid email address', { email: 'Invalid format' });
  }
  // Unknown error - rethrow
  throw error;
}
```

### ❌ DON'T: Swallow Errors
```typescript
// NEVER DO THIS
try {
  await riskyOperation();
} catch (e) {
  // Silent failure - impossible to debug
}

// NEVER DO THIS EITHER
try {
  await riskyOperation();
} catch (e) {
  return null;  // Hides error, returns bad data
}
```

### ❌ DON'T: Catch and Log Only
```typescript
// BAD: Error is logged but still propagates incorrectly
try {
  await riskyOperation();
} catch (e) {
  console.error(e);
  throw e;  // Pointless - let error boundary handle logging
}
```

---

## Error Context Wrapping

```typescript
// Add context when rethrowing
async function processOrder(orderId: string) {
  try {
    const order = await getOrder(orderId);
    const payment = await processPayment(order);
    return payment;
  } catch (error) {
    // Wrap with context
    throw new InternalError('Failed to process order', {
      orderId,
      originalError: error instanceof Error ? error.message : 'Unknown',
      step: 'payment',
    });
  }
}
```

---

## Retry Patterns

### Exponential Backoff
```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    baseDelay?: number;
    maxDelay?: number;
    retryOn?: (error: Error) => boolean;
  } = {}
): Promise<T> {
  const {
    maxRetries = 3,
    baseDelay = 100,
    maxDelay = 10000,
    retryOn = () => true,
  } = options;
  
  let lastError: Error;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      if (attempt === maxRetries || !retryOn(lastError)) {
        throw lastError;
      }
      
      const delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  
  throw lastError!;
}

// Usage
const result = await withRetry(
  () => fetch('https://api.example.com/data'),
  {
    maxRetries: 3,
    retryOn: (error) => error instanceof NetworkError,
  }
);
```
