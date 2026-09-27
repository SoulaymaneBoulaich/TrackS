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

console = Console(legacy_windows=False)

def get_status_style(status: GoalStatus) -> str:
    if status == GoalStatus.VERIFIED_COMPLETED:
        return "[bold green]VERIFIED COMPLETED[/bold green]"
    elif status == GoalStatus.EVIDENCE_SUBMITTED:
        return "[bold cyan]EVIDENCE SUBMITTED[/bold cyan]"
    elif status == GoalStatus.FAILED_PENALIZED:
        return "[bold red]FAILED & PENALIZED[/bold red]"
    else:
        return "[bold yellow]PENDING AUDIT[/bold yellow]"

def cmd_status(db: Database):
    profile = db.get_profile()
    uncleared_penalties = db.get_uncleared_penalties()
    
    strikes_bar = "⚠️ " * profile.strikes + "⚪ " * (profile.max_strikes - profile.strikes)
    panel_content = (
        f"[bold]Commander:[/bold] {profile.username}   |   "
        f"[bold]Active Cycle:[/bold] [cyan]{profile.current_month}[/cyan]   |   "
        f"[bold]Level:[/bold] [magenta]{profile.level}[/magenta]   |   "
        f"[bold]XP:[/bold] [yellow]{profile.xp:,}[/yellow]\n"
        f"[bold]Accountability Strikes:[/bold] {strikes_bar} ({profile.strikes}/{profile.max_strikes})\n"
    )

    if profile.strikes >= 3:
        panel_content += "\n[bold red blink]🚨 CODE RED: ACCOUNTABILITY BANKRUPTCY! ALL REWARDS LOCKED! 🚨[/bold red blink]"
    elif uncleared_penalties:
        panel_content += f"\n[bold red]Pending Penalties to Clear: {len(uncleared_penalties)}[/bold red]"

    console.print(Panel(panel_content, title="🎯 GOAL ACCOUNTABILITY DASHBOARD", border_style="blue", box=box.ROUNDED))

    # List current month goals
    goals = db.get_goals_by_month(profile.current_month)
    if not goals:
        console.print(f"[dim]No goals registered for {profile.current_month}. Run 'goaltrack add' to commit to a goal.[/dim]\n")
        return

    table = Table(title=f"Monthly Commitments ({profile.current_month})", box=box.SIMPLE_HEAVY)
    table.add_column("ID", style="bold white", width=5)
    table.add_column("Goal Title", style="bold", width=30)
    table.add_column("Verification Criteria", width=35)
    table.add_column("Status", width=22)
    table.add_column("Evidence", width=20)

    for g in goals:
        ev_summary = (g.evidence[:17] + "...") if g.evidence and len(g.evidence) > 20 else (g.evidence or "[dim]None[/dim]")
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
        console.print("\n[bold red]⚡ UNCLEARED PENALTY TASKS (PENANCE REQUIRED):[/bold red]")
        for p in uncleared_penalties:
            pen_box = (
                f"[bold red]PENALTY #{p.id} for '{p.goal_title}' ({p.month})[/bold red]\n"
                f"[yellow]XP Lost:[/yellow] -{p.xp_lost} | [yellow]Strikes Added:[/yellow] +{p.strike_increment}\n\n"
                f"[bold]Assigned Penance:[/bold]\n👉 [bold underline red]{p.penalty_task}[/bold underline red]\n\n"
                f"[dim]To clear after doing it: goaltrack clear-penalty {p.id}[/dim]"
            )
            console.print(Panel(pen_box, border_style="red", box=box.SQUARE))

def cmd_add(db: Database, title: str, criteria: str, month: str = None):
    profile = db.get_profile()
    target_month = month or profile.current_month
    goal = db.add_goal(title, criteria, target_month)
    console.print(f"\n[green]✓ Goal #{goal.id} committed for {target_month}![/green]")
    console.print(f"  [bold]Title:[/bold] {goal.title}")
    console.print(f"  [bold]Criteria:[/bold] {goal.target_criteria}")
    console.print("[dim]Remember: Vague claims will fail audit. Make sure your proof is airtight.[/dim]\n")

def cmd_submit(db: Database, goal_id: int, evidence: str):
    goal = db.get_goal(goal_id)
    if not goal:
        console.print(f"[red]Error: Goal #{goal_id} not found.[/red]")
        return
    updated = db.submit_evidence(goal_id, evidence)
    console.print(f"\n[cyan]✓ Evidence recorded for Goal #{goal_id}: '{updated.title}'[/cyan]")
    console.print("[dim]Now run 'goaltrack audit <id>' to cross-examine and get final judgment.[/dim]\n")

