import os
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    CheckConstraint,
    func,
    Index,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# -----------------------------------
# Load environment variables
# -----------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./metadata.db")

# -----------------------------------
# Database Setup
# -----------------------------------
engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# -----------------------------------
# Enum-like class for statuses
# -----------------------------------
class IngestionStatus:
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# -----------------------------------
# URL Metadata Model
# -----------------------------------
class URLMetadata(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default=IngestionStatus.pending)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"status IN ('{IngestionStatus.pending}', '{IngestionStatus.processing}', '{IngestionStatus.completed}', '{IngestionStatus.failed}')",
            name="check_status_valid",
        ),
        Index("idx_status", "status"),
        Index("idx_url", "url"),
    )


# -----------------------------------
# Create tables if not exist
# -----------------------------------
def init_db():
    Base.metadata.create_all(bind=engine)
