import os
import pytest
from blinsky.skills import SkillManager

@pytest.fixture
def temp_skills():
    test_file = "data/test_skills.json"
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    if os.path.exists(test_file):
        os.remove(test_file)
    manager = SkillManager()
    manager._path = test_file
    yield manager
    if os.path.exists(test_file):
        os.remove(test_file)

def test_skills_crud(temp_skills):
    # Learn
    temp_skills.learn("test_skill", "test content")
    assert temp_skills.get("test_skill") == "test content"

    # List
    skills = temp_skills.list_skills()
    assert len(skills) == 1
    assert skills[0]["name"] == "test_skill"

    # Forget
    existed = temp_skills.forget("test_skill")
    assert existed is True
    assert temp_skills.get("test_skill") is None

    # Inject Context
    temp_skills.learn("skill1", "content1")
    ctx = temp_skills.inject_context()
    assert "skill1: content1" in ctx
