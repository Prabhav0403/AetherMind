"""
Configuration management for the Agentic RAG system.
"""
from pydantic_settings import BaseSettings
from typing import Literal, Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Agentic RAG Research Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM Provider
    LLM_PROVIDER: Literal["openai", "anthropic", "ollama", "groq", "cerebras"] = "groq"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Groq (free tier — https://console.groq.com)
    GROQ_API_KEY: Optional[str] = None
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"    # Planner + Researcher (speed)
    GROQ_SMART_MODEL: str = "llama-3.1-8b-instant" # Analyst + Writer (quality)

    # Cerebras (free tier — https://cloud.cerebras.ai)
    CEREBRAS_API_KEY: Optional[str] = None
    CEREBRAS_FAST_MODEL: str = "llama3.1-8b"          # Planner + Researcher
    CEREBRAS_SMART_MODEL: str = "llama3.1-8b"        # Analyst + Writer

    # Per-agent model overrides (auto-set based on provider if left as "auto")
    PLANNER_MODEL: str = "auto"
    RESEARCHER_MODEL: str = "auto"
    ANALYST_MODEL: str = "auto"
    WRITER_MODEL: str = "auto"

    # Legacy single-model fields (used when provider is openai/anthropic)
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_FAST_MODEL: str = "claude-3-5-haiku-20241022"
    ANTHROPIC_SMART_MODEL: str = "claude-3-5-sonnet-20241022"

    # Vector Database
    VECTOR_DB: Literal["chromadb", "faiss"] = "chromadb"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    FAISS_INDEX_PATH: str = "./data/faiss"

    # Embeddings
    EMBEDDING_PROVIDER: Literal["openai", "sentence_transformers"] = "sentence_transformers"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 384

    # Document Processing
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MAX_CHUNKS_PER_DOC: int = 500

    # RAG Pipeline
    TOP_K_RETRIEVAL: int = 8
    RERANK_TOP_K: int = 5
    MIN_RELEVANCE_SCORE: float = 0.3

    # Agent Iteration Control
    MAX_ITERATIONS: int = 5
    COVERAGE_THRESHOLD: float = 0.75
    ANALYST_CONFIDENCE_THRESHOLD: float = 0.85
    MIN_EVIDENCE_PIECES: int = 5

    # File Upload
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".txt", ".html", ".md", ".docx"]

    # Storage
    REPORTS_DIR: str = "./data/reports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
for directory in [
    settings.CHROMA_PERSIST_DIR,
    settings.UPLOAD_DIR,
    settings.REPORTS_DIR,
    settings.FAISS_INDEX_PATH,
]:
    os.makedirs(directory, exist_ok=True)
