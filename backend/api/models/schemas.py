"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from enum import Enum


class AccessLevel(str, Enum):
    GENERAL = "general"
    LEADERSHIP = "leadership"


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


# --- Ingestion ---

class TranscriptIngestRequest(BaseModel):
    transcript: str = Field(..., min_length=10, description="Raw meeting transcript text")
    meeting_name: str = Field(..., min_length=1, description="Name of the meeting")
    default_access_level: AccessLevel = AccessLevel.GENERAL


class DecisionOut(BaseModel):
    content: str
    participants: list[str] = []
    access_level: str = "general"
    confidence_score: float = 0.0


class TaskOut(BaseModel):
    description: str
    owner: str = ""
    deadline: str = ""
    status: str = "open"
    confidence_score: float = 0.0


class ExtractionResponse(BaseModel):
    meeting_id: str
    meeting_name: str
    status: str
    decisions: list[DecisionOut] = []
    tasks: list[TaskOut] = []
    error: str | None = None


# --- Review ---

class ApproveDecisionRequest(BaseModel):
    content: str
    access_level: AccessLevel = AccessLevel.GENERAL
    allowed_groups: list[str] = ["all"]
    participants: list[str] = []
    meeting_id: str
    meeting_name: str
    confidence_score: float = 0.0


class ApproveTaskRequest(BaseModel):
    description: str
    owner: str
    deadline: str = ""
    status: TaskStatus = TaskStatus.OPEN
    access_level: AccessLevel = AccessLevel.GENERAL
    allowed_groups: list[str] = ["all"]
    meeting_id: str
    meeting_name: str
    confidence_score: float = 0.0


class BatchApproveRequest(BaseModel):
    decision_ids: list[int] = []
    task_ids: list[int] = []


class EditItemRequest(BaseModel):
    new_content: str = Field(..., min_length=1)


# --- Query ---

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question")
    session_id: str = "default"


class SourceCitation(BaseModel):
    content: str
    item_type: str
    meeting_name: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitation] = []
    session_id: str = ""


# --- Health ---

class HealthResponse(BaseModel):
    status: str = "ok"
    environment: str
    version: str = "0.1.0"
