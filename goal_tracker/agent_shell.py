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

console = Console(legacy_windows=False)


class GoalAgentShell:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.judge = GoalJudge(self.db)
        self.scheduler = MonthlyScheduler(self.db)

    def print_agent_greeting(self):
        profile = self.db.get_profile()
        uncleared = self.db.get_uncleared_penalties()

        if profile.strikes >= 3:
            avatar = "🚨 [bold red][STRIKE 3 - SYSTEM LOCKDOWN][/bold red]"
            comment = (
                "You have breached the discipline covenant with 3 strikes. "
                "Accountability bankruptcy active. Clear your penances immediately."
            )
        elif profile.strikes == 2:
            avatar = "⚠️ [bold yellow][SENTINEL-X: CODE ORANGE][/bold yellow]"
            comment = (
                "You are one missed goal away from Strike 3. "
                "Every excuse will be scrutinized without mercy."
            )
        elif profile.strikes == 1:
            avatar = "👁️ [bold cyan][SENTINEL-X: WATCHFUL EYE][/bold cyan]"
            comment = "1 strike recorded. Redemption is possible, but complacency will cost you."
        else:
            avatar = "🛡️ [bold green][SENTINEL-X: DISCIPLINE ARBITER][/bold green]"
            comment = (
                "System clean. Zero strikes. Keep your standards high and your evidence airtight."
            )

        greeting_panel = (
            f"{avatar}\n"
            f"[italic white]\"{comment}\"[/italic white]\n\n"
            f"[dim]Commander: [bold cyan]{profile.username}[/bold cyan] | "
            f"XP: [bold yellow]{profile.xp:,}[/bold yellow] | "
            f"Level: [bold magenta]{profile.level}[/bold magenta] | "
            f"Strikes: {'⚠️ ' * profile.strikes + '⚪ ' * (profile.max_strikes - profile.strikes)} ({profile.strikes}/3)[/dim]"
        )
        console.print(Panel(greeting_panel, border_style="cyan", box=box.ROUNDED))

    def show_dashboard(self):
        profile = self.db.get_profile()
        goals = self.db.get_goals_by_month(profile.current_month)
        uncleared_penalties = self.db.get_uncleared_penalties()

        self.print_agent_greeting()

        # Goals Table
        if not goals:
            console.print(
                f"\n[dim yellow]No active goals registered for {profile.current_month}. "
                f"Type '2' or 'add' to commit to a goal.[/dim yellow]\n"
            )
        else:
            table = Table(
                title=f"📋 Monthly Commitments ({profile.current_month})",
                box=box.ROUNDED,
                title_style="bold bold",
                header_style="bold cyan"
            )
            table.add_column("ID", style="bold white", width=5, justify="center")
            table.add_column("Goal Title", style="bold white", width=28)
            table.add_column("Target Criteria", width=34)
            table.add_column("Status", width=22, justify="center")
            table.add_column("Evidence Summary", width=22)

            for g in goals:
                if g.status == GoalStatus.VERIFIED_COMPLETED:
                    status_str = "[bold green]VERIFIED ✓[/bold green]"
                elif g.status == GoalStatus.EVIDENCE_SUBMITTED:
                    status_str = "[bold cyan]EVIDENCE IN[/bold cyan]"
                elif g.status == GoalStatus.FAILED_PENALIZED:
                    status_str = "[bold red]FAILED & PENALIZED[/bold red]"
                else:
                    status_str = "[bold yellow]PENDING AUDIT[/bold yellow]"

                ev_summary = (
                    (g.evidence[:18] + "...")
                    if g.evidence and len(g.evidence) > 20
                    else (g.evidence or "[dim]None[/dim]")
                )
                table.add_row(str(g.id), g.title, g.target_criteria, status_str, ev_summary)

            console.print(table)

        # Uncleared Penances
        if uncleared_penalties:
            console.print("\n[bold red]⚡ UNCLEARED PENANCE TASKS REQUIRING COMPLETION:[/bold red]")
            for p in uncleared_penalties:
                pen_text = (
                    f"[bold red]PENALTY #{p.id} FOR '{p.goal_title}' ({p.month})[/bold red]\n"
                    f"[yellow]Lost:[/yellow] -{p.xp_lost} XP | [yellow]Strikes Added:[/yellow] +{p.strike_increment}\n\n"
                    f"[bold white]Required Penance:[/bold white]\n"
                    f"👉 [bold underline red]{p.penalty_task}[/bold underline red]\n\n"
                    f"[dim]Run 'clear-penalty {p.id}' once you have performed this task.[/dim]"
                )
                console.print(Panel(pen_text, border_style="red", box=box.HEAVY))

    def show_menu(self):
        menu = (
            "[bold cyan]AGENT COMMAND MENU:[/bold cyan]\n"
            "  [bold green]1[/bold green]. [white]dashboard[/white]        - Refresh & view live status\n"
            "  [bold green]2[/bold green]. [white]add[/white]              - Commit to a new monthly goal\n"
            "  [bold green]3[/bold green]. [white]update[/white]           - Edit a goal title or criteria\n"
            "  [bold green]4[/bold green]. [white]delete[/white]           - Remove a goal\n"
            "  [bold green]5[/bold green]. [white]submit[/white]           - Submit proof/evidence for audit\n"
            "  [bold green]6[/bold green]. [white]audit[/white]            - Trigger AI Judge cross-examination & verdict\n"
            "  [bold green]7[/bold green]. [white]clear-penalty[/white]    - Mark completed penance task\n"
            "  [bold green]8[/bold green]. [white]history[/white]          - View past penalty and audit logs\n"
            "  [bold green]9[/bold green]. [white]remove-history[/white]   - Purge or remove penalty records\n"
            "  [bold green]10[/bold green]. [white]advice[/white]          - AI Goal Feasibility & Criteria Coaching\n"
            "  [bold green]11[/bold green]. [white]rollover[/white]        - Check calendar rollover & auto-audit past goals\n"
            "  [bold red]0[/bold red]. [white]exit[/white]            - Quit Sentinel Agent\n"
        )
        console.print(Panel(menu, border_style="dim", box=box.SIMPLE))

    def action_add(self):
        console.print("\n[bold cyan]─── COMMITTING TO A NEW GOAL ───[/bold cyan]")
        title = Prompt.ask("[bold]Enter Goal Title[/bold]")
        if not title.strip():
            console.print("[red]Cancelled: Goal title cannot be empty.[/red]")
            return

        criteria = Prompt.ask("[bold]Enter Verifiable SMART Criteria[/bold] (metrics, artifact URL, or quantitative threshold)")
        if not criteria.strip():
            console.print("[red]Cancelled: SMART criteria required.[/red]")
            return

        month = Prompt.ask(
            "[bold]Target Month (YYYY-MM)[/bold]",
            default=self.db.get_profile().current_month
        )

        goal = self.db.add_goal(title.strip(), criteria.strip(), month.strip())
        console.print(f"\n[bold green]✓ Goal #{goal.id} committed successfully![/bold green]")
        console.print(f"  [cyan]Title:[/cyan] {goal.title}")
        console.print(f"  [cyan]Criteria:[/cyan] {goal.target_criteria}")
        console.print(f"  [cyan]Cycle:[/cyan] {goal.month}\n")

    def action_update(self):
        console.print("\n[bold cyan]─── UPDATE AN EXISTING GOAL ───[/bold cyan]")
        goal_id_str = Prompt.ask("[bold]Enter Goal ID to update[/bold]")
        if not goal_id_str.isdigit():
            console.print("[red]Invalid Goal ID.[/red]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[red]Goal #{goal_id} not found.[/red]")
            return

        console.print(f"Current Title: [cyan]{goal.title}[/cyan]")
        new_title = Prompt.ask("[bold]New Title[/bold] (leave blank to keep current)", default=goal.title)

        console.print(f"Current Criteria: [cyan]{goal.target_criteria}[/cyan]")
        new_criteria = Prompt.ask("[bold]New Criteria[/bold] (leave blank to keep current)", default=goal.target_criteria)

        updated = self.db.update_goal(goal_id, new_title.strip(), new_criteria.strip())
        console.print(f"\n[bold green]✓ Goal #{goal_id} successfully updated![/bold green]")
        console.print(f"  [cyan]Title:[/cyan] {updated.title}")
        console.print(f"  [cyan]Criteria:[/cyan] {updated.target_criteria}\n")

    def action_delete(self):
        console.print("\n[bold cyan]─── REMOVE / DELETE GOAL ───[/bold cyan]")
        goal_id_str = Prompt.ask("[bold]Enter Goal ID to delete[/bold]")
        if not goal_id_str.isdigit():
            console.print("[red]Invalid Goal ID.[/red]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[red]Goal #{goal_id} not found.[/red]")
            return

        confirm = Confirm.ask(f"[bold red]Are you sure you want to permanently delete Goal #{goal_id} ('{goal.title}')?[/bold red]")
        if confirm:
            self.db.delete_goal(goal_id)
            console.print(f"[bold green]✓ Goal #{goal_id} deleted.[/bold green]\n")
        else:
            console.print("[dim]Deletion cancelled.[/dim]\n")

    def action_submit(self):
        console.print("\n[bold cyan]─── SUBMIT PROOF / EVIDENCE ───[/bold cyan]")
        goal_id_str = Prompt.ask("[bold]Enter Goal ID[/bold]")
        if not goal_id_str.isdigit():
            console.print("[red]Invalid Goal ID.[/red]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[red]Goal #{goal_id} not found.[/red]")
            return

        console.print(f"[bold]Submitting evidence for Goal #{goal_id}:[/bold] '{goal.title}'")
        console.print(f"[bold]Target criteria was:[/bold] '{goal.target_criteria}'")
        console.print("[dim]Tips: Provide URLs, commit hashes, specific metrics, file locations, and dates to ensure a passing score.[/dim]\n")

        evidence = Prompt.ask("[bold]Enter Your Verification Evidence / Proof[/bold]")
        if not evidence.strip():
            console.print("[red]Evidence cannot be blank.[/red]")
            return

        updated = self.db.submit_evidence(goal_id, evidence.strip())
        console.print(f"\n[bold green]✓ Evidence recorded for Goal #{goal_id}![/bold green]")
        console.print("[dim]You can now run '6' or 'audit' to receive AI Judge evaluation.[/dim]\n")

    def action_audit(self):
        console.print("\n[bold cyan]─── AI EVIDENCE AUDIT & CROSS-EXAMINATION ───[/bold cyan]")
        goal_id_str = Prompt.ask("[bold]Enter Goal ID to audit[/bold]")
        if not goal_id_str.isdigit():
            console.print("[red]Invalid Goal ID.[/red]")
            return

        goal_id = int(goal_id_str)
        goal = self.db.get_goal(goal_id)
        if not goal:
            console.print(f"[red]Goal #{goal_id} not found.[/red]")
            return

        console.print(f"\n[dim cyan]⚖️ INITIATING SENTINEL-X CROSS-EXAMINATION FOR '{goal.title}'...[/dim cyan]")
        decision = self.judge.execute_audit(goal_id)

        if decision.passed:
            panel_content = (
                f"[bold green]🏆 {decision.verdict_summary}[/bold green]\n\n"
                f"[bold]Feedback Analysis:[/bold]\n{decision.feedback}\n\n"
                f"[yellow]XP Reward:[/yellow] [bold green]+{decision.xp_delta} XP[/bold green]\n"
                f"[cyan]Accountability Strikes:[/cyan] 0"
            )
            console.print(Panel(panel_content, border_style="green", box=box.ROUNDED, title="✅ AUDIT PASSED"))
        else:
            panel_content = (
                f"[bold red]❌ {decision.verdict_summary}[/bold red]\n\n"
                f"[bold]Feedback Analysis:[/bold]\n{decision.feedback}\n\n"
                f"[yellow]XP Penalty:[/yellow] [bold red]{decision.xp_delta} XP[/bold red]\n"
                f"[red]Strikes Added:[/red] [bold red]+{decision.strike_delta} Strike[/bold red]\n\n"
                f"{decision.roast}\n\n"
                f"[bold white]MANDATORY PENALTY TASK:[/bold white]\n"
                f"👉 [bold underline red]{decision.assigned_penalty}[/bold underline red]\n\n"
                f"[dim]Complete this penance and run 'clear-penalty' to restore honor.[/dim]"
            )
            console.print(Panel(panel_content, border_style="red", box=box.HEAVY, title="🔥 AUDIT FAILED & PENALIZED"))

    def action_clear_penalty(self):
        console.print("\n[bold cyan]─── CLEAR ASSIGNED PENALTY TASK ───[/bold cyan]")
        uncleared = self.db.get_uncleared_penalties()
        if not uncleared:
            console.print("[green]No uncleared penalties found! You have zero active penances.[/green]\n")
            return

        pen_id_str = Prompt.ask("[bold]Enter Penalty ID to clear[/bold]")
        if not pen_id_str.isdigit():
            console.print("[red]Invalid Penalty ID.[/red]")
            return

        pen_id = int(pen_id_str)
        self.db.clear_penalty(pen_id)
        console.print(f"[bold green]✓ Penalty #{pen_id} marked as CLEARED![/bold green]")
        console.print("[dim]Honor restored. Maintain your discipline for the rest of the cycle.[/dim]\n")

    def action_history(self):
        console.print("\n[bold cyan]─── HISTORICAL ACCOUNTABILITY & PENALTY LEDGER ───[/bold cyan]")
        penalties = self.db.get_all_penalties()
        if not penalties:
            console.print("[dim]No penalty history recorded in the ledger.[/dim]\n")
            return

        table = Table(box=box.SIMPLE_HEAVY, header_style="bold magenta")
        table.add_column("ID", width=5, justify="center")
        table.add_column("Cycle", width=8, justify="center")
        table.add_column("Failed Goal", width=25)
        table.add_column("XP Lost", width=9, justify="center")
        table.add_column("Assigned Penance", width=36)
        table.add_column("Status", width=12, justify="center")

        for p in penalties:
            stat = "[green]CLEARED[/green]" if p.is_cleared else "[bold red]ACTIVE[/bold red]"
            table.add_row(str(p.id), p.month, p.goal_title, f"-{p.xp_lost}", p.penalty_task, stat)

        console.print(table)

    def action_remove_history(self):
        console.print("\n[bold cyan]─── PURGE / REMOVE HISTORY ───[/bold cyan]")
        choice = Prompt.ask(
            "[bold]Select option[/bold]",
            choices=["single", "all", "cancel"],
            default="cancel"
        )
        if choice == "cancel":
            return
        elif choice == "single":
            pen_id_str = Prompt.ask("[bold]Enter Penalty ID to delete[/bold]")
            if pen_id_str.isdigit() and self.db.delete_penalty(int(pen_id_str)):
                console.print(f"[bold green]✓ Penalty #{pen_id_str} deleted from history.[/bold green]\n")
            else:
                console.print("[red]Penalty ID not found.[/red]\n")
        elif choice == "all":
            if Confirm.ask("[bold red]Purge ALL historical penalty records permanently?[/bold red]"):
                count = self.db.clear_penalty_history()
                console.print(f"[bold green]✓ Purged {count} penalty records from history.[/bold green]\n")

    def action_advice(self):
        console.print("\n[bold cyan]─── AI GOAL COACHING & CRITERIA STRENGTHENING ───[/bold cyan]")
        draft_goal = Prompt.ask("[bold]Describe the goal you want to achieve[/bold]")
        if not draft_goal.strip():
            return

        console.print(f"\n[dim cyan]Analyzing goal: '{draft_goal}'...[/dim cyan]")
        
        # Heuristic coaching analysis
        is_vague = any(w in draft_goal.lower() for w in ["better", "more", "learn", "study", "try", "work on"])
        suggestions = []
        if is_vague:
            suggestions.append("⚠️ Goal uses subjective or vague wording. Replace 'learn/work on' with a concrete deliverable.")
        
        suggestions.append("💡 SMART Recommendation: Attach an exact artifact (e.g. 'Deploy repository to URL', 'Complete 30 sessions with Strava log', 'Write 10,000 words in docs/').")
        suggestions.append("💡 Pass Requirement: AI Judge requires numbers (e.g., 20 chapters, 50km), dates, and verifiable links to pass the 70-point threshold.")

        coaching_panel = (
            f"[bold yellow]SENTINEL-X COACHING FEEDBACK:[/bold yellow]\n\n"
            + "\n".join(suggestions) + "\n\n"
            f"[bold green]Recommended Criteria Format:[/bold green]\n"
            f"\"Deliver [Specific Artifact] verified via [Link/Log/File] with [Exact Metric] by [Date]\""
        )
        console.print(Panel(coaching_panel, border_style="yellow", box=box.ROUNDED))

    def action_rollover(self):
        console.print("\n[bold cyan]─── EXECUTING MONTH-END ROLLOVER CHECK ───[/bold cyan]")
        res = self.scheduler.check_and_process_rollover()
        if res["rollover_detected"]:
            console.print(f"[bold yellow]Month rollover detected from {res['previous_month']} to {res['new_month']}![/bold yellow]")
            console.print(f"  - Goals auto-audited: {len(res['audited_goals'])}")
            console.print(f"  - Penalties triggered: {res['penalties_triggered']}")
        else:
            console.print(f"[dim]Still in active cycle {res['previous_month']}. No rollover needed.[/dim]\n")

    def run(self):
        console.clear()
        console.print("[bold cyan]════════════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]       SENTINEL-X: AUTONOMOUS AI GOAL & PENALTY TRACKER          [/bold yellow]")
        console.print("[bold cyan]════════════════════════════════════════════════════════════════════[/bold cyan]\n")

        self.show_dashboard()

        try:
            while True:
                self.show_menu()
                cmd = Prompt.ask("\n[bold cyan][SENTINEL-X][/bold cyan] [bold white]Select action[/bold white]").strip().lower()

                if cmd in ["0", "exit", "quit", "q"]:
                    console.print("\n[bold yellow]Exiting Sentinel-X. Stay disciplined.[/bold yellow]\n")
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
                elif cmd in ["clear", "cls"]:
                    console.clear()
                    self.show_dashboard()
                else:
                    console.print(f"[red]Unknown command '{cmd}'. Select 1-11 or 0 to exit.[/red]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Session ended. Stay disciplined.[/bold yellow]\n")


def launch_agent_shell():
    shell = GoalAgentShell()
    shell.run()


if __name__ == "__main__":
    launch_agent_shell()
