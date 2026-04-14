# Messages and Reducers (Python)

## TOC
- Message state with reducers
- MessagesState
- Update rules and gotchas

## Message State With Reducers

Canonical guidance (Context7: `/websites/langchain_oss_python_langgraph`, `graph-api`):

Use a reducer on the `messages` key so updates append/merge correctly (including ID-based replacement):

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

Supported update shape:

```python
{"messages": [{"role": "user", "content": "hello"}]}
```

## MessagesState

If you don't need any additional keys beyond `messages`, use `MessagesState` as the graph state type (Context7: `/websites/langchain_oss_python_langgraph`, `add-memory`).

## Gotchas

- When tools update message history, ensure the update is a valid message type (e.g., `ToolMessage`) rather than raw strings.
- Don't hand-roll message list concatenation; let the reducer manage it.
