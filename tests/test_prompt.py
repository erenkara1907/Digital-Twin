import pytest

from twin.prompt import DATA_FILES, build_system_prompt


@pytest.fixture
def data_dir(tmp_path):
    for name in DATA_FILES:
        (tmp_path / name).write_text(f"CONTENT-OF-{name}", encoding="utf-8")
    return tmp_path


def test_prompt_includes_every_data_file(data_dir):
    prompt = build_system_prompt(data_dir)

    for name in DATA_FILES:
        assert f"CONTENT-OF-{name}" in prompt


def test_prompt_states_the_five_rules(data_dir):
    prompt = build_system_prompt(data_dir)

    assert "Eren Kara" in prompt
    assert "record_unknown_question" in prompt
    assert "record_contact" in prompt
    assert "language" in prompt


def test_data_comes_after_rules(data_dir):
    prompt = build_system_prompt(data_dir)

    assert prompt.index("record_contact") < prompt.index("CONTENT-OF-profile.md")


def test_missing_file_raises_with_file_name(tmp_path):
    (tmp_path / "profile.md").write_text("x", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="projects.md"):
        build_system_prompt(tmp_path)
