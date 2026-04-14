# Tools and ReAct Agents (Python)

## TOC
- create_react_agent (prebuilt)
- ToolNode in a custom StateGraph
- Tools that update graph state (Command + ToolMessage)

## create_react_agent (Prebuilt)

Canonical snippet (Context7: `/langchain-ai/langgraph/1.0.6`, `libs/prebuilt/README.md`):

```python
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent


def search(query: str):
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


tools = [search]
model = ChatAnthropic(model="claude-3-7-sonnet-latest")

app = create_react_agent(model, tools)
app.invoke({"messages": [{"role": "user", "content": "what is the weather in sf"}]})
```

## ToolNode in a Custom Graph

When you need a bespoke state schema and explicit control over routing, combine a `StateGraph` with a `ToolNode` (see LangGraph docs for your version).

## Tools That Update Graph State

Canonical snippet (Context7: `/websites/langchain_oss_python_langgraph`, `use-graph-api`):

Return `Command(update=...)` to update state from a tool; update `messages` with a `ToolMessage` for valid history.

```python
from typing import Annotated
from langgraph.graph.core import RunnableConfig
from langgraph.graph.types import Command, ToolMessage


def lookup_user_info(tool_call_id: str, config: RunnableConfig):
    user_id = (config.get("configurable") or {}).get("user_id")
    user_info = {"user_id": user_id}
    return Command(
        update={
            "user_info": user_info,
            "messages": [ToolMessage("Successfully looked up user information", tool_call_id=tool_call_id)],
        }
    )
```
