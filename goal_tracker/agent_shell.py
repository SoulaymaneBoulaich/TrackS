import sys
import re
from datetime import datetime
from typing import Optional

# Windows terminal UTF-8 encoding support
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

from goal_tracker.database import Database
from goal_tracker.models import GoalStatus
from goal_tracker.judge import GoalJudge
from goal_tracker.scheduler import MonthlyScheduler
from goal_tracker.theme import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_SLATE,
    COLOR_DARK_SLATE,
    COLOR_WHITE,
    COLOR_MUTED,
    BOX_STYLE,
    BOX_HEAVY,
    format_status_badge,
    format_strike_gauge,
    render_cycle_progress
)

console = Console(legacy_windows=False)


class GoalAgentShell:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.judge = GoalJudge(self.db)
        self.scheduler = MonthlyScheduler(self.db)

    def print_agent_greeting(self):
        profile = self.db.get_profile()
        goals = self.db.get_goals_by_month(profile.current_month)

        if profile.strikes >= 3:
            avatar = f"[bold {COLOR_DANGER}][SYSTEM STATUS: CODE RED - DISCIPLINE BANKRUPTCY][/bold {COLOR_DANGER}]"
            comment = (
                "Discipline covenant breached with 3 strikes. "
                "Accountability freeze active. Clear all outstanding penances immediately."
            )
        elif profile.strikes == 2:
            avatar = f"[bold {COLOR_WARNING}][SYSTEM STATUS: CODE ORANGE - MAXIMUM SCRUTINY][/bold {COLOR_WARNING}]"
            comment = (
                "One missed milestone from terminal lockout. "
                "Every justification will be cross-examined without leniency."
            )
        elif profile.strikes == 1:
            avatar = f"[bold {COLOR_PRIMARY}][SYSTEM STATUS: PROBATIONARY WATCH][/bold {COLOR_PRIMARY}]"
            comment = "1 strike recorded. Milestone recovery required this cycle."
        else:
            avatar = f"[bold {COLOR_SUCCESS}][SYSTEM STATUS: NOMINAL - STANDARDS ENFORCED][/bold {COLOR_SUCCESS}]"
            comment = "Cycle standing clean. Ensure all commitments are substantiated with objective proof."

        gauge = format_strike_gauge(profile.strikes, profile.max_strikes)
        progress_bar = render_cycle_progress(profile.current_month, goals)

        panel_content = (
            f"{avatar}\n"
            f"[{COLOR_SLATE}]\"{comment}\"[/{COLOR_SLATE}]\n\n"
            f"[{COLOR_DARK_SLATE}]----------------------------------------------------------------------[/{COLOR_DARK_SLATE}]\n"
            f"[bold {COLOR_WHITE}]OPERATOR:[/bold {COLOR_WHITE}] [bold {COLOR_PRIMARY}]{profile.username}[/bold {COLOR_PRIMARY}]  |  "
            f"[bold {COLOR_WHITE}]XP:[/bold {COLOR_WHITE}] [bold {COLOR_WARNING}]{profile.xp:,}[/bold {COLOR_WARNING}]  |  "
            f"[bold {COLOR_WHITE}]TIER:[/bold {COLOR_WHITE}] [bold {COLOR_SECONDARY}]LEVEL {profile.level}[/bold {COLOR_SECONDARY}]  |  "
            f"[bold {COLOR_WHITE}]STRIKES:[/bold {COLOR_WHITE}] {gauge}\n"
            f"[{COLOR_DARK_SLATE}]----------------------------------------------------------------------[/{COLOR_DARK_SLATE}]\n"
            f"{progress_bar}"
        )
        console.print(Panel(
            panel_content,
            title=f"[bold {COLOR_PRIMARY}]TrackS :: ACCOUNTABILITY ENGINE [v1.0.0][/bold {COLOR_PRIMARY}]",
            border_style=COLOR_DARK_SLATE,
            box=BOX_STYLE
        ))

    def show_dashboard(self):
        profile = self.db.get_profile()
        goals = self.db.get_goals_by_month(profile.current_month)
        uncleared_penalties = self.db.get_uncleared_penalties()

        self.print_agent_greeting()

        # Goals Table
        if not goals:
            console.print(
                f"\n[{COLOR_MUTED}]No commitments recorded for active cycle {profile.current_month}. "
                f"Enter '2' or 'add' to commit to a milestone.[/{COLOR_MUTED}]\n"
            )
        else:
            table = Table(
                title=f"COMMITMENTS LEDGER :: CYCLE {profile.current_month}",
                box=BOX_STYLE,
                border_style=COLOR_DARK_SLATE,
                header_style=f"bold {COLOR_PRIMARY}",
                title_style=f"bold {COLOR_WHITE}"
            )
            table.add_column("ID", style=f"bold {COLOR_WHITE}", width=5, justify="center")
            table.add_column("Goal Title", style=f"bold {COLOR_WHITE}", width=28)
            table.add_column("Target Criteria", style=COLOR_SLATE, width=35)
            table.add_column("Status", width=16, justify="center")
            table.add_column("Submitted Proof", style=f"italic {COLOR_PRIMARY}", width=22)

            for g in goals:
                status_str = format_status_badge(g.status)
                ev_summary = (
                    (g.evidence[:18] + "...")
                    if g.evidence and len(g.evidence) > 20
                    else (g.evidence or f"[{COLOR_MUTED}]None[/{COLOR_MUTED}]")
                )
                table.add_row(str(g.id), g.title, g.target_criteria, status_str, ev_summary)

            console.print(table)

        # Uncleared Penances
        if uncleared_penalties:
            console.print(f"\n[bold {COLOR_DANGER}][!] OUTSTANDING PENANCE OBLIGATIONS:[/bold {COLOR_DANGER}]")
            for p in uncleared_penalties:
                pen_text = (
                    f"[bold {COLOR_DANGER}]PENALTY #{p.id} :: BREACH OF COMMITMENT '{p.goal_title}' ({p.month})[/bold {COLOR_DANGER}]\n"
                    f"[{COLOR_WARNING}]Consequence:[/{COLOR_WARNING}] -{p.xp_lost} XP | Strikes Added: +{p.strike_increment}\n\n"
                    f"[bold {COLOR_WHITE}]Assigned Penance Protocol:[/bold {COLOR_WHITE}]\n"
                    f"  >> [bold underline {COLOR_WARNING}]{p.penalty_task}[/bold underline {COLOR_WARNING}]\n\n"
                    f"[{COLOR_MUTED}]Execute the penance, then enter '7' or 'clear-penalty {p.id}' to confirm.[/{COLOR_MUTED}]"
                )
                console.print(Panel(pen_text, border_style=COLOR_DANGER, box=BOX_HEAVY))

    def show_menu(self):
        menu = (
            f"[bold {COLOR_PRIMARY}]COMMAND MATRIX:[/bold {COLOR_PRIMARY}]\n"
            f"  [bold {COLOR_PRIMARY}][ 1][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]dashboard[/bold {COLOR_WHITE}]      [{COLOR_MUTED}]-- Refresh active cycle status & progress[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 2][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]add[/bold {COLOR_WHITE}]            [{COLOR_MUTED}]-- Register a new SMART commitment milestone[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 3][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]update[/bold {COLOR_WHITE}]         [{COLOR_MUTED}]-- Modify goal title or verification criteria[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 4][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]delete[/bold {COLOR_WHITE}]         [{COLOR_MUTED}]-- Remove an existing commitment record[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 5][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]submit[/bold {COLOR_WHITE}]         [{COLOR_MUTED}]-- Submit artifacts, metrics, and proof links[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 6][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]audit[/bold {COLOR_WHITE}]          [{COLOR_MUTED}]-- Run algorithmic evidence cross-examination[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 7][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]clear-penalty[/bold {COLOR_WHITE}]  [{COLOR_MUTED}]-- Confirm completion of assigned penance[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 8][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]history[/bold {COLOR_WHITE}]        [{COLOR_MUTED}]-- Review historical audit ledger & sanctions[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][ 9][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]remove-history[/bold {COLOR_WHITE}] [{COLOR_MUTED}]-- Purge single or all historical penalty logs[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][10][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]advice[/bold {COLOR_WHITE}]         [{COLOR_MUTED}]-- Optimize goal criteria prior to commitment[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_PRIMARY}][11][/bold {COLOR_PRIMARY}] [bold {COLOR_WHITE}]rollover[/bold {COLOR_WHITE}]       [{COLOR_MUTED}]-- Trigger month-end rollover & auto-audit past-due goals[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_WARNING}][12][/bold {COLOR_WARNING}] [bold {COLOR_WHITE}]reset[/bold {COLOR_WHITE}]          [{COLOR_MUTED}]-- Purge all data and restore factory clean state[/{COLOR_MUTED}]\n"
            f"  [bold {COLOR_DANGER}][ 0][/bold {COLOR_DANGER}] [bold {COLOR_WHITE}]exit[/bold {COLOR_WHITE}]           [{COLOR_MUTED}]-- Terminate active session[/{COLOR_MUTED}]"
        )
        console.print(Panel(menu, border_style=COLOR_DARK_SLATE, box=BOX_STYLE))

    def action_add(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- COMMIT TO NEW MILESTONE ---[/bold {COLOR_PRIMARY}]")
        title = Prompt.ask(f"[bold {COLOR_WHITE}]Goal Title[/bold {COLOR_WHITE}]")
        if not title.strip():
            console.print(f"[{COLOR_DANGER}][!] Cancelled: Goal title cannot be empty.[/{COLOR_DANGER}]")
            return

        criteria = Prompt.ask(f"[bold {COLOR_WHITE}]Quantifiable Criteria[/bold {COLOR_WHITE}] (Target metrics, repository link, or deliverables)")
        if not criteria.strip():
            console.print(f"[{COLOR_DANGER}][!] Cancelled: Verifiable criteria required.[/{COLOR_DANGER}]")
            return

        month = Prompt.ask(
            f"[bold {COLOR_WHITE}]Target Cycle (YYYY-MM)[/bold {COLOR_WHITE}]",
            default=self.db.get_profile().current_month
        )

        goal = self.db.add_goal(title.strip(), criteria.strip(), month.strip())
        console.print(f"\n[bold {COLOR_SUCCESS}][OK] Goal #{goal.id} committed to ledger.[/{COLOR_SUCCESS}]")
        console.print(f"  [{COLOR_SLATE}]Title:[/{COLOR_SLATE}] {goal.title}")
        console.print(f"  [{COLOR_SLATE}]Criteria:[/{COLOR_SLATE}] {goal.target_criteria}")
        console.print(f"  [{COLOR_SLATE}]Cycle:[/{COLOR_SLATE}] {goal.month}\n")

    def action_update(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- UPDATE COMMITMENT RECORD ---[/bold {COLOR_PRIMARY}]")
        goal_id_str = Prompt.ask(f"[bold {COLOR_WHITE}]Goal ID to update[/bold {COLOR_WHITE}]")
        if not goal_id_str.isdigit():
            console.print(f"[{COLOR_DANGER}][!] Invalid Goal ID.[/{COLOR_DANGER}]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[{COLOR_DANGER}][!] Goal #{goal_id} not found.[/{COLOR_DANGER}]")
            return

        console.print(f"Current Title: [{COLOR_PRIMARY}]{goal.title}[/{COLOR_PRIMARY}]")
        new_title = Prompt.ask(f"[bold {COLOR_WHITE}]New Title[/bold {COLOR_WHITE}] (leave blank to keep current)", default=goal.title)

        console.print(f"Current Criteria: [{COLOR_PRIMARY}]{goal.target_criteria}[/{COLOR_PRIMARY}]")
        new_criteria = Prompt.ask(f"[bold {COLOR_WHITE}]New Criteria[/bold {COLOR_WHITE}] (leave blank to keep current)", default=goal.target_criteria)

        updated = self.db.update_goal(goal_id, new_title.strip(), new_criteria.strip())
        console.print(f"\n[bold {COLOR_SUCCESS}][OK] Goal #{goal_id} updated.[/{COLOR_SUCCESS}]")
        console.print(f"  [{COLOR_SLATE}]Title:[/{COLOR_SLATE}] {updated.title}")
        console.print(f"  [{COLOR_SLATE}]Criteria:[/{COLOR_SLATE}] {updated.target_criteria}\n")

    def action_delete(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- REMOVE COMMITMENT RECORD ---[/bold {COLOR_PRIMARY}]")
        goal_id_str = Prompt.ask(f"[bold {COLOR_WHITE}]Goal ID to delete[/bold {COLOR_WHITE}]")
        if not goal_id_str.isdigit():
            console.print(f"[{COLOR_DANGER}][!] Invalid Goal ID.[/{COLOR_DANGER}]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[{COLOR_DANGER}][!] Goal #{goal_id} not found.[/{COLOR_DANGER}]")
            return

        confirm = Confirm.ask(f"[bold {COLOR_DANGER}]Permanently remove Goal #{goal_id} ('{goal.title}')?[/bold {COLOR_DANGER}]")
        if confirm:
            self.db.delete_goal(goal_id)
            console.print(f"[bold {COLOR_SUCCESS}][OK] Goal #{goal_id} removed.[/{COLOR_SUCCESS}]\n")
        else:
            console.print(f"[{COLOR_MUTED}]Removal aborted.[/{COLOR_MUTED}]\n")

    def action_submit(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- SUBMIT VERIFICATION PROOF ---[/bold {COLOR_PRIMARY}]")
        goal_id_str = Prompt.ask(f"[bold {COLOR_WHITE}]Goal ID[/bold {COLOR_WHITE}]")
        if not goal_id_str.isdigit():
            console.print(f"[{COLOR_DANGER}][!] Invalid Goal ID.[/{COLOR_DANGER}]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[{COLOR_DANGER}][!] Goal #{goal_id} not found.[/{COLOR_DANGER}]")
            return

        console.print(f"Goal #{goal_id}: [{COLOR_PRIMARY}]{goal.title}[/{COLOR_PRIMARY}]")
        console.print(f"Required Criteria: [{COLOR_SLATE}]{goal.target_criteria}[/{COLOR_SLATE}]")
        console.print(f"[{COLOR_MUTED}]Evaluation factors: Quantitative numbers, artifact links, dates, and zero justification vocabulary.[/{COLOR_MUTED}]\n")

        evidence = Prompt.ask(f"[bold {COLOR_WHITE}]Enter Verification Evidence Text / Links[/bold {COLOR_WHITE}]")
        if not evidence.strip():
            console.print(f"[{COLOR_DANGER}][!] Evidence submission cannot be empty.[/{COLOR_DANGER}]")
            return

        updated = self.db.submit_evidence(goal_id, evidence.strip())
        console.print(f"\n[bold {COLOR_SUCCESS}][OK] Evidence logged for Goal #{goal_id}.[/{COLOR_SUCCESS}]")
        console.print(f"[{COLOR_MUTED}]Execute '6' or 'audit' to run automated evaluation.[/{COLOR_MUTED}]\n")

    def action_audit(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- INITIATING EVIDENCE CROSS-EXAMINATION ---[/bold {COLOR_PRIMARY}]")
        goal_id_str = Prompt.ask(f"[bold {COLOR_WHITE}]Goal ID to audit[/bold {COLOR_WHITE}]")
        if not goal_id_str.isdigit():
            console.print(f"[{COLOR_DANGER}][!] Invalid Goal ID.[/{COLOR_DANGER}]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[{COLOR_DANGER}][!] Goal #{goal_id} not found.[/{COLOR_DANGER}]")
            return

        console.print(f"\n[{COLOR_SLATE}]Running heuristic validation engine on Goal #{goal_id} ('{goal.title}')...[/{COLOR_SLATE}]")
        decision = self.judge.execute_audit(goal_id)

        if decision.passed:
            panel_content = (
                f"[bold {COLOR_SUCCESS}][PASS] {decision.verdict_summary}[/bold {COLOR_SUCCESS}]\n\n"
                f"[bold {COLOR_WHITE}]Evaluation Log:[/bold {COLOR_WHITE}]\n{decision.feedback}\n\n"
                f"[{COLOR_WARNING}]Reward Granted:[/{COLOR_WARNING}] [bold {COLOR_SUCCESS}]+{decision.xp_delta} XP[/bold {COLOR_SUCCESS}]  |  "
                f"Strikes Added: 0"
            )
            console.print(Panel(panel_content, border_style=COLOR_SUCCESS, box=BOX_STYLE, title=f"[bold {COLOR_SUCCESS}][AUDIT VERDICT :: PASSED][/bold {COLOR_SUCCESS}]"))
        else:
            panel_content = (
                f"[bold {COLOR_DANGER}][FAIL] {decision.verdict_summary}[/bold {COLOR_DANGER}]\n\n"
                f"[bold {COLOR_WHITE}]Evaluation Log:[/bold {COLOR_WHITE}]\n{decision.feedback}\n\n"
                f"[{COLOR_WARNING}]Sanction:[/{COLOR_WARNING}] [bold {COLOR_DANGER}]{decision.xp_delta} XP[/bold {COLOR_DANGER}]  |  "
                f"[bold {COLOR_DANGER}]+{decision.strike_delta} Strike Added[/bold {COLOR_DANGER}]\n\n"
                f"{decision.roast}\n\n"
                f"[bold {COLOR_WHITE}]MANDATORY PENANCE OBLIGATION:[/bold {COLOR_WHITE}]\n"
                f"  >> [bold underline {COLOR_WARNING}]{decision.assigned_penalty}[/bold underline {COLOR_WARNING}]\n\n"
                f"[{COLOR_MUTED}]Complete this task and execute 'clear-penalty' to clear sanction.[/{COLOR_MUTED}]"
            )
            console.print(Panel(panel_content, border_style=COLOR_DANGER, box=BOX_HEAVY, title=f"[bold {COLOR_DANGER}][AUDIT VERDICT :: FAILED & SANCTIONED][/bold {COLOR_DANGER}]"))

    def action_clear_penalty(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- RESOLVE PENANCE OBLIGATION ---[/bold {COLOR_PRIMARY}]")
        uncleared = self.db.get_uncleared_penalties()
        if not uncleared:
            console.print(f"[{COLOR_SUCCESS}][OK] No active penalties recorded.[/{COLOR_SUCCESS}]\n")
            return

        pen_id_str = Prompt.ask(f"[bold {COLOR_WHITE}]Penalty ID to clear[/bold {COLOR_WHITE}]")
        if not pen_id_str.isdigit():
            console.print(f"[{COLOR_DANGER}][!] Invalid Penalty ID.[/{COLOR_DANGER}]")
            return

        pen_id = int(pen_id_str)
        self.db.clear_penalty(pen_id)
        console.print(f"[bold {COLOR_SUCCESS}][OK] Penalty #{pen_id} resolved and recorded in historical ledger.[/{COLOR_SUCCESS}]\n")

    def action_history(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- HISTORICAL AUDIT & PENALTY LEDGER ---[/bold {COLOR_PRIMARY}]")
        penalties = self.db.get_all_penalties()
        if not penalties:
            console.print(f"[{COLOR_MUTED}]Historical ledger is empty.[/{COLOR_MUTED}]\n")
            return

        table = Table(box=BOX_STYLE, border_style=COLOR_DARK_SLATE, header_style=f"bold {COLOR_PRIMARY}")
        table.add_column("ID", width=5, justify="center")
        table.add_column("Cycle", width=8, justify="center")
        table.add_column("Breached Goal", width=25)
        table.add_column("XP Lost", width=9, justify="center")
        table.add_column("Assigned Penance", width=36)
        table.add_column("Status", width=12, justify="center")

        for p in penalties:
            stat = f"[{COLOR_SUCCESS}][RESOLVED][/{COLOR_SUCCESS}]" if p.is_cleared else f"[bold {COLOR_DANGER}][ACTIVE][/bold {COLOR_DANGER}]"
            table.add_row(str(p.id), p.month, p.goal_title, f"-{p.xp_lost}", p.penalty_task, stat)

        console.print(table)

    def action_remove_history(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- PURGE HISTORICAL RECORDS ---[/bold {COLOR_PRIMARY}]")
        choice = Prompt.ask(
            f"[bold {COLOR_WHITE}]Select purge mode[/bold {COLOR_WHITE}]",
            choices=["single", "all", "cancel"],
            default="cancel"
        )
        if choice == "cancel":
            return
        elif choice == "single":
            pen_id_str = Prompt.ask(f"[bold {COLOR_WHITE}]Penalty ID to delete[/bold {COLOR_WHITE}]")
            if pen_id_str.isdigit() and self.db.delete_penalty(int(pen_id_str)):
                console.print(f"[bold {COLOR_SUCCESS}][OK] Penalty record #{pen_id_str} purged.[/{COLOR_SUCCESS}]\n")
            else:
                console.print(f"[{COLOR_DANGER}][!] Record ID not found.[/{COLOR_DANGER}]\n")
        elif choice == "all":
            if Confirm.ask(f"[bold {COLOR_DANGER}]Purge ALL historical audit and penalty entries?[/bold {COLOR_DANGER}]"):
                count = self.db.clear_penalty_history()
                console.print(f"[bold {COLOR_SUCCESS}][OK] Purged {count} records from ledger.[/{COLOR_SUCCESS}]\n")

    def action_advice(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- CRITERIA HARDENING & OPTIMIZATION ---[/bold {COLOR_PRIMARY}]")
        draft_goal = Prompt.ask(f"[bold {COLOR_WHITE}]Draft goal description[/bold {COLOR_WHITE}]")
        if not draft_goal.strip():
            return

        console.print(f"\n[{COLOR_SLATE}]Analyzing draft commitment: '{draft_goal}'...[/{COLOR_SLATE}]")
        
        is_vague = any(w in draft_goal.lower() for w in ["better", "more", "learn", "study", "try", "work on"])
        suggestions = []
        if is_vague:
            suggestions.append(f"[-] Replace subjective verbs ('learn', 'work on') with a tangible deliverable.")
        
        suggestions.append(f"[+] Attach measurable artifact: (e.g. 'Deploy public release to URL', 'Complete 25 sessions', 'Log 50km on Strava').")
        suggestions.append(f"[+] The 70-point verification threshold requires numbers, dates, and artifact links.")

        coaching_panel = (
            f"[bold {COLOR_WARNING}]CRITERIA RECOMMENDATIONS:[/bold {COLOR_WARNING}]\n\n"
            + "\n".join(suggestions) + "\n\n"
            f"[bold {COLOR_WHITE}]Standard Commitment Template:[/bold {COLOR_WHITE}]\n"
            f"  [{COLOR_PRIMARY}]\"Deliver [Artifact] verified via [Link/Report/Hash] with [Specific Metric] by [Date]\"[/{COLOR_PRIMARY}]"
        )
        console.print(Panel(coaching_panel, border_style=COLOR_WARNING, box=BOX_STYLE))

    def action_rollover(self):
        console.print(f"\n[bold {COLOR_PRIMARY}]--- RECONCILING CYCLE ROLLOVER ---[/bold {COLOR_PRIMARY}]")
        res = self.scheduler.check_and_process_rollover()
        if res["rollover_detected"]:
            console.print(f"[bold {COLOR_WARNING}]Cycle rollover executed: {res['previous_month']} -> {res['new_month']}[/bold {COLOR_WARNING}]")
            console.print(f"  - Goals auto-audited: {len(res['audited_goals'])}")
            console.print(f"  - Sanctions applied: {res['penalties_triggered']}")
        else:
            console.print(f"[{COLOR_MUTED}]Current cycle {res['previous_month']} is active. No rollover required.[/{COLOR_MUTED}]\n")

    def action_reset(self):
        console.print(f"\n[bold {COLOR_DANGER}][!] FACTORY PURGE & RESET[/bold {COLOR_DANGER}]")
        confirm = Prompt.ask(
            f"[bold {COLOR_WARNING}]Are you sure you want to purge all commitments, penalties, and history?[/bold {COLOR_WARNING}]",
            choices=["y", "n"],
            default="n"
        )
        if confirm.lower() == "y":
            self.db.reset_database()
            console.print(f"\n[bold {COLOR_SUCCESS}][+] System restored to factory clean state: 0 goals, 0 penalties, 0 strikes (Level 1, 1000 XP).[/bold {COLOR_SUCCESS}]\n")
            self.show_dashboard()
        else:
            console.print(f"[{COLOR_MUTED}]Reset cancelled.[/{COLOR_MUTED}]\n")

    def run(self):
        console.clear()
        profile = self.db.get_profile()

        self.show_dashboard()

        try:
            while True:
                self.show_menu()
                prompt_label = f"[{COLOR_PRIMARY}]tracks:{profile.current_month}[/{COLOR_PRIMARY}] [bold {COLOR_WHITE}]>>[/bold {COLOR_WHITE}] "
                cmd = console.input(prompt_label).strip().lower()

                if cmd in ["0", "exit", "quit", "q"]:
                    console.print(f"\n[{COLOR_SLATE}]Session terminated. Compliance active.[/{COLOR_SLATE}]\n")
                    break
                elif cmd in ["1", "dashboard", "status"]:
                    console.clear()
                    self.show_dashboard()
                elif cmd in ["2", "add"]:
                    self.action_add()
                elif cmd in ["3", "update"]:
                    self.action_update()
                elif cmd in ["4", "delete", "remove"]:
                    self.action_delete()
                elif cmd in ["5", "submit"]:
                    self.action_submit()
                elif cmd in ["6", "audit"]:
                    self.action_audit()
                elif cmd in ["7", "clear-penalty"]:
                    self.action_clear_penalty()
                elif cmd in ["8", "history"]:
                    self.action_history()
                elif cmd in ["9", "remove-history"]:
                    self.action_remove_history()
                elif cmd in ["10", "advice", "coach"]:
                    self.action_advice()
                elif cmd in ["11", "rollover"]:
                    self.action_rollover()
                elif cmd in ["12", "reset", "purge"]:
                    self.action_reset()
                elif cmd in ["clear", "cls"]:
                    console.clear()
                    self.show_dashboard()
                else:
                    console.print(f"[{COLOR_DANGER}][!] Unrecognized command '{cmd}'. Enter 0-12 to execute.[/{COLOR_DANGER}]")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{COLOR_SLATE}]Session interrupted. Compliance active.[/{COLOR_SLATE}]\n")


def launch_agent_shell():
    shell = GoalAgentShell()
    shell.run()


if __name__ == "__main__":
    launch_agent_shell()