def cmd_audit(db: Database, goal_id: int):
    goal = db.get_goal(goal_id)
    if not goal:
        console.print(f"[red]Error: Goal #{goal_id} not found.[/red]")
        return
    
    console.print(f"\n[bold yellow]⚖️ INITIATING AI EVIDENCE CROSS-EXAMINATION for Goal #{goal_id}: '{goal.title}'...[/bold yellow]")
    judge = GoalJudge(db)
    decision = judge.execute_audit(goal_id)

    if decision.passed:
        res_text = (
            f"[bold green]🏆 {decision.verdict_summary}[/bold green]\n\n"
            f"[bold]Feedback:[/bold] {decision.feedback}\n"
            f"[bold]XP Reward:[/bold] [bold green]+{decision.xp_delta} XP[/bold green]\n"
            f"[bold]Strikes Added:[/bold] 0"
        )
        console.print(Panel(res_text, title="✅ AUDIT PASSED", border_style="green", box=box.ROUNDED))
    else:
        res_text = (
            f"[bold red]❌ {decision.verdict_summary}[/bold red]\n\n"
            f"[bold]Feedback:[/bold] {decision.feedback}\n"
            f"[bold]XP Penalty:[/bold] [bold red]{decision.xp_delta} XP[/bold red]\n"
            f"[bold]Strikes Added:[/bold] [bold red]+{decision.strike_delta} Strike[/bold red]\n\n"
            f"{decision.roast}\n\n"
            f"[bold red underline]MANDATORY PENALTY TASK:[/bold red underline]\n"
            f"👉 {decision.assigned_penalty}\n\n"
            f"[dim]Complete your penance and run: goaltrack clear-penalty <id>[/dim]"
        )
        console.print(Panel(res_text, title="🔥 AUDIT FAILED & PENALTY ASSIGNED", border_style="red", box=box.HEAVY))

def cmd_clear_penalty(db: Database, penalty_id: int):
    p = db.get_penalty(penalty_id)
    if not p:
        console.print(f"[red]Penalty #{penalty_id} not found.[/red]")
        return
    if p.is_cleared:
        console.print(f"[yellow]Penalty #{penalty_id} is already cleared.[/yellow]")
        return
    db.clear_penalty(penalty_id)
    console.print(f"\n[green]✓ Penalty #{penalty_id} marked as CLEARED![/green]")
    console.print("[dim]Honor restored. Now focus on not failing again next cycle.[/dim]\n")

def cmd_rollover(db: Database):
    scheduler = MonthlyScheduler(db)
    res = scheduler.check_and_process_rollover()
    if res["rollover_detected"]:
        console.print(f"\n[bold cyan]📅 Monthly Rollover Detected: {res['previous_month']} ➔ {res['new_month']}[/bold cyan]")
        console.print(f"  - Goals Audited: {len(res['audited_goals'])}")
        console.print(f"  - Penalties Triggered: {res['penalties_triggered']}\n")
    else:
        console.print(f"\n[dim]No rollover needed. Current active cycle ({res['previous_month']}) matches today's date.[/dim]\n")

def cmd_history(db: Database):
    penalties = db.get_all_penalties()
    if not penalties:
        console.print("[green]No penalties on record. Pristine discipline record![/green]")
        return

    table = Table(title="Historical Accountability & Penalty Ledger", box=box.SIMPLE_HEAVY)
    table.add_column("ID", width=4)
    table.add_column("Month", width=8)
    table.add_column("Failed Goal", width=25)
    table.add_column("XP Lost", width=8)
    table.add_column("Assigned Penance", width=35)
    table.add_column("Status", width=12)

    for p in penalties:
        stat = "[green]CLEARED[/green]" if p.is_cleared else "[bold red]ACTIVE[/bold red]"
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
            console.print(f"[green]✓ Goal #{args.goal_id} updated successfully![/green]")
        else:
            console.print(f"[red]Goal #{args.goal_id} not found.[/red]")
    elif args.command == "delete":
        if db.delete_goal(args.goal_id):
            console.print(f"[green]✓ Goal #{args.goal_id} deleted successfully![/green]")
        else:
            console.print(f"[red]Goal #{args.goal_id} not found.[/red]")
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
                console.print(f"[green]✓ Penalty #{args.penalty_id} removed.[/green]")
            else:
                console.print(f"[red]Penalty #{args.penalty_id} not found.[/red]")
        elif args.all:
            cnt = db.clear_penalty_history()
            console.print(f"[green]✓ Purged {cnt} penalty records from history.[/green]")
        else:
            console.print("[yellow]Specify --penalty-id <id> or --all[/yellow]")

if __name__ == "__main__":
    main()
