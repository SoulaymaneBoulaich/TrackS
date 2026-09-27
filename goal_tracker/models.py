from datetime import datetime, date
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class GoalStatus(str, Enum):
    PENDING = "PENDING"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    VERIFIED_COMPLETED = "VERIFIED_COMPLETED"
    FAILED_PENALIZED = "FAILED_PENALIZED"

class PenaltySeverity(str, Enum):
    LIGHT = "LIGHT"
    MEDIUM = "MEDIUM"
    SEVERE = "SEVERE"
    CATASTROPHIC = "CATASTROPHIC"

class Goal(BaseModel):
    id: Optional[int] = None
    month: str  # YYYY-MM
    title: str
    target_criteria: str
    status: GoalStatus = GoalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    evidence: Optional[str] = None
    evidence_submitted_at: Optional[datetime] = None
    ai_feedback: Optional[str] = None
    completed_at: Optional[datetime] = None

class Penalty(BaseModel):
    id: Optional[int] = None
    goal_id: int
    goal_title: str
    month: str
    xp_lost: int
    strike_increment: int
    roast: str
    penalty_task: str
    is_cleared: bool = False
    cleared_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

class UserProfile(BaseModel):
    id: int = 1
    username: str = "Commander"
    xp: int = 1000
    level: int = 1
    strikes: int = 0
    max_strikes: int = 3
    current_month: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m"))
    last_evaluated_month: Optional[str] = None

class AuditDecision(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    verdict_summary: str
    feedback: str
    assigned_penalty: Optional[str] = None
    roast: Optional[str] = None
    xp_delta: int
    strike_delta: int
