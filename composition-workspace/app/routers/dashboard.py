"""Coordination Console dashboard: aggregated stats & activity feed."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import ActivityLog, Document, DocumentStatus, Task, TaskStatus, User
from app.schemas import ActivityRead, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(session: Session = Depends(get_session)):
    total_documents = session.exec(select(func.count()).select_from(Document)).one()
    total_tasks = session.exec(select(func.count()).select_from(Task)).one()
    total_users = session.exec(select(func.count()).select_from(User)).one()

    documents_by_status = {}
    for status in DocumentStatus:
        count = session.exec(
            select(func.count()).select_from(Document).where(Document.status == status)
        ).one()
        documents_by_status[status.value] = count

    tasks_by_status = {}
    for status in TaskStatus:
        count = session.exec(
            select(func.count()).select_from(Task).where(Task.status == status)
        ).one()
        tasks_by_status[status.value] = count

    overdue_tasks = session.exec(
        select(func.count())
        .select_from(Task)
        .where(Task.due_date.is_not(None))
        .where(Task.due_date < datetime.utcnow())
        .where(Task.status != TaskStatus.done)
    ).one()

    recent_activity = session.exec(
        select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(15)
    ).all()

    return DashboardSummary(
        total_documents=total_documents,
        documents_by_status=documents_by_status,
        total_tasks=total_tasks,
        tasks_by_status=tasks_by_status,
        overdue_tasks=overdue_tasks,
        total_users=total_users,
        recent_activity=recent_activity,
    )


@router.get("/activity", response_model=List[ActivityRead])
def dashboard_activity(
    limit: int = Query(default=50, le=200), session: Session = Depends(get_session)
):
    query = select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit)
    return session.exec(query).all()
