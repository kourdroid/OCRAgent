# Memory and Checkpointing (Python)

## TOC
- In-memory checkpointer (tests/dev)
- Postgres checkpointer (durable memory)
- AsyncPostgresSaver
- Thread scoping via configurable.thread_id

## InMemorySaver (Tests/Dev)

Canonical snippet (Context7: `/langchain-ai/langgraph/1.0.6`, `libs/checkpoint/README.md`):

```python
from langgraph.checkpoint.memory import InMemorySaver

write_config = {"configurable": {"thread_id": "1", "checkpoint_ns": ""}}
read_config = {"configurable": {"thread_id": "1"}}

checkpointer = InMemorySaver()
checkpoint = {
    "v": 4,
    "ts": "2024-07-31T20:14:19.804150+00:00",
    "id": "1ef4f797-8335-6428-8001-8a1503f9b875",
    "channel_values": {"my_key": "meow", "node": "node"},
    "channel_versions": {"__start__": 2, "my_key": 3, "start:node": 3, "node": 3},
    "versions_seen": {"__input__": {}, "__start__": {"__start__": 1}, "node": {"start:node": 2}},
}

checkpointer.put(write_config, checkpoint, {}, {})
checkpointer.get(read_config)
list(checkpointer.list(read_config))
```

## PostgresSaver (Durable Memory)

Canonical snippet (Context7: `/websites/langchain_oss_python_langgraph`, `add-memory`):

```python
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.postgres import PostgresSaver

model = init_chat_model(model="claude-haiku-4-5-20251001")

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    def call_model(state: MessagesState):
        response = model.invoke(state["messages"])
        return {"messages": response}

    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_edge(START, "call_model")

    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "1"}}

    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
        config,
        stream_mode="values",
    ):
        chunk["messages"][-1].pretty_print()
```

## AsyncPostgresSaver

Canonical snippet (Context7: `/langchain-ai/langgraph/1.0.6`, `libs/checkpoint-postgres/README.md`):

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    await checkpointer.aput(write_config, checkpoint, {}, {})
    await checkpointer.aget(read_config)
    [c async for c in checkpointer.alist(read_config)]
```

## Defensive Notes

- Treat the checkpointer as an I/O boundary: DB down must not corrupt state.
- Use configuration (env vars) for DB URIs; never hardcode credentials in production code.
