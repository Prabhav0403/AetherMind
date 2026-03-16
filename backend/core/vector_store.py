"""
Vector store abstraction supporting ChromaDB and FAISS backends.
Handles embedding generation and semantic similarity search.
"""

import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Embedding Factory
# ─────────────────────────────────────────────────────────────

def get_embedding_function():
    """Factory for embedding models."""
    if settings.EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    else:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )


# ─────────────────────────────────────────────────────────────
# Vector Store
# ─────────────────────────────────────────────────────────────

class VectorStore:
    """Unified vector store interface supporting multiple backends."""

    def __init__(self):
        self.embeddings = get_embedding_function()
        self.backend = settings.VECTOR_DB
        self._store = None
        self._collection_name = "agentic_rag_knowledge"
        self._initialize()

    # ─────────────────────────────────────────────────────────

    def _initialize(self):
        """Initialize the chosen vector database."""
        if self.backend == "chromadb":
            self._init_chroma()
        elif self.backend == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"Unsupported vector DB: {self.backend}")

    # ─────────────────────────────────────────────────────────
    # ChromaDB
    # ─────────────────────────────────────────────────────────

    def _init_chroma(self):
        """Initialize ChromaDB."""
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        try:
            self._store = client.get_collection(self._collection_name)
        except Exception:
            self._store = client.create_collection(
                self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        self._chroma_client = client
        logger.info(f"ChromaDB initialized: {settings.CHROMA_PERSIST_DIR}")

    # ─────────────────────────────────────────────────────────
    # FAISS
    # ─────────────────────────────────────────────────────────

    def _init_faiss(self):
        """Initialize FAISS index."""
        import faiss
        import json

        self._faiss_index_path = os.path.join(settings.FAISS_INDEX_PATH, "index.faiss")
        self._faiss_meta_path = os.path.join(settings.FAISS_INDEX_PATH, "metadata.json")
        self._faiss_docs: List[Dict] = []

        if os.path.exists(self._faiss_index_path):
            self._store = faiss.read_index(self._faiss_index_path)

            with open(self._faiss_meta_path) as f:
                self._faiss_docs = json.load(f)
        else:
            self._store = faiss.IndexFlatIP(settings.EMBEDDING_DIMENSION)

        logger.info(f"FAISS initialized: {settings.FAISS_INDEX_PATH}")

    # ─────────────────────────────────────────────────────────
    # Add Documents
    # ─────────────────────────────────────────────────────────

    async def add_documents(self, chunks: List[Dict[str, Any]]) -> int:
        """Add document chunks to the vector store."""
        if not chunks:
            return 0

        texts = [c["content"] for c in chunks]
        embeddings = self.embeddings.embed_documents(texts)

        if self.backend == "chromadb":
            return self._add_chroma(chunks, embeddings)

        elif self.backend == "faiss":
            return self._add_faiss(chunks, embeddings)

    # ─────────────────────────────────────────────────────────

    def _add_chroma(self, chunks: List[Dict], embeddings: List[List[float]]) -> int:
        """Add to ChromaDB."""

        ids = [c.get("chunk_id", str(uuid.uuid4())) for c in chunks]
        documents = [c["content"] for c in chunks]

        # FIXED: store numeric metadata instead of strings
        metadatas = [
            {
                "source": c.get("source", ""),
                "doc_id": c.get("doc_id", ""),
                "page_number": c.get("page_number") or 0,
                "chunk_index": c.get("chunk_index", 0),
            }
            for c in chunks
        ]

        self._store.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    # ─────────────────────────────────────────────────────────

    def _add_faiss(self, chunks: List[Dict], embeddings: List[List[float]]) -> int:
        """Add to FAISS index."""
        import numpy as np
        import faiss
        import json

        arr = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(arr)

        self._store.add(arr)
        self._faiss_docs.extend(chunks)

        faiss.write_index(self._store, self._faiss_index_path)

        with open(self._faiss_meta_path, "w") as f:
            json.dump(self._faiss_docs, f)

        return len(chunks)

    # ─────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────

    async def similarity_search(
        self,
        query: str,
        k: int = 8,
        filter_doc_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Perform semantic similarity search."""

        query_embedding = self.embeddings.embed_query(query)

        if self.backend == "chromadb":
            return self._search_chroma(query_embedding, k, filter_doc_ids)

        elif self.backend == "faiss":
            return self._search_faiss(query_embedding, k, filter_doc_ids)

    # ─────────────────────────────────────────────────────────

    def _safe_int(self, value):
        """Safely convert value to int."""
        try:
            if value in [None, "", "None"]:
                return 0
            return int(value)
        except Exception:
            return 0

    # ─────────────────────────────────────────────────────────

    def _search_chroma(
        self,
        query_embedding: List[float],
        k: int,
        filter_doc_ids: Optional[List[str]],
    ) -> List[Dict]:

        where = None
        if filter_doc_ids:
            where = {"doc_id": {"$in": filter_doc_ids}}

        results = self._store.query(
            query_embeddings=[query_embedding],
            n_results=min(k, max(self._store.count(), 1)),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []

        if results["documents"] and results["documents"][0]:

            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):

                score = 1.0 - float(dist)

                page_number = self._safe_int(meta.get("page_number"))

                chunks.append(
                    {
                        "content": doc,
                        "source": meta.get("source", "Unknown"),
                        "doc_id": meta.get("doc_id", ""),
                        "chunk_id": str(uuid.uuid4()),
                        "page_number": page_number,
                        "metadata": meta,
                        "score": score,
                    }
                )

        return chunks

    # ─────────────────────────────────────────────────────────

    def _search_faiss(
        self,
        query_embedding: List[float],
        k: int,
        filter_doc_ids: Optional[List[str]],
    ) -> List[Dict]:

        import numpy as np
        import faiss

        if self._store.ntotal == 0:
            return []

        arr = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(arr)

        k = min(k, self._store.ntotal)

        scores, indices = self._store.search(arr, k)

        results = []

        for score, idx in zip(scores[0], indices[0]):

            if idx < 0 or idx >= len(self._faiss_docs):
                continue

            doc = self._faiss_docs[idx]

            if filter_doc_ids and doc.get("doc_id") not in filter_doc_ids:
                continue

            results.append(
                {
                    **doc,
                    "score": float(score),
                }
            )

        return results

    # ─────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────

    def get_document_count(self) -> int:
        """Return total number of indexed chunks."""

        if self.backend == "chromadb":
            return self._store.count()

        elif self.backend == "faiss":
            return self._store.ntotal

        return 0

    # ─────────────────────────────────────────────────────────

    async def delete_document(self, doc_id: str) -> int:
        """Delete all chunks belonging to a document."""

        if self.backend == "chromadb":

            results = self._store.get(where={"doc_id": doc_id})

            if results["ids"]:
                self._store.delete(ids=results["ids"])
                return len(results["ids"])

        return 0