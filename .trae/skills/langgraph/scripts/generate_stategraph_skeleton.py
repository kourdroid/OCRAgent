from __future__ import annotations

import argparse


def _build_code(with_messages: bool, with_routing: bool, with_checkpointer: bool) -> str:
    if with_messages:
        state_imports = "\n".join(
            [
                "from typing import Annotated",
                "from langgraph.graph.message import add_messages",
                "from langchain_core.messages import BaseMessage",
            ]
        )
        state_body = "    messages: Annotated[list[BaseMessage], add_messages]"
        initial_state = '{"messages": [{"role": "user", "content": "hello"}]}'
    else:
        state_imports = ""
        state_body = "    text: str"
        initial_state = '{"text": ""}'

    routing_imports = "from typing_extensions import Literal" if with_routing else ""
    routing_types = " -> Command[Literal[\"node_b\", \"node_c\"]]" if with_routing else " -> dict"
    routing_return = (
        "\n".join(
            [
                "    value = \"b\"",
                "    goto = \"node_b\" if value == \"b\" else \"node_c\"",
                "    return Command(update={\"text\": value}, goto=goto)",
            ]
        )
        if with_routing
        else "    return {\"text\": state[\"text\"] + \"a\"}"
    )

    checkpointer_import = "from langgraph.checkpoint.memory import InMemorySaver" if with_checkpointer else ""
    compile_line = "graph = builder.compile(checkpointer=InMemorySaver())" if with_checkpointer else "graph = builder.compile()"

    blocks = [
        "from typing_extensions import TypedDict",
        "from langgraph.graph import START, StateGraph",
        "from langgraph.types import Command" if with_routing else "",
        routing_imports,
        state_imports,
        checkpointer_import,
        "",
        "",
        "class State(TypedDict):",
        state_body,
        "",
        "",
        f"def node_a(state: State){routing_types}:",
        routing_return,
        "",
        "",
        "def node_b(state: State) -> dict:",
        "    return {\"text\": state.get(\"text\", \"\") + \"b\"}",
        "",
        "",
        "def node_c(state: State) -> dict:",
        "    return {\"text\": state.get(\"text\", \"\") + \"c\"}",
        "",
        "",
        "builder = StateGraph(State)",
        "builder.add_node(\"node_a\", node_a)",
        "builder.add_node(\"node_b\", node_b)",
        "builder.add_node(\"node_c\", node_c)",
        "builder.add_edge(START, \"node_a\")",
        "builder.add_edge(\"node_a\", \"node_b\")" if not with_routing else "",
        "",
        compile_line,
        "",
        "",
        "if __name__ == \"__main__\":",
        f"    result = graph.invoke({initial_state})",
        "    print(result)",
    ]

    return "\n".join([b for b in blocks if b != ""])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-messages", action="store_true")
    parser.add_argument("--with-routing", action="store_true")
    parser.add_argument("--with-checkpointer", action="store_true")
    args = parser.parse_args()

    print(_build_code(args.with_messages, args.with_routing, args.with_checkpointer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
