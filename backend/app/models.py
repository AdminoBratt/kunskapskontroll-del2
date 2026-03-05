from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class PdfDocument(Base):
    __tablename__ = "pdf_documents"

    document_id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    language = Column(Text, server_default="en")
    upload_date = Column(DateTime, server_default=func.now())
    pdf_data = Column(LargeBinary, nullable=False)

    category = relationship("Category")
    metadata_entries = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    metadata_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.document_id", ondelete="CASCADE"))
    key = Column(Text, nullable=False)
    value = Column(Text)

    document = relationship("PdfDocument", back_populates="metadata_entries")
