from agent.deep_agent import (
    HUMAN_APPROVAL_REQUIRED_TOOLS,
    REQUIRED_TOOL_NAMES,
    SUBAGENTS,
    build_agent_config,
    tool_names,
)


def test_required_tools_are_registered():
    assert tool_names() == REQUIRED_TOOL_NAMES


def test_no_raw_sql_tool_registered():
    names = tool_names()

    assert "run_sql" not in names
    assert "query_sql" not in names
    assert "execute_sql" not in names


def test_get_as_of_otb_requires_human_approval():
    assert "get_as_of_otb" in HUMAN_APPROVAL_REQUIRED_TOOLS


def test_subagents_include_segment_or_block_specialist():
    assert "segment_mix_analyst" in SUBAGENTS
    assert "block_mix_analyst" in SUBAGENTS


def test_agent_config_has_memory_skills_and_prompt():
    config = build_agent_config()

    assert config["memory"]["enabled"] is True
    assert "skills" in config["skills_dir"]
    assert "Never invent numbers" in config["system_prompt"]
    assert "human_approval_required_tools" in config