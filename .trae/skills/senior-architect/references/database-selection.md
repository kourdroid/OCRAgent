# Database Selection Guide

## Decision Matrix

| Factor | Question | Trade-off |
|--------|----------|-----------|
| **Consistency** | Must reads see latest writes? | Strong → Lower availability |
| **Availability** | Can we tolerate downtime? | High → Eventual consistency |
| **Partition Tolerance** | Network splits happen? | Always assume yes |
| **Latency** | P99 requirements? | Low → More infrastructure cost |
| **Throughput** | Writes/second needed? | High → Consider LSM-trees |

## Access Pattern Decision Tree

```
WHAT IS YOUR PRIMARY ACCESS PATTERN?
         │
         ├─── Relational Joins, ACID Transactions
         │    └─► PostgreSQL, MySQL, CockroachDB
         │
         ├─── Key-Value Lookups (simple, fast)
         │    └─► Redis, DynamoDB, Memcached
         │
         ├─── Graph Relationships (friends-of-friends, recommendations)
         │    └─► Neo4j, Dgraph, Amazon Neptune
         │
         ├─── Full-Text Search
         │    └─► Elasticsearch, Meilisearch, Typesense
         │
         ├─── Time-Series Data (metrics, logs, IoT)
         │    └─► TimescaleDB, InfluxDB, QuestDB
         │
         ├─── Document Storage (flexible schema)
         │    └─► MongoDB, CouchDB (only if truly schema-less)
         │
         └─── Wide-Column (massive scale, sparse data)
              └─► Cassandra, ScyllaDB, HBase
```

## PostgreSQL vs Others

### When PostgreSQL is the Answer (90% of cases)
- You need ACID transactions
- Your data is relational
- You need full-text search (built-in)
- You need JSON support (JSONB)
- You need geospatial (PostGIS)
- Team knows SQL

### When PostgreSQL is NOT the Answer
| Scenario | Better Choice | Why |
|----------|--------------|-----|
| Sub-millisecond latency | Redis | In-memory, no disk |
| 100k+ writes/second | Cassandra/ScyllaDB | LSM-tree optimized |
| Graph traversals 5+ levels | Neo4j | Native graph engine |
| Horizontal scale required | CockroachDB | Distributed PostgreSQL |

## B-Trees vs LSM-Trees

### B-Trees (PostgreSQL, MySQL)
- **Optimized for**: Reads
- **Write performance**: Slower (in-place updates)
- **Read performance**: Faster (single lookup)
- **Use when**: Read-heavy workloads, OLTP

### LSM-Trees (Cassandra, RocksDB, LevelDB)
- **Optimized for**: Writes
- **Write performance**: Faster (append-only)
- **Read performance**: Slower (multiple levels to check)
- **Use when**: Write-heavy workloads, time-series, logs

## CAP Theorem Quick Reference

```
                CONSISTENCY
                    /\
                   /  \
                  /    \
                 /  CA  \
                /________\
               /\        /\
              /  \      /  \
             / CP \    / AP \
            /______\  /______\
    PARTITION       AVAILABILITY
    TOLERANCE
```

- **CP (Consistent + Partition Tolerant)**: MongoDB, HBase, Redis Cluster
- **AP (Available + Partition Tolerant)**: Cassandra, CouchDB, DynamoDB
- **CA (Consistent + Available)**: Traditional RDBMS (but no partition tolerance)

## Consistency Models

| Model | Guarantee | Use Case |
|-------|-----------|----------|
| **Strong** | Reads always see latest write | Financial transactions |
| **Eventual** | Reads eventually see write | Social media feeds |
| **Causal** | Related operations ordered | Chat applications |
| **Read-your-writes** | User sees own writes immediately | Profile updates |

## Replication Strategies

### Single-Leader (Master-Slave)
- Writes go to leader, replicated to followers
- Good for read-heavy workloads
- Failover complexity

### Multi-Leader
- Multiple nodes accept writes
- Conflict resolution required
- Good for multi-datacenter

### Leaderless
- Any node accepts reads/writes
- Quorum-based consistency
- No single point of failure
