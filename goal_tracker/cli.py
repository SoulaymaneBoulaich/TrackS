import sys
import argparse
from datetime import datetime

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
from rich.text import Text
from rich import box

from goal_tracker.database import Database
from goal_tracker.judge import GoalJudge
from goal_tracker.scheduler import MonthlyScheduler
from goal_tracker.models import GoalStatus
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

def get_status_style(status: GoalStatus) -> str:
    return format_status_badge(status)

def cmd_status(db: Database):
    profile = db.get_profile()
    uncleared_penalties = db.get_uncleared_penalties()
    goals = db.get_goals_by_month(profile.current_month)
    
    strikes_bar = format_strike_gauge(profile.strikes, profile.max_strikes)
    cycle_prog = render_cycle_progress(profile.current_month, goals)
    
    panel_content = (
        f"[bold {COLOR_PRIMARY}]OPERATOR:[/bold {COLOR_PRIMARY}] {profile.username}   |   "
        f"[bold {COLOR_PRIMARY}]ACTIVE CYCLE:[/bold {COLOR_PRIMARY}] [{COLOR_PRIMARY}]{profile.current_month}[/{COLOR_PRIMARY}]   |   "
        f"[bold {COLOR_PRIMARY}]TIER:[/bold {COLOR_PRIMARY}] [{COLOR_SECONDARY}]LEVEL {profile.level}[/{COLOR_SECONDARY}]   |   "
        f"[bold {COLOR_PRIMARY}]XP:[/bold {COLOR_PRIMARY}] [{COLOR_WARNING}]{profile.xp:,}[/{COLOR_WARNING}]\n"
        f"[bold {COLOR_PRIMARY}]STRIKES:[/bold {COLOR_PRIMARY}] {strikes_bar}\n"
        f"{cycle_prog}"
    )

    if profile.strikes >= 3:
        panel_content += f"\n\n[bold {COLOR_DANGER} blink][!] CODE RED: ACCOUNTABILITY BANKRUPTCY - ALL PRIVILEGES LOCKED [!][/bold {COLOR_DANGER} blink]"
    elif uncleared_penalties:
        panel_content += f"\n\n[bold {COLOR_DANGER}][!] PENDING PENANCE TASKS TO CLEAR: {len(uncleared_penalties)}[/bold {COLOR_DANGER}]"

    console.print(Panel(panel_content, title=f"[bold {COLOR_PRIMARY}]TrackS // ACCOUNTABILITY DASHBOARD[/bold {COLOR_PRIMARY}]", border_style=COLOR_PRIMARY, box=BOX_STYLE))

    # List current month goals
    if not goals:
        console.print(f"[{COLOR_MUTED}]No commitments registered for {profile.current_month}. Run 'tracks add' to commit.[/{COLOR_MUTED}]\n")
        return

    table = Table(title=f"Commitments Ledger ({profile.current_month})", box=box.ROUNDED, border_style=COLOR_DARK_SLATE)
    table.add_column("ID", style=f"bold {COLOR_WHITE}", width=5)
    table.add_column("Commitment Title", style=f"bold {COLOR_WHITE}", width=30)
    table.add_column("Verification Criteria", style=COLOR_SLATE, width=35)
    table.add_column("Audit Status", width=22)
    table.add_column("Evidence", style=COLOR_SLATE, width=20)

    for g in goals:
        ev_summary = (g.evidence[:17] + "...") if g.evidence and len(g.evidence) > 20 else (g.evidence or f"[{COLOR_MUTED}]None[/{COLOR_MUTED}]")
        table.add_row(
            str(g.id),
            g.title,
            g.target_criteria,
            get_status_style(g.status),
            ev_summary
        )
    console.print(table)

    # Show uncleared penalties if any
    if uncleared_penalties:
        console.print(f"\n[bold {COLOR_DANGER}][!] UNCLEARED PENALTY TASKS (PENANCE REQUIRED):[/bold {COLOR_DANGER}]")
        for p in uncleared_penalties:
            pen_box = (
                f"[bold {COLOR_DANGER}]PENALTY #{p.id} for '{p.goal_title}' ({p.month})[/bold {COLOR_DANGER}]\n"
                f"[{COLOR_WARNING}]XP Lost:[/{COLOR_WARNING}] -{p.xp_lost} | [{COLOR_DANGER}]Strikes Added:[/{COLOR_DANGER}] +{p.strike_increment}\n\n"
                f"[bold {COLOR_WHITE}]Assigned Penance:[/bold {COLOR_WHITE}]\n"
                f"[-] [bold {COLOR_DANGER}]{p.penalty_task}[/bold {COLOR_DANGER}]\n\n"
                f"[{COLOR_MUTED}]To clear after completion: tracks clear-penalty {p.id}[/{COLOR_MUTED}]"
            )
            console.print(Panel(pen_box, border_style=COLOR_DANGER, box=BOX_STYLE))

