"""
Document ingestion pipeline: Extract text → chunk → embed → store.
Supports PDF, TXT, HTML, Markdown, and DOCX formats.
"""
import os
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from config import settings
from models.schemas import DocumentInfo, DocumentStatus

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document ingestion, chunking, and indexing."""

    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.documents: Dict[str, DocumentInfo] = {}

    def set_vector_store(self, vector_store):
        self.vector_store = vector_store

    async def process_file(self, file_path: str, filename: str,
                            doc_id: Optional[str] = None) -> DocumentInfo:
        """Full ingestion pipeline for a single file."""
        doc_id = doc_id or str(uuid.uuid4())
        file_size = os.path.getsize(file_path)
        ext = Path(filename).suffix.lower()

        doc_info = DocumentInfo(
            doc_id=doc_id,
            filename=filename,
            file_type=ext,
            file_size=file_size,
            status=DocumentStatus.PROCESSING,
        )
        self.documents[doc_id] = doc_info

        try:
            # Step 1: Extract text
            text_blocks = await self._extract_text(file_path, ext)

            if not text_blocks:
                raise ValueError(f"No text extracted from {filename}")

            # Step 2: Chunk text
            chunks = self._chunk_text_blocks(text_blocks, doc_id, filename)

            # Step 3: Index to vector store
            if self.vector_store and chunks:
                await self.vector_store.add_documents(chunks)

            doc_info.chunk_count = len(chunks)
            doc_info.status = DocumentStatus.INDEXED
            doc_info.indexed_at = datetime.utcnow()

            logger.info(f"Processed {filename}: {len(chunks)} chunks indexed")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}", exc_info=True)
            doc_info.status = DocumentStatus.FAILED
            doc_info.error = str(e)

        return doc_info

    async def _extract_text(self, file_path: str,
                             ext: str) -> List[Dict[str, Any]]:
        """Extract text blocks with page/section metadata."""
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext in [".txt", ".md"]:
            return self._extract_text_file(file_path)
        elif ext in [".html", ".htm"]:
            return self._extract_html(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, path: str) -> List[Dict[str, Any]]:
        """Extract text from PDF with page numbers."""
        from pypdf import PdfReader

        reader = PdfReader(path)
        blocks = []
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                blocks.append({
                    "text": text.strip(),
                    "page_number": page_num,
                    "section": f"Page {page_num}",
                })
        return blocks

    def _extract_text_file(self, path: str) -> List[Dict[str, Any]]:
        """Extract from plain text or Markdown."""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Split into logical sections by blank lines
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        return [{"text": p, "page_number": None, "section": f"Part {i+1}"}
                for i, p in enumerate(paragraphs)]

    def _extract_html(self, path: str) -> List[Dict[str, Any]]:
        """Extract from HTML, stripping tags."""
        from bs4 import BeautifulSoup

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract text blocks by major structural elements
        blocks = []
        for i, elem in enumerate(soup.find_all(["p", "article", "section", "div"])):
            text = elem.get_text(separator=" ", strip=True)
            if len(text) > 50:  # Skip very short fragments
                blocks.append({
                    "text": text,
                    "page_number": None,
                    "section": f"Section {i+1}",
                })
        return blocks

    def _extract_docx(self, path: str) -> List[Dict[str, Any]]:
        """Extract from DOCX."""
        from docx import Document

        doc = Document(path)
        blocks = []
        current_section = []
        section_num = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                if current_section:
                    blocks.append({
                        "text": " ".join(current_section),
                        "page_number": None,
                        "section": f"Section {section_num}",
                    })
                    current_section = []
                    section_num += 1
            else:
                current_section.append(text)

        if current_section:
            blocks.append({
                "text": " ".join(current_section),
                "page_number": None,
                "section": f"Section {section_num}",
            })
        return blocks

    def _chunk_text_blocks(self, blocks: List[Dict[str, Any]],
                            doc_id: str, filename: str) -> List[Dict[str, Any]]:
        """Split text blocks into overlapping chunks."""
        chunks = []
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        chunk_index = 0

        for block in blocks:
            text = block["text"]
            words = text.split()

            if len(words) <= chunk_size:
                # Block fits in a single chunk
                if len(words) > 10:  # Skip trivially short chunks
                    chunk_id = self._generate_chunk_id(doc_id, chunk_index)
                    chunks.append({
                        "chunk_id": chunk_id,
                        "doc_id": doc_id,
                        "content": text,
                        "source": filename,
                        "page_number": block.get("page_number"),
                        "section": block.get("section", ""),
                        "chunk_index": chunk_index,
                        "metadata": {
                            "doc_id": doc_id,
                            "filename": filename,
                            "page": block.get("page_number"),
                        }
                    })
                    chunk_index += 1
            else:
                # Sliding window chunking
                start = 0
                while start < len(words):
                    end = min(start + chunk_size, len(words))
                    chunk_words = words[start:end]
                    if len(chunk_words) > 10:
                        chunk_id = self._generate_chunk_id(doc_id, chunk_index)
                        chunks.append({
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "content": " ".join(chunk_words),
                            "source": filename,
                            "page_number": block.get("page_number"),
                            "section": block.get("section", ""),
                            "chunk_index": chunk_index,
                            "metadata": {
                                "doc_id": doc_id,
                                "filename": filename,
                                "page": block.get("page_number"),
                            }
                        })
                        chunk_index += 1
                    start += chunk_size - overlap

        return chunks[:settings.MAX_CHUNKS_PER_DOC]

    def _generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        """Generate a deterministic chunk ID."""
        return hashlib.md5(f"{doc_id}_{chunk_index}".encode()).hexdigest()

    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        return self.documents.get(doc_id)

    def list_documents(self) -> List[DocumentInfo]:
        return list(self.documents.values())
