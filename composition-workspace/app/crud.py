from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    ActivityLog,
    Comment,
    Document,
    DocumentVersion,
    Task,
    User,
)


def log_activity(
    session: Session,
    action: str,
    document_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    details: str = "",
) -> ActivityLog:
    entry = ActivityLog(
        document_id=document_id, actor_id=actor_id, action=action, details=details
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def get_document_or_404(session: Session, document_id: int) -> Document:
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return document


def get_task_or_404(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


def get_user_or_404(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def create_document_version(
    session: Session, document: Document, author_id: Optional[int]
) -> DocumentVersion:
    """Snapshot the current document content as a new version row."""
    version = DocumentVersion(
        document_id=document.id,
        version_number=document.version,
        content=document.content,
        author_id=author_id,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version
