from sqlmodel import SQLModel, Session, create_engine
DATABASE_URL = "sqlite:///./composition_workspace.db"

connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create all tables if they don't already exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a DB session."""
    with Session(engine) as session:
        yield session
