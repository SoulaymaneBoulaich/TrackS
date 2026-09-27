# 🎯 GoalTracker: Ruthless AI Monthly Accountability & Penalty Engine

An automated accountability tracking system designed and engineered by the 40-agent swarm (`@product-manager`, `@backend-architect`, `@prompt-engineer`, `@qa-testing`).

GoalTracker ensures you do not just write monthly goals—it verifies completion through an **AI Evidence Audit Engine**, awards XP for substantiated achievements, and **ruthlessly penalizes failures** with XP loss, 3-strike escalation, psychological AI roasts, and mandatory penance tasks.

---

## ⚡ Core Architecture

```
[ User Monthly Goals ] 
        │
        ▼
[ Evidence Submission ] (Artifacts, metrics, links, dates)
        │
        ▼
[ AI Judge & Cross-Examiner ] ──(Score < 70)──► [ Ruthless AI Roaster ]
        │                                                │
   (Score >= 70)                                         ▼
        │                                   [ -250 XP & +1 Strike Added ]
        ▼                                   [ Tiered Penance Assigned ]
 [ +100-150 XP Awarded ]                                 │
        │                                                ▼
        └───────────────────► [ SQLite Ledger & Monthly Daemon ]
```

## 🌐 Universal One-Line Global Installer

Users do not need to download or clone `.py` files manually. They can simply run:

### Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/SoulaymaneBoulaich/TrackS/main/install.ps1 | iex
```
*(Or locally: `powershell -ExecutionPolicy Bypass -File .\install.ps1`)*

### macOS / Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/SoulaymaneBoulaich/TrackS/main/install.sh | bash
```

**What the installer does automatically:**
1. Prompts you to choose your **trusted folder** (e.g. `C:\Users\Username\.sentinel-x` or custom path).
2. Deploys the self-contained Sentinel-X engine and required dependencies.
3. Automatically registers `sentinel` and `goaltrack` to your permanent system `PATH`.
4. Immediately launches Sentinel-X in your current window!

---

## 🚀 Interactive AI Agent Terminal Shell

To launch the full interactive AI Agent shell with real-time dashboard and command menu:

```bash
cd c:\Users\dell\Documents\goal_penalty_tracker
python -m goal_tracker
```
*(Or `python -m goal_tracker.cli`)*

### Interactive Menu Features:
```
  1. dashboard        - Refresh & view live status
  2. add              - Commit to a new monthly goal (with SMART criteria)
  3. update           - Edit a goal title or criteria
  4. delete           - Remove a goal
  5. submit           - Submit proof/evidence for audit
  6. audit            - Trigger AI Judge cross-examination & verdict
  7. clear-penalty    - Mark completed penance task
  8. history          - View past penalty and audit logs
  9. remove-history   - Purge or remove penalty records
  10. advice          - AI Goal Feasibility & Criteria Coaching
  11. rollover        - Check calendar rollover & auto-audit past goals
  0. exit             - Quit Sentinel Agent
```

---

## ⚡ Direct CLI Subcommands (Non-Interactive)

You can also run any command directly from your terminal:

### 1. View Dashboard & Current Status
```bash
python -m goal_tracker.cli status
```

### 2. Commit to a New Goal
```bash
python -m goal_tracker.cli add "Ship SaaS MVP" --criteria "Deploy fullstack app to Fly.io with Stripe checkout and 10 passing tests"
```

### 3. Update Existing Goal
```bash
python -m goal_tracker.cli update 1 --title "New Title" --criteria "New Criteria"
```

### 4. Delete / Remove Goal
```bash
python -m goal_tracker.cli delete 1
```

### 5. Submit Proof / Evidence
```bash
python -m goal_tracker.cli submit 1 "Deployed live at https://app.example.com with 12 passing integration tests on 2026-09-27."
```

### 6. Trigger AI Evidence Audit
```bash
python -m goal_tracker.cli audit 1
```

### 7. Clear Penalty / Remove History
```bash
python -m goal_tracker.cli clear-penalty 1
python -m goal_tracker.cli remove-history --all
```

---

## ⚖️ Gamified Penalty & Escalation Model

| Strike | Penalty Severity | Consequence | Assigned Penance Example |
| :--- | :--- | :--- | :--- |
| **0 Strikes** | Light / Medium | -250 XP, Strike +1 | 40 strict pushups or 3-minute cold shower |
| **1 Strike** | Severe | -250 XP, Strike +2 | 36-hour digital dopamine detox or 5km run |
| **2 Strikes** | Catastrophic | -250 XP, Strike +3 | Code Red: 48h blackout + 200 pushups + confession letter |
| **3 Strikes** | **Discipline Bankruptcy** | All rewards locked | Full system freeze until all backlog penances cleared |

---

## 🧪 Automated Test Verification

Run the full pytest suite:

```bash
python -m pytest tests -v
```
All 10 unit and integration tests verify:
- Database CRUD and user profile leveling
- Evidence evaluation logic and heuristic parsing
- Anti-excuse vocabulary filtering
- XP and strike state transitions
- Monthly calendar rollover detection
- Multi-tier penalty escalation
