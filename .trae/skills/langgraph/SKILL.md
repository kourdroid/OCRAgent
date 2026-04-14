---
name: langgraph
description: "Use when building or refactoring LangGraph (Python) agent workflows as graphs: StateGraph/START/END, typed state (TypedDict/MessagesState), routing (add_conditional_edges or Command(goto/update)), tools (ToolNode, create_react_agent), memory/checkpointing (InMemorySaver/PostgresSaver, thread_id), streaming (stream/astream, stream_mode, custom stream writer), and human-in-the-loop interrupts."
---

# LangGraph (Python)

**Announce at start:** "I'm using the langgraph skill to implement this LangGraph workflow."

## Bundled Resources

| File | Load When |
|------|-----------|
| `references/core-stategraph.md` | Creating a new graph, START/END wiring, compile/invoke |
| `references/messages-and-reducers.md` | Building chat agents, storing message history, reducers |
| `references/routing-and-command.md` | Conditional routing, routers, Command(goto/update) |
| `references/tools-and-react-agent.md` | ToolNode, ReAct agents, tool-returned state updates |
| `references/memory-and-checkpointing.md` | Persistence, checkpoints, Postgres checkpointers, thread_id |
| `references/streaming.md` | Streaming outputs, custom stream writer, subgraph streaming |
| `references/hitl-interrupts.md` | Human-in-the-loop interrupts and Agent Inbox patterns |
| `scripts/generate_stategraph_skeleton.py` | Generating a minimal typed graph skeleton quickly |

## Quick Start (Minimal StateGraph)

Load `references/core-stategraph.md` for the canonical snippet. The minimum pattern is:
- Define a typed state (`TypedDict`)
- Add nodes
- Connect `START` -> node(s)
- `compile()` then `invoke()`

## Core Contracts (Non-Negotiable)

### State Schema
- Use `typing_extensions.TypedDict` (or `typing.TypedDict`) for the graph state.
- Treat the graph state as the single source of truth: no hidden globals.
- Every node must return only a partial update (a `dict`) for keys it owns.

### Node Interface
A node should be one of:
- `def node(state: State) -> dict`: returns state updates, merged by reducers.
- `def node(state: State) -> Command[...]`: returns `Command(update=..., goto=...)` to update and route in one step.

Load `references/routing-and-command.md` for Command patterns.

### Messages / Chat State
- Prefer `MessagesState` or `messages: Annotated[list[BaseMessage], add_messages]` when building chat agents.
- When updating message history, use the reducer pattern (`add_messages`) so messages append/merge correctly.

Load `references/messages-and-reducers.md` for message formats and gotchas.

## Routing Patterns

Pick one routing style and stick to it inside a graph:
- **Edges + Router:** `add_conditional_edges("node_a", routing_fn, {True: "node_b", False: "node_c"})`
- **Command Routing:** node returns `Command(goto="next_node", update={...})` (preferred when routing depends on computed updates)

Load `references/routing-and-command.md`.

## Tools and ReAct Agents

Preferred patterns:
- Use `langgraph.prebuilt.create_react_agent(model, tools)` for standard ReAct agents.
- Use `ToolNode` when you want explicit tool execution as part of a custom StateGraph.
- If a tool needs to update state, return a `Command(update=...)` and include `ToolMessage` for correct message history.

Load `references/tools-and-react-agent.md`.

## Memory, Checkpointing, and Durability

If the workflow needs continuity across calls (chat memory, long jobs, human-in-the-loop):
- Compile with a checkpointer (`InMemorySaver` for tests/dev, `PostgresSaver`/`AsyncPostgresSaver` for durability).
- Always pass a `config` with `configurable.thread_id` so checkpoints scope correctly.

Load `references/memory-and-checkpointing.md`.

## Streaming

Use streaming for UX, observability, and long-running operations:
- `graph.stream(..., stream_mode="updates"|"values"|"custom")`
- `graph.astream(...)` for async
- Emit custom progress events from inside a node using `get_stream_writer()` (Python >= 3.11), or accept a `StreamWriter` argument (fallback)

Load `references/streaming.md`.

## Human-in-the-Loop (HITL)

Use interrupts when an action must be approved or edited:
- Create a `HumanInterrupt` request object
- Call `interrupt([request])` and branch on the response type

Load `references/hitl-interrupts.md`.

## Defensive Engineering Checklist

- Validate every external input before writing it into state (LLM outputs, tool responses, HTTP/DB responses).
- Add explicit timeouts for all I/O boundaries (LLM call, tool call, DB access).
- Handle partial failures without corrupting state: return no update (or a safe update) when a boundary fails.
- Catch specific exceptions at boundaries; rethrow or return a typed error field in state.
- Never log secrets; log durations and correlation IDs (thread_id).

## Implementation Workflow (Repeatable)

1. Define `State` with only the keys you need, with reducers for list-like keys (especially messages).
2. Write small single-purpose nodes; ensure each node updates only its owned keys.
3. Add edges and routing; prefer `Command` for "compute + route" in one step.
4. Decide on checkpointing; wire a checkpointer and thread_id config if you need durability.
5. Add streaming where user feedback matters; emit custom progress events for long steps.
6. Add tests around node purity, routing determinism, and checkpoint read/write behavior.
