from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class DocumentStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    published = "published"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    role: str = Field(default="writer")  # writer, editor, coordinator, admin
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str = Field(default="")
    status: DocumentStatus = Field(default=DocumentStatus.draft)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    version_number: int
    content: str
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    text: str
    resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: Optional[int] = Field(default=None, foreign_key="document.id", index=True)
    assignee_id: Optional[int] = Field(default=None, foreign_key="user.id")
    title: str
    description: str = Field(default="")
    status: TaskStatus = Field(default=TaskStatus.todo)
    due_date: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ActivityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: Optional[int] = Field(default=None, foreign_key="document.id", index=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    action: str
    details: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
