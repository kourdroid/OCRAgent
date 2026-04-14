# Human-in-the-Loop Interrupts (Python)

## TOC
- Agent Inbox interrupts (HumanInterrupt)
- Handling responses

## Agent Inbox Interrupts

Canonical snippet (Context7: `/langchain-ai/langgraph/1.0.6`, `libs/prebuilt/README.md`):

```python
from langgraph.types import interrupt
from langgraph.prebuilt.interrupt import HumanInterrupt, HumanResponse


def my_graph_function():
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    if response["type"] == "response":
        ...
```

## Handling Responses

- Treat interrupts like an external boundary: validate and sanitize any human-provided fields before updating state.
- Keep interrupt payloads minimal and explicit (action, args, description).
