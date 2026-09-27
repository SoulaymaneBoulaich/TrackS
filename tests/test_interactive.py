import os
import tempfile
import pytest

from goal_tracker.database import Database
from goal_tracker.models import GoalStatus
from goal_tracker.agent_shell import GoalAgentShell


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = Database(db_path=db_path)
    yield db
    
    try:
        os.remove(db_path)
    except OSError:
        pass


def test_update_goal(temp_db):
    goal = temp_db.add_goal("Old Title", "Old Criteria")
    updated = temp_db.update_goal(goal.id, title="New Title", target_criteria="New SMART Criteria")
    
    assert updated is not None
    assert updated.title == "New Title"
    assert updated.target_criteria == "New SMART Criteria"

    fetched = temp_db.get_goal(goal.id)
    assert fetched.title == "New Title"


def test_delete_goal(temp_db):
    goal = temp_db.add_goal("To be deleted", "Some criteria")
    assert temp_db.get_goal(goal.id) is not None

    deleted = temp_db.delete_goal(goal.id)
    assert deleted is True
    assert temp_db.get_goal(goal.id) is None


def test_delete_penalty_and_clear_history(temp_db):
    # Record two dummy penalties
    p1 = temp_db.record_penalty(1, "Goal 1", "2026-09", 250, 1, "Roast 1", "Task 1")
    p2 = temp_db.record_penalty(2, "Goal 2", "2026-09", 250, 1, "Roast 2", "Task 2")

    all_pens = temp_db.get_all_penalties()
    assert len(all_pens) == 2

    # Delete single penalty
    deleted = temp_db.delete_penalty(p1.id)
    assert deleted is True
    assert len(temp_db.get_all_penalties()) == 1

    # Clear entire penalty history
    count = temp_db.clear_penalty_history()
    assert count == 1
    assert len(temp_db.get_all_penalties()) == 0


def test_agent_shell_methods(temp_db, capsys):
    shell = GoalAgentShell(db=temp_db)
    
    # Test dashboard rendering does not crash
    shell.show_dashboard()
    captured = capsys.readouterr()
    assert "TrackS" in captured.out or "ACCOUNTABILITY" in captured.out

    # Test menu display
    shell.show_menu()
    captured_menu = capsys.readouterr()
    assert "COMMAND MATRIX" in captured_menu.out or "COMMAND" in captured_menu.out
