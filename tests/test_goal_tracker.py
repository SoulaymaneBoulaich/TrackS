import os
import tempfile
import pytest
from datetime import datetime

from goal_tracker.database import Database
from goal_tracker.models import GoalStatus
from goal_tracker.judge import GoalJudge
from goal_tracker.scheduler import MonthlyScheduler
from goal_tracker.roaster import generate_roast_and_penalty, PENALTY_TASKS_BY_TIER


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = Database(db_path=db_path)
    yield db
    
    # Cleanup
    try:
        os.remove(db_path)
    except OSError:
        pass


def test_database_init_and_profile(temp_db):
    profile = temp_db.get_profile()
    assert profile.username == "Commander"
    assert profile.xp == 1000
    assert profile.level == 1
    assert profile.strikes == 0
    assert profile.max_strikes == 3


def test_add_and_get_goal(temp_db):
    goal = temp_db.add_goal(
        title="Ship SaaS Landing Page",
        target_criteria="Deploy responsive Next.js landing page with Stripe checkout live on Vercel.",
        month="2026-10"
    )
    assert goal.id is not None
    assert goal.title == "Ship SaaS Landing Page"
    assert goal.month == "2026-10"
    assert goal.status == GoalStatus.PENDING

    retrieved = temp_db.get_goal(goal.id)
    assert retrieved is not None
    assert retrieved.title == goal.title


def test_submit_evidence(temp_db):
    goal = temp_db.add_goal("Run 50km this month", "Log 50km total on Strava")
    evidence_text = "Completed 52km logged across 8 runs on Strava profile https://strava.com/athletes/12345"
    updated_goal = temp_db.submit_evidence(goal.id, evidence_text)
    
    assert updated_goal.status == GoalStatus.EVIDENCE_SUBMITTED
    assert updated_goal.evidence == evidence_text
    assert updated_goal.evidence_submitted_at is not None


def test_judge_evaluation_pass(temp_db):
    judge = GoalJudge(temp_db)
    goal = temp_db.add_goal("Write Technical Whitepaper", "Complete 40-page PDF on distributed consensus")
    evidence = (
        "Finished full whitepaper draft on 2026-10-15 with 42 pages and 12,000 words. "
        "Artifact published at https://github.com/org/consensus-whitepaper/releases/tag/v1.0 "
        "Reviewed by 3 external peer researchers with 100% sign-off."
    )
    temp_db.submit_evidence(goal.id, evidence)
    
    goal_to_eval = temp_db.get_goal(goal.id)
    decision = judge.evaluate_evidence(goal_to_eval, current_strikes=0)

    assert decision.passed is True
    assert decision.score >= 70
    assert decision.xp_delta > 0
    assert decision.strike_delta == 0
    assert decision.assigned_penalty is None
    assert decision.roast is None


def test_judge_evaluation_fail_no_evidence(temp_db):
    judge = GoalJudge(temp_db)
    goal = temp_db.add_goal("Read 3 Books", "Finish 3 non-fiction books")
    
    goal_to_eval = temp_db.get_goal(goal.id)
    decision = judge.evaluate_evidence(goal_to_eval, current_strikes=0)

    assert decision.passed is False
    assert decision.score == 0
    assert decision.xp_delta == -250
    assert decision.strike_delta == 1
    assert decision.assigned_penalty is not None
    assert decision.roast is not None
    assert "NO EVIDENCE" in decision.roast


def test_judge_evaluation_fail_excuses(temp_db):
    judge = GoalJudge(temp_db)
    goal = temp_db.add_goal("Daily Gym Workout", "Go to gym 20 days in the month")
    excuse_evidence = "I tried really hard, but unfortunately work got super busy and I got sick next month I will do it."
    temp_db.submit_evidence(goal.id, excuse_evidence)

    goal_to_eval = temp_db.get_goal(goal.id)
    decision = judge.evaluate_evidence(goal_to_eval, current_strikes=0)

    assert decision.passed is False
    assert decision.score < 70
    assert decision.xp_delta == -250
    assert decision.strike_delta == 1
    assert "justification/excuse" in decision.feedback.lower()


