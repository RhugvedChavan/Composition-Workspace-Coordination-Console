from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from app.crud import create_document_version, get_document_or_404, log_activity
from app.database import get_session
from app.models import Comment, Document, DocumentStatus, DocumentVersion
from app.schemas import (
    CommentCreate,
    CommentRead,
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    DocumentVersionRead,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentRead, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    owner_id: Optional[int] = Form(default=None),
    session: Session = Depends(get_session),
):
    """Create a new document by browsing/uploading a local text file."""
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Only plain-text files (.txt, .md, etc.) can be uploaded as documents",
        )

    title = file.filename or "Uploaded document"
    document = Document(title=title, content=text, owner_id=owner_id)
    session.add(document)
    session.commit()
    session.refresh(document)

    create_document_version(session, document, owner_id)
    log_activity(
        session,
        action="document_uploaded",
        document_id=document.id,
        actor_id=owner_id,
        details=f"Uploaded '{title}'",
    )
    return document


@router.post("", response_model=DocumentRead, status_code=201)
def create_document(payload: DocumentCreate, session: Session = Depends(get_session)):
    document = Document(
        title=payload.title, content=payload.content, owner_id=payload.owner_id
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    # Snapshot version 1
    create_document_version(session, document, payload.owner_id)
    log_activity(
        session,
        action="document_created",
        document_id=document.id,
        actor_id=payload.owner_id,
        details=f"Created '{document.title}'",
    )
    return document


@router.get("", response_model=List[DocumentRead])
def list_documents(
    status: Optional[DocumentStatus] = Query(default=None),
    owner_id: Optional[int] = Query(default=None),
    session: Session = Depends(get_session),
):
    query = select(Document)
    if status is not None:
        query = query.where(Document.status == status)
    if owner_id is not None:
        query = query.where(Document.owner_id == owner_id)
    return session.exec(query.order_by(Document.updated_at.desc())).all()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, session: Session = Depends(get_session)):
    return get_document_or_404(session, document_id)


@router.put("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int, payload: DocumentUpdate, session: Session = Depends(get_session)
):
    from datetime import datetime

    document = get_document_or_404(session, document_id)
    content_changed = payload.content is not None and payload.content != document.content

    if payload.title is not None:
        document.title = payload.title
    if payload.status is not None:
        document.status = payload.status
    if content_changed:
        document.content = payload.content
        document.version += 1

    document.updated_at = datetime.utcnow()
    session.add(document)
    session.commit()
    session.refresh(document)

    if content_changed:
        create_document_version(session, document, payload.editor_id)
        log_activity(
            session,
            action="document_edited",
            document_id=document.id,
            actor_id=payload.editor_id,
            details=f"Updated to version {document.version}",
        )
    if payload.status is not None:
        log_activity(
            session,
            action="status_changed",
            document_id=document.id,
            actor_id=payload.editor_id,
            details=f"Status set to {payload.status.value}",
        )
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, session: Session = Depends(get_session)):
    document = get_document_or_404(session, document_id)
    session.delete(document)
    session.commit()
    return None


@router.get("/{document_id}/versions", response_model=List[DocumentVersionRead])
def list_versions(document_id: int, session: Session = Depends(get_session)):
    get_document_or_404(session, document_id)
    query = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    return session.exec(query).all()


@router.post("/{document_id}/versions/{version_number}/restore", response_model=DocumentRead)
def restore_version(
    document_id: int, version_number: int, session: Session = Depends(get_session)
):
    from datetime import datetime

    document = get_document_or_404(session, document_id)
    version = session.exec(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.version_number == version_number,
        )
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    document.content = version.content
    document.version += 1
    document.updated_at = datetime.utcnow()
    session.add(document)
    session.commit()
    session.refresh(document)

    create_document_version(session, document, version.author_id)
    log_activity(
        session,
        action="version_restored",
        document_id=document.id,
        details=f"Restored content from version {version_number}",
    )
    return document


# ---------- Comments ----------
@router.post("/{document_id}/comments", response_model=CommentRead, status_code=201)
def add_comment(
    document_id: int, payload: CommentCreate, session: Session = Depends(get_session)
):
    get_document_or_404(session, document_id)
    comment = Comment(
        document_id=document_id, author_id=payload.author_id, text=payload.text
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    log_activity(
        session,
        action="comment_added",
        document_id=document_id,
        actor_id=payload.author_id,
        details=payload.text[:80],
    )
    return comment


@router.get("/{document_id}/comments", response_model=List[CommentRead])
def list_comments(document_id: int, session: Session = Depends(get_session)):
    get_document_or_404(session, document_id)
    query = (
        select(Comment)
        .where(Comment.document_id == document_id)
        .order_by(Comment.created_at.desc())
    )
    return session.exec(query).all()


@router.patch("/comments/{comment_id}/resolve", response_model=CommentRead)
def resolve_comment(comment_id: int, session: Session = Depends(get_session)):
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.resolved = True
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment
