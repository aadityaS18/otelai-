from pathlib import Path


SKILLS_DIR = Path("skills")


def read(path):
    return path.read_text().lower()


def test_at_least_six_skills_exist():
    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    assert len(skill_files) >= 6


def test_challenge_skill_pack_version_exists():
    text = read(SKILLS_DIR / "CHALLENGE_SKILL.md")
    assert "otel-rm-v2" in text


def test_at_least_three_skills_encode_judgment():
    judgment_words = ["threshold", "recommended action", "risk", "protect rate"]
    count = 0

    for skill_file in SKILLS_DIR.glob("*/SKILL.md"):
        text = read(skill_file)
        if any(word in text for word in judgment_words):
            count += 1

    assert count >= 3


def test_ota_dependency_has_numeric_thresholds_and_action():
    text = read(SKILLS_DIR / "ota_dependency" / "SKILL.md")

    assert "25%" in text
    assert "40%" in text
    assert "55%" in text
    assert "recommended actions" in text
    assert "get_segment_mix" in text


def test_pickup_skill_mentions_create_datetime_and_london_utc():
    text = read(SKILLS_DIR / "pickup_pace" / "SKILL.md")

    assert "get_pickup_delta" in text
    assert "create_datetime" in text
    assert "europe/london" in text
    assert "utc" in text


def test_segment_skill_uses_effective_macro_group():
    text = read(SKILLS_DIR / "segment_mix" / "SKILL.md")

    assert "get_segment_mix" in text
    assert "effective_macro_group" in text
    assert "raw sql" not in text or "do not use raw sql" in text