def test_execute_audit_updates_database(temp_db):
    judge = GoalJudge(temp_db)
    goal = temp_db.add_goal("Run 100 Miles", "Log 100 miles on Nike Run Club")
    
    # Audit with zero evidence to trigger failure and penalty
    decision = judge.execute_audit(goal.id)
    assert decision.passed is False

    # Verify goal record updated
    audited_goal = temp_db.get_goal(goal.id)
    assert audited_goal.status == GoalStatus.FAILED_PENALIZED
    
    # Verify profile updated
    profile = temp_db.get_profile()
    assert profile.xp == 750  # 1000 - 250
    assert profile.strikes == 1

    # Verify penalty ledger
    penalties = temp_db.get_uncleared_penalties()
    assert len(penalties) == 1
    assert penalties[0].goal_id == goal.id
    assert penalties[0].xp_lost == 250
    assert penalties[0].is_cleared is False


def test_penalty_clearing(temp_db):
    judge = GoalJudge(temp_db)
    goal = temp_db.add_goal("Meditate daily", "30 sessions")
    judge.execute_audit(goal.id)

    penalties = temp_db.get_uncleared_penalties()
    assert len(penalties) == 1
    penalty_id = penalties[0].id

    temp_db.clear_penalty(penalty_id)
    uncleared = temp_db.get_uncleared_penalties()
    assert len(uncleared) == 0

    all_penalties = temp_db.get_all_penalties()
    assert len(all_penalties) == 1
    assert all_penalties[0].is_cleared is True
    assert all_penalties[0].cleared_at is not None


def test_monthly_scheduler_rollover(temp_db):
    scheduler = MonthlyScheduler(temp_db)

    # Set profile to an older month
    temp_db.update_profile(xp=1000, strikes=0, current_month="2026-08")
    
    # Add an unfinished goal in the older month
    goal = temp_db.add_goal("Complete Cyber Audit", "Pass ISO27001 prep", month="2026-08")

    # Run rollover check (system date is 2026-09)
    res = scheduler.check_and_process_rollover()
    assert res["rollover_detected"] is True
    assert res["previous_month"] == "2026-08"
    assert len(res["audited_goals"]) == 1
    assert res["penalties_triggered"] == 1

    # Check goal is now marked FAILED_PENALIZED
    updated_goal = temp_db.get_goal(goal.id)
    assert updated_goal.status == GoalStatus.FAILED_PENALIZED

    # Check profile updated to current month and strike added
    profile = temp_db.get_profile()
    assert profile.strikes == 1
    assert profile.xp == 750
    assert profile.last_evaluated_month == "2026-08"


def test_roaster_escalation():
    # 0 strikes -> MEDIUM or LIGHT
    sev0, roast0, task0 = generate_roast_and_penalty("Goal 1", "Criteria", "", strikes=0)
    assert sev0 in ["LIGHT", "MEDIUM"]
    assert task0 in PENALTY_TASKS_BY_TIER[sev0]

    # 1 strike -> SEVERE
    sev1, roast1, task1 = generate_roast_and_penalty("Goal 2", "Criteria", "", strikes=1)
    assert sev1 == "SEVERE"
    assert task1 in PENALTY_TASKS_BY_TIER["SEVERE"]

    # 2+ strikes -> CATASTROPHIC
    sev2, roast2, task2 = generate_roast_and_penalty("Goal 3", "Criteria", "", strikes=2)
    assert sev2 == "CATASTROPHIC"
    assert "CRITICAL WARNING" in roast2
    assert task2 in PENALTY_TASKS_BY_TIER["CATASTROPHIC"]


def test_reset_database(temp_db):
    # Add dummy goals and penalties
    g1 = temp_db.add_goal("Goal to purge", "Proof criteria")
    p1 = temp_db.record_penalty(g1.id, g1.title, "2026-09", 250, 1, "Roast", "Penance")
    temp_db.update_profile(xp=500, strikes=2)

    assert len(temp_db.get_all_goals()) == 1
    assert len(temp_db.get_all_penalties()) == 1
    assert temp_db.get_profile().strikes == 2

    # Execute factory reset
    temp_db.reset_database()

    assert len(temp_db.get_all_goals()) == 0
    assert len(temp_db.get_all_penalties()) == 0
    profile = temp_db.get_profile()
    assert profile.strikes == 0
    assert profile.xp == 1000
    assert profile.level == 1
