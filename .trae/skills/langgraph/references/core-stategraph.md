# Core StateGraph Patterns (Python)

## TOC
- Minimal graph (TypedDict + START + compile/invoke)
- Node return contract

## Minimal Graph

Canonical example (Context7: `/langchain-ai/langgraph/1.0.6`, `libs/langgraph/README.md`):

```python
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict


class State(TypedDict):
    text: str


def node_a(state: State) -> dict:
    return {"text": state["text"] + "a"}


def node_b(state: State) -> dict:
    return {"text": state["text"] + "b"}


graph = StateGraph(State)
graph.add_node("node_a", node_a)
graph.add_node("node_b", node_b)
graph.add_edge(START, "node_a")
graph.add_edge("node_a", "node_b")

result = graph.compile().invoke({"text": ""})
print(result)  # {"text": "ab"}
```

## Node Return Contract

- Return a partial state update: `dict[str, Any]` with only keys you intend to modify.
- Keep nodes small and single-purpose; treat I/O boundaries as explicit steps.
