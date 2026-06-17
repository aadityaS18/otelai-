from scripts.langgraph_agent_cli import needs_as_of_approval


def test_needs_as_of_approval_for_as_of_question():
    assert needs_as_of_approval("What was July 2026 OTB as of 2026-06-15?") is True


def test_needs_as_of_approval_for_as_of_with_hyphen():
    assert needs_as_of_approval("Show me as-of OTB for July 2026") is True


def test_needs_as_of_approval_for_point_in_time_question():
    assert needs_as_of_approval("Give point in time OTB for July") is True


def test_needs_as_of_approval_false_for_normal_otb():
    assert needs_as_of_approval("What is July 2026 OTB?") is False


def test_needs_as_of_approval_false_for_segment_mix():
    assert needs_as_of_approval("What is our segment mix for July 2026?") is False