# Architecture Patterns Reference

## Hexagonal Architecture (Ports & Adapters)

### Core Principle
Business logic is isolated in the center. All external concerns connect via ports (interfaces) and adapters (implementations).

### Structure
```
src/
├── domain/              # THE CENTER - Pure business logic
│   ├── entities/        # Business objects (User, Order, Product)
│   ├── services/        # Business rules
│   ├── value-objects/   # Immutable values (Money, Email, Address)
│   └── ports/           # Interface definitions
│       ├── inbound/     # Use case interfaces
│       └── outbound/    # Repository/external service interfaces
│
├── application/         # USE CASES - Orchestration layer
│   ├── commands/        # Write operations
│   ├── queries/         # Read operations
│   └── handlers/        # Command/query handlers
│
├── adapters/            # THE OUTSIDE - Infrastructure implementations
│   ├── inbound/         # Entry points
│   │   ├── rest/        # HTTP controllers
│   │   ├── graphql/     # GraphQL resolvers
│   │   └── grpc/        # gRPC services
│   │
│   └── outbound/        # External dependencies
│       ├── database/    # Repository implementations
│       ├── cache/       # Cache implementations
│       ├── messaging/   # Queue implementations
│       └── http/        # External API clients
│
└── config/              # Wiring and configuration
    └── di.ts            # Dependency injection setup
```

### The Dependency Rule
**All dependencies point inward.** Domain knows nothing about adapters.

```typescript
// ✅ CORRECT: Domain defines interface
// domain/ports/outbound/user-repository.ts
interface UserRepository {
  findById(id: UserId): Promise<User | null>;
  save(user: User): Promise<void>;
}

// ✅ CORRECT: Adapter implements interface
// adapters/outbound/database/postgres-user-repository.ts
class PostgresUserRepository implements UserRepository {
  async findById(id: UserId): Promise<User | null> {
    const row = await this.db.query('SELECT * FROM users WHERE id = $1', [id]);
    return row ? UserMapper.toDomain(row) : null;
  }
}
```

---

## CQRS (Command Query Responsibility Segregation)

### When to Use
- Read/write ratio > 10:1
- Different scaling needs for reads vs writes
- Complex querying requirements
- Event-driven architecture already in place

### Structure
```
Commands (Write)              Queries (Read)
     │                             │
     ▼                             ▼
┌─────────────┐            ┌─────────────┐
│ Write Model │            │ Read Model  │
│ (Normalized)│───Events──▶│(Denormalized│
│ PostgreSQL  │            │ Elasticsearch│
└─────────────┘            └─────────────┘
```

### Implementation Pattern
```typescript
// Command side
interface CreateOrderCommand {
  userId: string;
  items: OrderItem[];
}

class CreateOrderHandler {
  async execute(cmd: CreateOrderCommand): Promise<OrderId> {
    const order = Order.create(cmd.userId, cmd.items);
    await this.orderRepository.save(order);
    await this.eventBus.publish(order.domainEvents);
    return order.id;
  }
}

// Query side (separate model, separate database)
interface OrderSummaryQuery {
  userId: string;
  limit: number;
}

class OrderSummaryHandler {
  async execute(query: OrderSummaryQuery): Promise<OrderSummary[]> {
    // Reads from denormalized read model
    return this.readDb.orderSummaries.findByUserId(query.userId, query.limit);
  }
}
```

---

## Event Sourcing

### Core Concept
Store events, not state. Derive current state by replaying events.

### Event Store Pattern
```typescript
// Events are immutable facts
interface OrderCreated {
  type: 'OrderCreated';
  orderId: string;
  userId: string;
  items: OrderItem[];
  timestamp: Date;
}

interface PaymentReceived {
  type: 'PaymentReceived';
  orderId: string;
  amount: Money;
  paymentMethod: string;
  timestamp: Date;
}

interface OrderShipped {
  type: 'OrderShipped';
  orderId: string;
  carrier: string;
  trackingNumber: string;
  timestamp: Date;
}

type OrderEvent = OrderCreated | PaymentReceived | OrderShipped;

// Rebuild state from events
function rebuildOrder(events: OrderEvent[]): Order {
  return events.reduce((order, event) => {
    switch (event.type) {
      case 'OrderCreated':
        return Order.create(event);
      case 'PaymentReceived':
        return order.applyPayment(event);
      case 'OrderShipped':
        return order.markShipped(event);
    }
  }, Order.empty());
}
```

### Benefits
- Complete audit trail
- Time-travel debugging
- Rebuild projections from history
- Event replay for new features

### Challenges
- Schema evolution
- Event versioning
- Snapshot optimization for performance

---

## Strangler Fig Pattern

### Migration Strategy
```
Phase 1: Intercept       Phase 2: Migrate        Phase 3: Complete
┌───────────┐           ┌───────────┐           ┌───────────┐
│   Proxy   │           │   Proxy   │           │   Proxy   │
└─────┬─────┘           └─────┬─────┘           └─────┬─────┘
      │                       │                       │
      ▼                       ▼                       ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Monolith   │    →    │  Monolith   │    →    │ New Service │
│  (100%)     │         │   (60%)     │         │   (100%)    │
└─────────────┘         └──────┬──────┘         └─────────────┘
                              │
                        ┌─────▼─────┐
                        │New Service│
                        │  (40%)    │
                        └───────────┘
```

### Implementation Checklist
1. **Put proxy in front** of monolith (API Gateway, nginx, Envoy)
2. **Pick ONE endpoint** to migrate first
3. **Shadow traffic** to new service (compare responses)
4. **Canary deploy** (1% → 10% → 50% → 100%)
5. **Verify** metrics match or improve
6. **Repeat** for next endpoint
7. **Decommission** empty monolith

---

## Saga Pattern (Distributed Transactions)

### Choreography (Event-Based)
```
Order Service ──OrderCreated──▶ Payment Service
                                      │
                              PaymentCompleted
                                      │
                                      ▼
                               Inventory Service
                                      │
                              InventoryReserved
                                      │
                                      ▼
                               Shipping Service
```

### Orchestration (Command-Based)
```
                    ┌─────────────┐
                    │ Saga        │
                    │ Orchestrator│
                    └─────┬───────┘
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ Payment  │    │ Inventory│    │ Shipping │
   │ Service  │    │ Service  │    │ Service  │
   └──────────┘    └──────────┘    └──────────┘
```

### Compensation
For each step, define a compensating action:
| Step | Action | Compensation |
|------|--------|--------------|
| 1 | Reserve payment | Release payment hold |
| 2 | Reserve inventory | Return items to stock |
| 3 | Schedule shipping | Cancel shipment |