def cmd_add(db: Database, title: str, criteria: str, month: str = None):
    profile = db.get_profile()
    target_month = month or profile.current_month
    goal = db.add_goal(title, criteria, target_month)
    console.print(f"\n[bold {COLOR_SUCCESS}][+] Goal #{goal.id} committed for cycle {target_month}![/bold {COLOR_SUCCESS}]")
    console.print(f"  [bold {COLOR_PRIMARY}]Title:[/bold {COLOR_PRIMARY}] {goal.title}")
    console.print(f"  [bold {COLOR_PRIMARY}]Criteria:[/bold {COLOR_PRIMARY}] {goal.target_criteria}")
    console.print(f"[{COLOR_MUTED}]Proof standard: Vague claims fail cross-examination. Prepare verifiable artifacts.[/{COLOR_MUTED}]\n")

def cmd_submit(db: Database, goal_id: int, evidence: str):
    goal = db.get_goal(goal_id)
    if not goal:
        console.print(f"[bold {COLOR_DANGER}][!] Error: Goal #{goal_id} not found.[/bold {COLOR_DANGER}]")
        return
    updated = db.submit_evidence(goal_id, evidence)
    console.print(f"\n[bold {COLOR_PRIMARY}][+] Evidence recorded for Goal #{goal_id}: '{updated.title}'[/bold {COLOR_PRIMARY}]")
    console.print(f"[{COLOR_MUTED}]Initiate audit via: tracks audit {goal_id}[/{COLOR_MUTED}]\n")

def cmd_audit(db: Database, goal_id: int):
    goal = db.get_goal(goal_id)
    if not goal:
        console.print(f"[bold {COLOR_DANGER}][!] Error: Goal #{goal_id} not found.[/bold {COLOR_DANGER}]")
        return
    
    console.print(f"\n[bold {COLOR_WARNING}][*] INITIATING AI EVIDENCE AUDIT for Goal #{goal_id}: '{goal.title}'...[/bold {COLOR_WARNING}]")
    judge = GoalJudge(db)
    decision = judge.execute_audit(goal_id)

    if decision.passed:
        res_text = (
            f"[bold {COLOR_SUCCESS}][PASS] {decision.verdict_summary}[/bold {COLOR_SUCCESS}]\n\n"
            f"[bold {COLOR_PRIMARY}]Feedback:[/bold {COLOR_PRIMARY}] {decision.feedback}\n"
            f"[bold {COLOR_PRIMARY}]XP Reward:[/bold {COLOR_PRIMARY}] [bold {COLOR_SUCCESS}]+{decision.xp_delta} XP[/bold {COLOR_SUCCESS}]\n"
            f"[bold {COLOR_PRIMARY}]Strikes Added:[/bold {COLOR_PRIMARY}] 0"
        )
        console.print(Panel(res_text, title=f"[bold {COLOR_SUCCESS}][PASS] AUDIT VERIFIED[/bold {COLOR_SUCCESS}]", border_style=COLOR_SUCCESS, box=BOX_STYLE))
    else:
        res_text = (
            f"[bold {COLOR_DANGER}][FAIL] {decision.verdict_summary}[/bold {COLOR_DANGER}]\n\n"
            f"[bold {COLOR_PRIMARY}]Feedback:[/bold {COLOR_PRIMARY}] {decision.feedback}\n"
            f"[bold {COLOR_PRIMARY}]XP Penalty:[/bold {COLOR_PRIMARY}] [bold {COLOR_DANGER}]{decision.xp_delta} XP[/bold {COLOR_DANGER}]\n"
            f"[bold {COLOR_PRIMARY}]Strikes Added:[/bold {COLOR_PRIMARY}] [bold {COLOR_DANGER}]+{decision.strike_delta} Strike[/bold {COLOR_DANGER}]\n\n"
            f"{decision.roast}\n\n"
            f"[bold {COLOR_DANGER}]MANDATORY PENALTY TASK:[/bold {COLOR_DANGER}]\n"
            f"[-] {decision.assigned_penalty}\n\n"
            f"[{COLOR_MUTED}]Complete penance and run: tracks clear-penalty {goal_id}[/{COLOR_MUTED}]"
        )
        console.print(Panel(res_text, title=f"[bold {COLOR_DANGER}][FAIL] AUDIT REJECTED & PENALTY ASSIGNED[/bold {COLOR_DANGER}]", border_style=COLOR_DANGER, box=BOX_STYLE))

