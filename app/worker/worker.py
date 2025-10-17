"""
Worker module for processing URL ingestion jobs
Run with: rq worker ingestion_queue
"""

import os
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# Monkey patch for NumPy 2.0 compatibility
import numpy as np

if not hasattr(np, "float_"):
    np.float_ = np.float64

import google.generativeai as genai
from app.db.vector import get_collection
from app.db.metadata import SessionLocal, URLMetadata, IngestionStatus


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize ChromaDB
collection = get_collection()


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False


def scrape_url(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.Timeout:
        raise ValueError("Request timeout after 30 seconds")
    except requests.ConnectionError:
        raise ValueError("Failed to connect to URL")
    except requests.HTTPError as e:
        raise ValueError(f"HTTP {response.status_code}: {response.reason}")
    except Exception as e:
        raise ValueError(f"Failed to scrape URL: {str(e)}")

    soup = BeautifulSoup(response.content, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Get text
    text = soup.get_text(separator=" ", strip=True)

    if not text:
        raise ValueError("No extractable text content found")

    return text


def clean_text(text: str) -> str:
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove special characters but keep basic punctuation
    # text = re.sub(r"[^\w\s.,!?;:\-\(\)]", "", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    # Here text represents a list of text chunks.
    model = "models/text-embedding-004"
    embeddings = []
    for idx, text in enumerate(texts):
        try:
            result = genai.embed_content(
                model=model, content=text, task_type="retrieval_document"
            )
            # api response is a disctionary with "embedding" key
            embedding = result["embedding"]

            # Verify embedding dimensions
            # if len(embedding) != 1536:
            #     logger.warning(
            #         f"Chunk {idx}: Expected 1536 dimensions, got {len(embedding)}"
            #     )

            embeddings.append(embedding)
            logger.info(f"Generated embedding for chunk {idx} ({len(embedding)} dims)")

        except Exception as e:
            logger.error(f"Error generating embedding for chunk {idx}: {str(e)}")
            raise ValueError(f"Failed to generate embedding: {str(e)}")

    logger.info(
        f"🆗Total {len(embeddings)} embeddings successfully generated for {len(texts)} chunks"
    )
    # returning the list of list;
    return embeddings


def process_url(url_id: int):
    db = SessionLocal()
    metadata = None

    try:
        # 1. Get metadata record
        metadata = db.query(URLMetadata).filter(URLMetadata.id == url_id).first()
        if not metadata:
            raise ValueError(f"URL metadata with id {url_id} not found")

        logger.info(f"[{url_id}]🔃 Processing URL: {metadata.url}")

        # 2. Validate URL format
        if not is_valid_url(metadata.url):
            raise ValueError(f"Invalid URL format: {metadata.url}")

        # 3. Update status to processing
        metadata.status = IngestionStatus.processing
        metadata.updated_at = datetime.utcnow()
        db.commit()

        # 4. Scrape content
        logger.info(f"[{url_id}]🔃 Scraping content...")
        raw_text = scrape_url(metadata.url)

        # 5. Clean text
        logger.info(f"[{url_id}]🔃 Cleaning text...")
        cleaned_text = clean_text(raw_text)

        if len(cleaned_text) < 100:
            raise ValueError("Extracted text too short, might be invalid content")

        # 6. Chunk text
        logger.info(f"[{url_id}]🔃 Chunking text...")
        chunks = chunk_text(cleaned_text, chunk_size=1000, overlap=200)
        logger.info(f"[{url_id}]🆗 Created {len(chunks)} chunks")

        # 7. Generate embeddings in batch
        logger.info(f"[{url_id}]🔃 Generating embeddings...")
        embeddings = generate_embeddings_batch(chunks)

        # 8. Store in ChromaDB
        logger.info(f"[{url_id}]🔃 Storing {len(chunks)} chunks in ChromaDB...")
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=[
                {
                    "url": metadata.url,
                    "url_id": url_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for idx in range(len(chunks))
            ],
            ids=[f"{url_id}_chunk_{idx}" for idx in range(len(chunks))],
        )

        # 9. Update status to completed
        metadata.status = IngestionStatus.completed
        metadata.chunks_created = len(chunks)
        metadata.updated_at = datetime.utcnow()
        metadata.error_message = None
        db.commit()

        logger.info(f"[{url_id}] ✅ Successfully processed URL")

    except Exception as e:
        # Update status to failed with error message
        logger.error(f"[{url_id}] ❌ Error: {str(e)}")

        if metadata:
            metadata.status = IngestionStatus.failed
            metadata.error_message = str(e)
            metadata.updated_at = datetime.utcnow()
            db.commit()

        # Re-raise so RQ marks job as failed
        raise

    finally:
        db.close()
