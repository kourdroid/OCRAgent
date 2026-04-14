# Streaming (Python)

## TOC
- Basic streaming
- Custom streaming from inside nodes
- Async custom streaming (Python < 3.11 fallback)
- Streaming from subgraphs

## Basic Streaming

Canonical snippet (Context7: `/websites/langchain_oss_python_langgraph`, `streaming`):

```python
for chunk in graph.stream(inputs, stream_mode="updates"):
    print(chunk)
```

Common `stream_mode` values shown in docs include:
- `updates`: incremental updates to state
- `values`: full state values at steps
- `custom`: user-emitted payloads

## Custom Streaming From Inside Nodes

Canonical snippet (Context7: `/websites/langchain_oss_python_langgraph`, `streaming`):

```python
from typing import TypedDict
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START


class State(TypedDict):
    query: str
    answer: str


def node(state: State):
    writer = get_stream_writer()
    writer({"custom_key": "Generating custom data inside node"})
    return {"answer": "some data"}


graph = (
    StateGraph(State)
    .add_node(node)
    .add_edge(START, "node")
    .compile()
)

for chunk in graph.stream({"query": "example"}, stream_mode="custom"):
    print(chunk)
```

## Async Custom Streaming (Python < 3.11 Fallback)

Canonical snippet (Context7: `/websites/langchain_oss_python_langgraph`, `streaming`):

```python
from typing import TypedDict
from langgraph.types import StreamWriter


class State(TypedDict):
    topic: str
    joke: str


async def generate_joke(state: State, writer: StreamWriter):
    writer({"custom_key": "Streaming custom data while generating a joke"})
    return {"joke": f"This is a joke about {state['topic']}"}
```

## Streaming From Subgraphs

Canonical snippet (Context7: `/websites/langchain_oss_python_langgraph`, `streaming`):

```python
for chunk in graph.stream(
    {"foo": "foo"},
    stream_mode="updates",
    subgraphs=True,
):
    print(chunk)
```