def cmd_clear_penalty(db: Database, penalty_id: int):
    p = db.get_penalty(penalty_id)
    if not p:
        console.print(f"[bold {COLOR_DANGER}][!] Penalty #{penalty_id} not found.[/bold {COLOR_DANGER}]")
        return
    if p.is_cleared:
        console.print(f"[bold {COLOR_WARNING}][*] Penalty #{penalty_id} is already cleared.[/bold {COLOR_WARNING}]")
        return
    db.clear_penalty(penalty_id)
    console.print(f"\n[bold {COLOR_SUCCESS}][+] Penalty #{penalty_id} marked as CLEARED.[/bold {COLOR_SUCCESS}]")
    console.print(f"[{COLOR_MUTED}]Ledger updated. Maintain discipline in the active cycle.[/{COLOR_MUTED}]\n")

def cmd_rollover(db: Database):
    scheduler = MonthlyScheduler(db)
    res = scheduler.check_and_process_rollover()
    if res["rollover_detected"]:
        console.print(f"\n[bold {COLOR_PRIMARY}][*] Monthly Rollover Detected: {res['previous_month']} -> {res['new_month']}[/bold {COLOR_PRIMARY}]")
        console.print(f"  - Goals Audited: {len(res['audited_goals'])}")
        console.print(f"  - Penalties Triggered: {res['penalties_triggered']}\n")
    else:
        console.print(f"\n[{COLOR_MUTED}]No rollover needed. Current cycle ({res['previous_month']}) matches today's date.[/{COLOR_MUTED}]\n")

