# Routing and Command (Python)

## TOC
- Conditional edges (router function)
- Command-based routing (goto + update)
- Choosing between them

## Conditional Edges

Canonical API (Context7: `/websites/langchain_oss_python_langgraph`, `graph-api`):

```python
graph.add_conditional_edges("node_a", routing_function)
```

With an explicit mapping:

```python
graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})
```

## Command-Based Routing

Canonical API (Context7: `/websites/langchain_oss_python_langgraph`, `use-graph-api`):

```python
from typing_extensions import Literal
from langgraph.types import Command


def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        update={"foo": "bar"},
        goto="my_other_node",
    )
```

End-to-end pattern (Context7: `/websites/langchain_oss_python_langgraph`, `use-graph-api`):

```python
import random
from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START
from langgraph.types import Command


class State(TypedDict):
    foo: str


def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    value = random.choice(["b", "c"])
    goto = "node_b" if value == "b" else "node_c"
    return Command(update={"foo": value}, goto=goto)
```

## Choosing Between Them

- Prefer `add_conditional_edges` when routing depends only on current state and you want explicit edge maps.
- Prefer `Command` when you need "compute update + decide next node" as one atomic operation.
