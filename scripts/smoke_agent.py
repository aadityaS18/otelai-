from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.deep_agent import build_agent_config


def main():
    config = build_agent_config()

    print("System prompt loaded:", bool(config["system_prompt"]))
    print("Skills dir:", config["skills_dir"])

    print("\nTools:")
    for tool in config["tools"]:
        print("-", tool.__name__)

    print("\nSubagents:")
    for name, subagent in config["subagents"].items():
        print("-", name, "=>", subagent["description"])

    print("\nHuman approval required tools:")
    for tool_name in config["human_approval_required_tools"]:
        print("-", tool_name)

    print("\nMemory enabled:", config["memory"]["enabled"])


if __name__ == "__main__":
    main()