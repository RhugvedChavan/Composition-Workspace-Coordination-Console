"""Coordination Console endpoints: task assignment & tracking."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.crud import get_task_or_404, log_activity
from app.database import get_session
from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["coordination"])


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, session: Session = Depends(get_session)):
    task = Task(
        document_id=payload.document_id,
        assignee_id=payload.assignee_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    log_activity(
        session,
        action="task_created",
        document_id=payload.document_id,
        actor_id=payload.assignee_id,
        details=f"Task '{task.title}' created",
    )
    return task


@router.get("", response_model=List[TaskRead])
def list_tasks(
    status: Optional[TaskStatus] = Query(default=None),
    assignee_id: Optional[int] = Query(default=None),
    document_id: Optional[int] = Query(default=None),
    session: Session = Depends(get_session),
):
    query = select(Task)
    if status is not None:
        query = query.where(Task.status == status)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    if document_id is not None:
        query = query.where(Task.document_id == document_id)
    return session.exec(query.order_by(Task.due_date)).all()


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)):
    return get_task_or_404(session, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, session: Session = Depends(get_session)):
    task = get_task_or_404(session, task_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)

    if "status" in data:
        log_activity(
            session,
            action="task_status_changed",
            document_id=task.document_id,
            actor_id=task.assignee_id,
            details=f"Task '{task.title}' -> {task.status.value}",
        )
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = get_task_or_404(session, task_id)
    session.delete(task)
    session.commit()
    return None
