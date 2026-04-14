## Goal
Create a new Trae Skill named `langgraph` that teaches and operationalizes LangGraph (Python) patterns: typed state, graph construction, routing, tools, memory/checkpointing, streaming, and human-in-the-loop—grounded in Context7 docs.

## Docs Baseline (Context7)
- Use these Context7 sources as canonical for examples/APIs:
  - `/langchain-ai/langgraph/1.0.6` (StateGraph basics, prebuilt ReAct agent, interrupts, checkpoint savers)
  - `/websites/langchain_oss_python_langgraph` (Command/goto/update, add_conditional_edges, add_messages, streaming, memory with PostgresSaver)

## Files To Create
Create a new skill folder at:
- `.trae/skills/langgraph/`

### 1) `SKILL.md`
- Frontmatter:
  - `name: langgraph`
  - `description:` include strong triggers like “build agent workflows as graphs”, “StateGraph”, “routing/conditional edges”, “checkpointing/memory”, “streaming”, “human-in-the-loop interrupts”, “ToolNode/create_react_agent”.
- Body sections (concise but complete, patterned after existing skills):
  - **Announce at start**: user-visible protocol.
  - **Bundled Resources** table with “Load When”.
  - **Quick Start**: minimal `StateGraph` + `TypedDict` example (from Context7).
  - **Core Contracts**:
    - Node signatures: `state -> dict` updates OR `state -> Command` (routing + updates).
    - State typing: `TypedDict`, and message state using `Annotated[list[BaseMessage], add_messages]` / `MessagesState`.
  - **Routing Patterns**:
    - `add_conditional_edges` pattern.
    - `Command(goto=..., update=...)` pattern (from Context7).
  - **Tools / Agents**:
    - `ToolNode` and `create_react_agent` entrypoints.
    - Tool-returned `Command(update=...)` with `ToolMessage` for history correctness.
  - **Memory & Durability**:
    - Checkpointers: `InMemorySaver`, `PostgresSaver`, `AsyncPostgresSaver`.
    - Thread-scoped config: `configurable.thread_id`.
    - Defensive notes: DB down, retries, safe fallbacks (no silent corruption).
  - **Streaming**:
    - `graph.stream(..., stream_mode="updates"|"values"|"custom")` and `graph.astream`.
    - Custom streaming via `get_stream_writer()` and `StreamWriter` fallback for Python < 3.11 (from Context7).
    - Subgraph streaming via `subgraphs=True`.
  - **Human-in-the-loop**:
    - `interrupt([...])` and Agent Inbox `HumanInterrupt` request/response shape (from Context7).
  - **Defensive Engineering Checklist**:
    - Validate external inputs before writing to state.
    - Use explicit timeouts for LLM/tools/DB.
    - Keep nodes single-purpose; avoid global exception swallowing; log context.
  - **Testing Guidance**:
    - Golden-state tests for nodes.
    - Deterministic routing tests.
    - Checkpointer integration tests using InMemorySaver.

### 2) Reference Files (keeps SKILL.md lean)
Create:
- `references/core-stategraph.md` (StateGraph/START/END/compile/invoke patterns)
- `references/messages-and-reducers.md` (`MessagesState`, `add_messages`, message update rules)
- `references/routing-and-command.md` (`add_conditional_edges`, `Command(goto/update)` examples)
- `references/tools-and-react-agent.md` (`ToolNode`, `create_react_agent`, tool-returned `Command`)
- `references/memory-and-checkpointing.md` (`InMemorySaver`, `PostgresSaver`, `AsyncPostgresSaver`, `thread_id`)
- `references/streaming.md` (stream modes, custom writer, subgraph streaming)
- `references/hitl-interrupts.md` (`interrupt`, `HumanInterrupt` shapes)

Each reference file:
- Starts with a short TOC
- Contains only the minimum examples + key gotchas (all sourced from Context7 snippets above)

### 3) Optional Scripts (deterministic scaffolding)
Create (only if useful after drafting the docs):
- `scripts/generate_stategraph_skeleton.py`
  - Prints a minimal, typed LangGraph skeleton to stdout (no project assumptions).
  - Parameters: `--with-messages`, `--with-routing`, `--with-checkpointer`.

## Validation / Packaging
- Run quick validation:
  - `python .trae/skills/skill-creator/scripts/quick_validate.py .trae/skills/langgraph`
- Package:
  - `python .trae/skills/skill-creator/scripts/package_skill.py .trae/skills/langgraph .trae/skills/dist`

## Acceptance Criteria
- Skill triggers reliably on LangGraph-related requests.
- SKILL.md stays under ~500 lines; deeper details live in references.
- All examples compile conceptually and match Context7 docs.
- Packaged `.skill` artifact is produced successfully via the existing packaging tooling.