def cmd_history(db: Database):
    penalties = db.get_all_penalties()
    if not penalties:
        console.print(f"[bold {COLOR_SUCCESS}][+] No penalties on record. Pristine discipline track record.[/bold {COLOR_SUCCESS}]")
        return

    table = Table(title="Accountability & Penalty History Ledger", box=box.ROUNDED, border_style=COLOR_DARK_SLATE)
    table.add_column("ID", width=4, style=f"bold {COLOR_WHITE}")
    table.add_column("Cycle", width=8, style=COLOR_SLATE)
    table.add_column("Failed Goal", width=25, style=f"bold {COLOR_WHITE}")
    table.add_column("XP Lost", width=8, style=COLOR_DANGER)
    table.add_column("Assigned Penance", width=35, style=COLOR_SLATE)
    table.add_column("Status", width=12)

    for p in penalties:
        stat = f"[bold {COLOR_SUCCESS}][CLEARED][/bold {COLOR_SUCCESS}]" if p.is_cleared else f"[bold {COLOR_DANGER}][ACTIVE][/bold {COLOR_DANGER}]"
        table.add_row(str(p.id), p.month, p.goal_title, f"-{p.xp_lost}", p.penalty_task, stat)

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="GoalTracker: Ruthless AI Monthly Accountability & Penalty System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status / List
    subparsers.add_parser("list", help="List monthly goals and current accountability dashboard")
    subparsers.add_parser("status", help="Show accountability dashboard status")

    # Add goal
    parser_add = subparsers.add_parser("add", help="Add a new monthly goal")
    parser_add.add_argument("title", type=str, help="Goal title (e.g. 'Read 2 books')")
    parser_add.add_argument("--criteria", "-c", type=str, required=True, help="Verifiable SMART criteria")
    parser_add.add_argument("--month", "-m", type=str, default=None, help="Target month in YYYY-MM format")

    # Submit evidence
    parser_submit = subparsers.add_parser("submit", help="Submit evidence of completion for a goal")
    parser_submit.add_argument("goal_id", type=int, help="Goal ID")
    parser_submit.add_argument("evidence", type=str, help="Proof text, metrics, file paths, or links")

    # Audit goal
    parser_audit = subparsers.add_parser("audit", help="Run AI Evidence Cross-Examination & Judgment")
    parser_audit.add_argument("goal_id", type=int, help="Goal ID to audit")

    # Clear penalty
    parser_clear = subparsers.add_parser("clear-penalty", help="Mark an assigned penalty task as completed")
    parser_clear.add_argument("penalty_id", type=int, help="Penalty ID to clear")

    # Update goal
    parser_update = subparsers.add_parser("update", help="Update goal title or criteria")
    parser_update.add_argument("goal_id", type=int, help="Goal ID to update")
    parser_update.add_argument("--title", "-t", type=str, default=None, help="New title")
    parser_update.add_argument("--criteria", "-c", type=str, default=None, help="New criteria")

    # Delete goal
    parser_delete = subparsers.add_parser("delete", help="Delete a goal")
    parser_delete.add_argument("goal_id", type=int, help="Goal ID to delete")

    # Rollover
    subparsers.add_parser("rollover", help="Check and execute monthly rollover check")

    # History
    subparsers.add_parser("history", help="Show past penalty ledger and audit history")

    # Remove history
    parser_rem = subparsers.add_parser("remove-history", help="Delete historical penalties")
    parser_rem.add_argument("--penalty-id", "-p", type=int, default=None, help="Specific penalty ID to delete")
    parser_rem.add_argument("--all", action="store_true", help="Purge all penalty records")

    # Reset
    parser_reset = subparsers.add_parser("reset", help="Purge all goals and penalties and reset profile to clean state")
    parser_reset.add_argument("--yes", "-y", action="store_true", help="Confirm reset without interactive prompt")

    # Interactive Agent Shell
    subparsers.add_parser("agent", help="Launch the interactive AI Agent terminal shell")
    subparsers.add_parser("interactive", help="Launch the interactive AI Agent terminal shell")

    args = parser.parse_args()
    db = Database()

    if args.command is None or args.command in ["agent", "interactive"]:
        from goal_tracker.agent_shell import launch_agent_shell
        launch_agent_shell()
    elif args.command in ["list", "status"]:
        cmd_status(db)
    elif args.command == "add":
        cmd_add(db, args.title, args.criteria, args.month)
    elif args.command == "update":
        updated = db.update_goal(args.goal_id, args.title, args.criteria)
        if updated:
            console.print(f"[bold {COLOR_SUCCESS}][+] Goal #{args.goal_id} updated successfully![/bold {COLOR_SUCCESS}]")
        else:
            console.print(f"[bold {COLOR_DANGER}][!] Goal #{args.goal_id} not found.[/bold {COLOR_DANGER}]")
    elif args.command == "delete":
        if db.delete_goal(args.goal_id):
            console.print(f"[bold {COLOR_SUCCESS}][+] Goal #{args.goal_id} deleted successfully![/bold {COLOR_SUCCESS}]")
        else:
            console.print(f"[bold {COLOR_DANGER}][!] Goal #{args.goal_id} not found.[/bold {COLOR_DANGER}]")
    elif args.command == "submit":
        cmd_submit(db, args.goal_id, args.evidence)
    elif args.command == "audit":
        cmd_audit(db, args.goal_id)
    elif args.command == "clear-penalty":
        cmd_clear_penalty(db, args.penalty_id)
    elif args.command == "rollover":
        cmd_rollover(db)
    elif args.command == "history":
        cmd_history(db)
    elif args.command == "remove-history":
        if args.penalty_id:
            if db.delete_penalty(args.penalty_id):
                console.print(f"[bold {COLOR_SUCCESS}][+] Penalty #{args.penalty_id} removed.[/bold {COLOR_SUCCESS}]")
            else:
                console.print(f"[bold {COLOR_DANGER}][!] Penalty #{args.penalty_id} not found.[/bold {COLOR_DANGER}]")
        elif args.all:
            cnt = db.clear_penalty_history()
            console.print(f"[bold {COLOR_SUCCESS}][+] Purged {cnt} penalty records from history.[/bold {COLOR_SUCCESS}]")
        else:
            console.print(f"[bold {COLOR_WARNING}][!] Specify --penalty-id <id> or --all[/bold {COLOR_WARNING}]")
    elif args.command == "reset":
        if args.yes:
            db.reset_database()
            console.print(f"[bold {COLOR_SUCCESS}][+] Database reset: All goals and penalties purged, profile restored to Level 1 (1000 XP, 0 strikes).[/bold {COLOR_SUCCESS}]")
        else:
            ans = input("Are you sure you want to reset all goals and penalties? (y/N): ")
            if ans.strip().lower() in ["y", "yes"]:
                db.reset_database()
                console.print(f"[bold {COLOR_SUCCESS}][+] Database reset successfully.[/bold {COLOR_SUCCESS}]")
            else:
                console.print(f"[bold {COLOR_WARNING}][*] Reset aborted.[/bold {COLOR_WARNING}]")

if __name__ == "__main__":
    main()
