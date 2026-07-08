"""Pydantic v2 request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import DocumentStatus, TaskStatus


# ---------- User ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str = "writer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    created_at: datetime


# ---------- Document ----------
class DocumentCreate(BaseModel):
    title: str
    content: str = ""
    owner_id: Optional[int] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[DocumentStatus] = None
    editor_id: Optional[int] = None  # who made this edit, for versioning/activity log


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    status: DocumentStatus
    owner_id: Optional[int]
    version: int
    created_at: datetime
    updated_at: datetime


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    version_number: int
    content: str
    author_id: Optional[int]
    created_at: datetime


# ---------- Comment ----------
class CommentCreate(BaseModel):
    author_id: Optional[int] = None
    text: str


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    author_id: Optional[int]
    text: str
    resolved: bool
    created_at: datetime


# ---------- Task ----------
class TaskCreate(BaseModel):
    document_id: Optional[int] = None
    assignee_id: Optional[int] = None
    title: str
    description: str = ""
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: Optional[int]
    assignee_id: Optional[int]
    title: str
    description: str
    status: TaskStatus
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ---------- Activity ----------
class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: Optional[int]
    actor_id: Optional[int]
    action: str
    details: str
    timestamp: datetime


# ---------- Dashboard ----------
class DashboardSummary(BaseModel):
    total_documents: int
    documents_by_status: dict[str, int]
    total_tasks: int
    tasks_by_status: dict[str, int]
    overdue_tasks: int
    total_users: int
    recent_activity: list[ActivityRead]
