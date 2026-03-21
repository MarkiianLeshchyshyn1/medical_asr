from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import DATABASE_URL


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    audio_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    document_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    output_format: Mapped[str] = mapped_column(String(10), nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
