import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from goal_tracker.models import Goal, GoalStatus, Penalty, UserProfile

DB_FILE = os.path.join(os.path.expanduser("~"), ".goal_tracker.db")

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # User profile table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 1000,
                level INTEGER NOT NULL DEFAULT 1,
                strikes INTEGER NOT NULL DEFAULT 0,
                max_strikes INTEGER NOT NULL DEFAULT 3,
                current_month TEXT NOT NULL,
                last_evaluated_month TEXT
            )
            """)
            
            # Goals table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                title TEXT NOT NULL,
                target_criteria TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                evidence TEXT,
                evidence_submitted_at TEXT,
                ai_feedback TEXT,
                completed_at TEXT
            )
            """)
            
            # Penalties ledger table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS penalties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                goal_title TEXT NOT NULL,
                month TEXT NOT NULL,
                xp_lost INTEGER NOT NULL,
                strike_increment INTEGER NOT NULL,
                roast TEXT NOT NULL,
                penalty_task TEXT NOT NULL,
                is_cleared INTEGER NOT NULL DEFAULT 0,
                cleared_at TEXT,
                created_at TEXT NOT NULL
            )
            """)
            
            # Seed profile if not exists
            cursor.execute("SELECT COUNT(*) FROM profile")
            if cursor.fetchone()[0] == 0:
                now_month = datetime.now().strftime("%Y-%m")
                cursor.execute("""
                INSERT INTO profile (id, username, xp, level, strikes, max_strikes, current_month)
                VALUES (1, 'Commander', 1000, 1, 0, 3, ?)
                """, (now_month,))
            
            conn.commit()

    def get_profile(self) -> UserProfile:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profile WHERE id = 1")
            row = cursor.fetchone()
            if not row:
                raise ValueError("Profile not found")
            return UserProfile(
                id=row["id"],
                username=row["username"],
                xp=row["xp"],
                level=row["level"],
                strikes=row["strikes"],
                max_strikes=row["max_strikes"],
                current_month=row["current_month"],
                last_evaluated_month=row["last_evaluated_month"]
            )

    def update_profile(self, xp: int, strikes: int, current_month: Optional[str] = None, last_evaluated_month: Optional[str] = None):
        # Calculate level based on XP (1000 XP per level, Level 1 at 1000)
        level = max(1, xp // 1000)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if current_month and last_evaluated_month:
                cursor.execute("""
                UPDATE profile 
                SET xp = ?, level = ?, strikes = ?, current_month = ?, last_evaluated_month = ?
                WHERE id = 1
                """, (xp, level, strikes, current_month, last_evaluated_month))
            elif current_month:
                cursor.execute("""
                UPDATE profile 
                SET xp = ?, level = ?, strikes = ?, current_month = ?
                WHERE id = 1
                """, (xp, level, strikes, current_month))
            else:
                cursor.execute("""
                UPDATE profile 
                SET xp = ?, level = ?, strikes = ?
                WHERE id = 1
                """, (xp, level, strikes))
            conn.commit()

    def add_goal(self, title: str, target_criteria: str, month: Optional[str] = None) -> Goal:
        if not month:
            month = datetime.now().strftime("%Y-%m")
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO goals (month, title, target_criteria, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (month, title, target_criteria, GoalStatus.PENDING.value, now_str))
            goal_id = cursor.lastrowid
            conn.commit()
            return self.get_goal(goal_id)

    def get_goal(self, goal_id: int) -> Optional[Goal]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_goal(row)

    def get_goals_by_month(self, month: str) -> List[Goal]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals WHERE month = ? ORDER BY id ASC", (month,))
            rows = cursor.fetchall()
            return [self._row_to_goal(r) for r in rows]

    def get_all_goals(self) -> List[Goal]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals ORDER BY month DESC, id ASC")
            rows = cursor.fetchall()
            return [self._row_to_goal(r) for r in rows]

    def submit_evidence(self, goal_id: int, evidence: str) -> Goal:
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE goals 
            SET evidence = ?, evidence_submitted_at = ?, status = ?
            WHERE id = ?
            """, (evidence, now_str, GoalStatus.EVIDENCE_SUBMITTED.value, goal_id))
            conn.commit()
            return self.get_goal(goal_id)

    def update_goal_status(self, goal_id: int, status: GoalStatus, ai_feedback: str, completed: bool = False):
        completed_at = datetime.now().isoformat() if completed else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE goals 
            SET status = ?, ai_feedback = ?, completed_at = ?
            WHERE id = ?
            """, (status.value, ai_feedback, completed_at, goal_id))
            conn.commit()

    def record_penalty(self, goal_id: int, goal_title: str, month: str, xp_lost: int, strike_increment: int, roast: str, penalty_task: str) -> Penalty:
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO penalties (goal_id, goal_title, month, xp_lost, strike_increment, roast, penalty_task, is_cleared, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (goal_id, goal_title, month, xp_lost, strike_increment, roast, penalty_task, now_str))
            pen_id = cursor.lastrowid
            conn.commit()
            return self.get_penalty(pen_id)

    def get_penalty(self, penalty_id: int) -> Optional[Penalty]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM penalties WHERE id = ?", (penalty_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_penalty(row)

    def get_uncleared_penalties(self) -> List[Penalty]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM penalties WHERE is_cleared = 0 ORDER BY id ASC")
            return [self._row_to_penalty(r) for r in cursor.fetchall()]

    def get_all_penalties(self) -> List[Penalty]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM penalties ORDER BY id DESC")
            return [self._row_to_penalty(r) for r in cursor.fetchall()]

    def clear_penalty(self, penalty_id: int):
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE penalties SET is_cleared = 1, cleared_at = ? WHERE id = ?", (now_str, penalty_id))
            conn.commit()

    def update_goal(self, goal_id: int, title: Optional[str] = None, target_criteria: Optional[str] = None) -> Optional[Goal]:
        goal = self.get_goal(goal_id)
        if not goal:
            return None
        new_title = title if title is not None else goal.title
        new_criteria = target_criteria if target_criteria is not None else goal.target_criteria
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE goals 
            SET title = ?, target_criteria = ?
            WHERE id = ?
            """, (new_title, new_criteria, goal_id))
            conn.commit()
        return self.get_goal(goal_id)

    def delete_goal(self, goal_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            deleted = cursor.rowcount > 0
            # Also clean up associated penalties if desired
            cursor.execute("DELETE FROM penalties WHERE goal_id = ?", (goal_id,))
            conn.commit()
            return deleted

    def delete_penalty(self, penalty_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM penalties WHERE id = ?", (penalty_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def clear_penalty_history(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM penalties")
            count = cursor.rowcount
            conn.commit()
            return count

    def _row_to_goal(self, row) -> Goal:
        return Goal(
            id=row["id"],
            month=row["month"],
            title=row["title"],
            target_criteria=row["target_criteria"],
            status=GoalStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            evidence=row["evidence"],
            evidence_submitted_at=datetime.fromisoformat(row["evidence_submitted_at"]) if row["evidence_submitted_at"] else None,
            ai_feedback=row["ai_feedback"],
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
        )

    def _row_to_penalty(self, row) -> Penalty:
        return Penalty(
            id=row["id"],
            goal_id=row["goal_id"],
            goal_title=row["goal_title"],
            month=row["month"],
            xp_lost=row["xp_lost"],
            strike_increment=row["strike_increment"],
            roast=row["roast"],
            penalty_task=row["penalty_task"],
            is_cleared=bool(row["is_cleared"]),
            cleared_at=datetime.fromisoformat(row["cleared_at"]) if row["cleared_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"])
        )
