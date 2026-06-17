from pathlib import Path
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from agent.deep_agent import build_agent_config


def get_message_content(message) -> str:
    content = getattr(message, "content", None)

    if isinstance(content, list):
        return "\n".join(
            part.get("text", str(part)) if isinstance(part, dict) else str(part)
            for part in content
        )

    return content or str(message)


def print_tool_activity(result: dict, previous_message_count: int) -> None:
    messages = result.get("messages", [])
    new_messages = messages[previous_message_count:]

    print("\n--- Tool Trace ---")

    found_tool_activity = False

    for msg in new_messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            found_tool_activity = True
            for call in tool_calls:
                print(f"Tool called: {call.get('name')} args={call.get('args')}")

        msg_type = getattr(msg, "type", "")
        name = getattr(msg, "name", None)

        if msg_type == "tool":
          found_tool_activity = True
          print(f"Tool result from: {name}")
          print(f"Tool output: {get_message_content(msg)}")

    if not found_tool_activity:
        print("No tool call detected for this turn.")

    print("--- End Tool Trace ---")


def needs_as_of_approval(question: str) -> bool:
    q = question.lower()
    return "as of" in q or "as-of" in q or "point in time" in q


def main():
    config = build_agent_config()

    llm = ChatOllama(
        model="qwen2.5:3b",
        temperature=0,
    )

    agent = create_react_agent(
        model=llm,
        tools=config["tools"],
        checkpointer=MemorySaver(),
        prompt=config["system_prompt"],
    )

    thread_id = f"ollama-demo-{uuid.uuid4()}"
    previous_message_count = 0

    print("Revenue Manager LangGraph Agent using Ollama")
    print("Ask a question, or type 'exit'.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Agent: Done.")
            break

        if needs_as_of_approval(question):
            approval = input(
                "This question may use the point-in-time OTB tool. Approve? (yes/no): "
            ).strip().lower()

            if approval not in {"yes", "y"}:
                print("Agent: Approval denied. I will not run the as-of OTB tool.\n")
                continue

        result = agent.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        )

        print_tool_activity(result, previous_message_count)

        previous_message_count = len(result.get("messages", []))

        final_message = result["messages"][-1]

        print("\nAgent:")
        print(get_message_content(final_message))
        print()


if __name__ == "__main__":
    main()