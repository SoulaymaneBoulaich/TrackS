import time
from datetime import datetime
from typing import List, Dict, Any
from goal_tracker.database import Database
from goal_tracker.judge import GoalJudge
from goal_tracker.models import GoalStatus

class MonthlyScheduler:
    def __init__(self, db: Database):
        self.db = db
        self.judge = GoalJudge(db)

    def check_and_process_rollover(self) -> Dict[str, Any]:
        """
        Checks if the calendar month has advanced beyond the profile's current active month.
        If yes, freezes previous month goals and auto-audits any unverified items.
        """
        profile = self.db.get_profile()
        now_month = datetime.now().strftime("%Y-%m")

        results = {
            "rollover_detected": False,
            "previous_month": profile.current_month,
            "new_month": now_month,
            "audited_goals": [],
            "penalties_triggered": 0
        }

        if profile.current_month != now_month:
            results["rollover_detected"] = True
            # Fetch all goals from the past month
            past_goals = self.db.get_goals_by_month(profile.current_month)

            for g in past_goals:
                if g.status in [GoalStatus.PENDING, GoalStatus.EVIDENCE_SUBMITTED]:
                    # Unfinished or unaudited goal past the deadline
                    decision = self.judge.execute_audit(g.id)
                    results["audited_goals"].append({
                        "goal_id": g.id,
                        "title": g.title,
                        "passed": decision.passed,
                        "penalty": decision.assigned_penalty
                    })
                    if not decision.passed:
                        results["penalties_triggered"] += 1

            # Update profile to new active month
            self.db.update_profile(
                xp=self.db.get_profile().xp,
                strikes=self.db.get_profile().strikes,
                current_month=now_month,
                last_evaluated_month=profile.current_month
            )

        return results

    def run_daemon(self, check_interval_seconds: int = 3600):
        """
        Runs continuously in the background, checking for monthly rollover.
        """
        print(f"[*] GoalTracker Monthly Daemon running (Polling every {check_interval_seconds}s)...")
        while True:
            res = self.check_and_process_rollover()
            if res["rollover_detected"]:
                print(f"[!] MONTHLY ROLLOVER PROCESSED from {res['previous_month']} to {res['new_month']}:")
                print(f"    - Goals Audited: {len(res['audited_goals'])}")
                print(f"    - Penalties Triggered: {res['penalties_triggered']}")
            time.sleep(check_interval_seconds)
