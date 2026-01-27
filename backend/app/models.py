from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
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
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    metadata_entries = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    metadata_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.document_id", ondelete="CASCADE"))
    key = Column(Text, nullable=False)
    value = Column(Text)

    document = relationship("PdfDocument", back_populates="metadata_entries")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.document_id", ondelete="CASCADE"))
    page_number = Column(Integer)
    chunk_index = Column(Integer)
    chunk_text = Column(Text, nullable=False)

    document = relationship("PdfDocument", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    chunk_id = Column(Integer, ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), primary_key=True)
    embedding = Column(Vector(768))

    chunk = relationship("DocumentChunk", back_populates="embedding")
