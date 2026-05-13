"""RAG indexing script — Stage 3.

Loads AbhiMart knowledge base docs, chunks them, embeds them using
Google's embedding model, and stores them in pgvector.

Run with:
    uv run python -m app.rag.ingest

This is an offline script — run it once, or whenever docs change.
It is never called during a user request.
"""

import asyncio
from pathlib import Path

import structlog
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

import os
os.environ["GOOGLE_API_KEY"] = get_settings().GEMINI_API_KEY

logger = structlog.get_logger()

settings = get_settings()

# --- Constants ---
DOCS_DIR = Path(__file__).parent / "docs"
COLLECTION_NAME = "abhimart_knowledge_base"
EMBEDDING_DIMENSIONS = 768  # reduced from default 3072 — faster search, less storage

# --- Embedding model ---
# Uses RETRIEVAL_DOCUMENT task type automatically when embedding docs
# Uses RETRIEVAL_QUERY task type automatically when embedding queries at retrieval time
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    output_dimensionality=EMBEDDING_DIMENSIONS,
)

# --- PGVector connection ---
# postgresql+psycopg:// tells SQLAlchemy to use the psycopg3 driver
# PGVector requires psycopg3 — it doesn't work with asyncpg
pgvector_url = settings.CHECKPOINT_DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg://"
)


def get_vector_store() -> PGVector:
    """Return a PGVector instance connected to our Postgres."""
    return PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=pgvector_url,
        use_jsonb=True,  # enables rich metadata filtering ($eq, $in, $between etc)
    )


def load_and_chunk_docs() -> list:
    """Load all markdown files and split into chunks.

    Returns a flat list of Document objects — one per chunk.
    Each chunk carries metadata about which file and section it came from.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # characters per chunk
        chunk_overlap=100,  # overlap between chunks to preserve context at boundaries
        separators=["\n\n", "\n", " ", ""],  # try paragraph breaks first
    )

    all_chunks = []

    for doc_path in sorted(DOCS_DIR.glob("*.md")):
        loader = TextLoader(str(doc_path), encoding="utf-8")
        docs = loader.load()

        # Enrich metadata before splitting — so every chunk knows its source
        for doc in docs:
            doc.metadata["source"] = doc_path.name
            doc.metadata["category"] = doc_path.stem  # e.g. "return-policy"

        chunks = splitter.split_documents(docs)

        logger.info(
            "Chunked document",
            file=doc_path.name,
            chunks=len(chunks),
        )
        all_chunks.extend(chunks)

    return all_chunks


def ingest():
    """Main indexing function."""
    logger.info("Starting RAG ingestion", docs_dir=str(DOCS_DIR))

    # Load and chunk all docs
    chunks = load_and_chunk_docs()
    logger.info("Total chunks to index", count=len(chunks))

    # Connect to pgvector and index
    # PGVector.from_documents() creates the table if it doesn't exist,
    # embeds every chunk, and stores them — all in one call
    vector_store = PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        connection=pgvector_url,
        use_jsonb=True,
        pre_delete_collection=True,  # wipe existing vectors before re-indexing
        # makes the script idempotent — safe to re-run
    )

    logger.info(
        "Ingestion complete",
        chunks_indexed=len(chunks),
        collection=COLLECTION_NAME,
    )


if __name__ == "__main__":
    ingest()
