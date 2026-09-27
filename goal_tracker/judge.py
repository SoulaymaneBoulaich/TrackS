import re
from typing import Optional
from goal_tracker.models import Goal, GoalStatus, AuditDecision
from goal_tracker.roaster import generate_roast_and_penalty
from goal_tracker.database import Database

class GoalJudge:
    def __init__(self, db: Database):
        self.db = db

    def evaluate_evidence(self, goal: Goal, current_strikes: int) -> AuditDecision:
        """
        Cross-examines evidence against the target criteria.
        Scores evidence on a scale of 0-100.
        """
        evidence = goal.evidence or ""
        criteria = goal.target_criteria.lower()

        if not evidence.strip():
            # Zero evidence provided
            severity, roast, penalty_task = generate_roast_and_penalty(
                goal.title, goal.target_criteria, "NO EVIDENCE SUBMITTED", current_strikes
            )
            return AuditDecision(
                passed=False,
                score=0,
                verdict_summary="FAILED: No evidence was submitted before deadline.",
                feedback="You submitted zero evidence. A goal without proof is a daydream.",
                assigned_penalty=penalty_task,
                roast=roast,
                xp_delta=-250,
                strike_delta=1
            )

        # Quantitative heuristic scoring based on evidence rigor
        score = 50  # Baseline for providing something
        feedback_points = []

        # 1. Evidence length & detail
        words = len(evidence.strip().split())
        if words >= 40:
            score += 15
            feedback_points.append("[+] Thorough written documentation provided.")
        elif words < 10:
            score -= 20
            feedback_points.append("[-] Evidence is suspiciously brief and lacks detail.")

        # 2. Presence of concrete proof artifacts (links, numbers, metrics, dates, file paths)
        has_numbers = bool(re.search(r"\b\d+(\.\d+)?%?\b", evidence))
        has_links = bool(re.search(r"https?://|github\.com|file://|/|\\", evidence, re.I))
        has_dates = bool(re.search(r"\b(202\d|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|day|week)\b", evidence, re.I))

        if has_numbers:
            score += 15
            feedback_points.append("[+] Quantifiable metrics or numbers detected.")
        else:
            score -= 10
            feedback_points.append("[-] No quantifiable metrics or data points identified.")

        if has_links:
            score += 15
            feedback_points.append("[+] External verification link, commit, or file path provided.")

        if has_dates:
            score += 5
            feedback_points.append("[+] Temporal milestones/dates cited.")

        # 3. Check for excuse language vs proof language
        excuse_patterns = [r"\btried\b", r"\balmost\b", r"\bbusy\b", r"\bsick\b", r"\bnext month\b", r"\bunfortunately\b"]
        for ep in excuse_patterns:
            if re.search(ep, evidence, re.I):
                score -= 15
                feedback_points.append(f"[-] Detected justification/excuse vocabulary ('{ep.replace(chr(92)+'b', '')}').")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        passed = score >= 70

        if passed:
            xp_gain = 100 if score < 90 else 150
            return AuditDecision(
                passed=True,
                score=score,
                verdict_summary=f"VERIFIED PASSED (Score: {score}/100)",
                feedback=" ".join(feedback_points) + " Objective verified as completed according to criteria.",
                assigned_penalty=None,
                roast=None,
                xp_delta=xp_gain,
                strike_delta=0
            )
        else:
            severity, roast, penalty_task = generate_roast_and_penalty(
                goal.title, goal.target_criteria, evidence, current_strikes
            )
            return AuditDecision(
                passed=False,
                score=score,
                verdict_summary=f"FAILED AUDIT (Score: {score}/100 - Below 70 threshold)",
                feedback=" ".join(feedback_points) + " Evidence was insufficient or failed to substantiate the target criteria.",
                assigned_penalty=penalty_task,
                roast=roast,
                xp_delta=-250,
                strike_delta=1
            )

    def execute_audit(self, goal_id: int) -> AuditDecision:
        goal = self.db.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal #{goal_id} not found.")

        profile = self.db.get_profile()
        decision = self.evaluate_evidence(goal, profile.strikes)

        # Apply database state updates
        new_xp = max(0, profile.xp + decision.xp_delta)
        new_strikes = min(profile.max_strikes, profile.strikes + decision.strike_delta)

        if decision.passed:
            self.db.update_goal_status(goal_id, GoalStatus.VERIFIED_COMPLETED, decision.feedback, completed=True)
            self.db.update_profile(xp=new_xp, strikes=new_strikes)
        else:
            self.db.update_goal_status(goal_id, GoalStatus.FAILED_PENALIZED, decision.feedback, completed=False)
            self.db.record_penalty(
                goal_id=goal.id,
                goal_title=goal.title,
                month=goal.month,
                xp_lost=abs(decision.xp_delta),
                strike_increment=decision.strike_delta,
                roast=decision.roast,
                penalty_task=decision.assigned_penalty
            )
            self.db.update_profile(xp=new_xp, strikes=new_strikes)

        return decision
