from pathlib import Path

from tools.revenue_tools import (
    get_as_of_otb,
    get_block_vs_transient_mix,
    get_otb_summary,
    get_pickup_delta,
    get_segment_mix,
)

def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


SYSTEM_PROMPT_PATH = Path(__file__).with_name("system_prompt.md")
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

REVENUE_TOOLS = [
    get_otb_summary,
    get_segment_mix,
    get_pickup_delta,
    get_as_of_otb,
    get_block_vs_transient_mix,
]

REQUIRED_TOOL_NAMES = {
    "get_otb_summary",
    "get_segment_mix",
    "get_pickup_delta",
    "get_as_of_otb",
    "get_block_vs_transient_mix",
}

HUMAN_APPROVAL_REQUIRED_TOOLS = {"get_as_of_otb"}

SUBAGENTS = {
    "segment_mix_analyst": {
        "description": "Specialist for segment, OTA dependency, and macro-group mix questions.",
        "tools": ["get_segment_mix"],
        "skills": ["segment_mix", "ota_dependency"],
    },
    "block_mix_analyst": {
        "description": "Specialist for block versus transient and company concentration questions.",
        "tools": ["get_block_vs_transient_mix"],
        "skills": ["block_mix"],
    },
    "pickup_pace_analyst": {
        "description": "Specialist for recent pickup and booking pace questions.",
        "tools": ["get_pickup_delta"],
        "skills": ["pickup_pace"],
    },
}


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text()


def tool_names() -> set[str]:
    return {tool.__name__ for tool in REVENUE_TOOLS}


def build_agent_config() -> dict:
    """
    Returns the Deep Agents configuration surface without making an LLM API call.

    The deployed app will pass these tools, skills, subagents, memory/filesystem,
    and HITL settings into create_deep_agent.
    """
    return {
        "system_prompt": load_system_prompt(),
        "tools": REVENUE_TOOLS,
        "skills_dir": str(SKILLS_DIR),
        "subagents": SUBAGENTS,
        "human_approval_required_tools": HUMAN_APPROVAL_REQUIRED_TOOLS,
        "memory": {
            "enabled": True,
            "purpose": "Persist multi-turn GM context and prior assumptions.",
        },
    }