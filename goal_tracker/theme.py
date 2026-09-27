"""
TrackS Cyber-Slate Industrial Design System Tokens
Strictly zero emojis. Monospace aligned ASCII indicators and color tokens.
"""

import calendar
from datetime import datetime
from rich import box
from rich.text import Text
from rich.panel import Panel

from goal_tracker.models import GoalStatus

# Color Tokens
COLOR_PRIMARY = "#00e5ff"       # Electric Cyan
COLOR_SECONDARY = "#a855f7"     # Violet / Level indicator
COLOR_SUCCESS = "#00ff88"       # Bright Mint
COLOR_WARNING = "#f59e0b"       # Industrial Amber
COLOR_DANGER = "#ef4444"        # Crimson Alert
COLOR_SLATE = "#94a3b8"         # Muted Slate
COLOR_DARK_SLATE = "#334155"    # Border / Divider
COLOR_WHITE = "#f8fafc"         # Crisp White
COLOR_MUTED = "#64748b"         # Dim text

BOX_STYLE = box.ROUNDED
BOX_HEAVY = box.HEAVY_EDGE

def format_status_badge(status: GoalStatus) -> str:
    """Returns color-coded bracketed ASCII status badges."""
    if status == GoalStatus.VERIFIED_COMPLETED:
        return f"[bold {COLOR_SUCCESS}][VERIFIED][/bold {COLOR_SUCCESS}]"
    elif status == GoalStatus.EVIDENCE_SUBMITTED:
        return f"[bold {COLOR_PRIMARY}][EVIDENCE][/bold {COLOR_PRIMARY}]"
    elif status == GoalStatus.FAILED_PENALIZED:
        return f"[bold {COLOR_DANGER}][PENALIZED][/bold {COLOR_DANGER}]"
    else:
        return f"[bold {COLOR_WARNING}][PENDING][/bold {COLOR_WARNING}]"

def format_strike_gauge(strikes: int, max_strikes: int = 3) -> str:
    """Returns clean ASCII monospace strike meter: [!] [!] [ - ]."""
    slots = []
    for i in range(max_strikes):
        if i < strikes:
            slots.append(f"[bold {COLOR_DANGER}][!][/bold {COLOR_DANGER}]")
        else:
            slots.append(f"[{COLOR_DARK_SLATE}][-][/{COLOR_DARK_SLATE}]")
    
    meter_str = " ".join(slots)
    if strikes >= 3:
        return f"{meter_str} [bold {COLOR_DANGER}CRITICAL LOCKOUT (3/3)[/bold {COLOR_DANGER}]"
    elif strikes == 2:
        return f"{meter_str} [bold {COLOR_WARNING}CODE ORANGE (2/3)[/bold {COLOR_WARNING}]"
    elif strikes == 1:
        return f"{meter_str} [{COLOR_SLATE}]ALERT (1/3)[/{COLOR_SLATE}]"
    else:
        return f"{meter_str} [{COLOR_SUCCESS}]NOMINAL (0/3)[/{COLOR_SUCCESS}]"

def render_cycle_progress(current_month: str, goals: list) -> str:
    """
    Renders an ASCII progress bar calculating days elapsed in active cycle and goals completed.
    Example: [============>-------] 63% (11d remaining) | GOALS: 2/3 (66%)
    """
    try:
        year, month = map(int, current_month.split("-"))
    except Exception:
        now = datetime.now()
        year, month = now.year, now.month

    now = datetime.now()
    _, num_days = calendar.monthrange(year, month)

    if now.year == year and now.month == month:
        current_day = min(now.day, num_days)
    elif (now.year, now.month) > (year, month):
        current_day = num_days
    else:
        current_day = 1

    days_remaining = max(0, num_days - current_day)
    elapsed_pct = int((current_day / num_days) * 100)

    # 20-character ASCII bar
    bar_length = 20
    filled = int((current_day / num_days) * bar_length)
    if filled > 0 and filled < bar_length:
        bar = "=" * (filled - 1) + ">" + "-" * (bar_length - filled)
    elif filled >= bar_length:
        bar = "=" * bar_length
    else:
        bar = "-" * bar_length

    total_goals = len(goals)
    completed_goals = sum(1 for g in goals if g.status == GoalStatus.VERIFIED_COMPLETED)
    goal_pct = int((completed_goals / total_goals * 100)) if total_goals > 0 else 0

    return (
        f"[{COLOR_PRIMARY}]CYCLE {current_month}[/{COLOR_PRIMARY}]  |  "
        f"TIME: [[bold {COLOR_PRIMARY}]{bar}[/bold {COLOR_PRIMARY}]] {elapsed_pct}% ({days_remaining}d left)  |  "
        f"COMPLETION: [{COLOR_SUCCESS}]{completed_goals}/{total_goals}[/{COLOR_SUCCESS}] ({goal_pct}%)"
    )
