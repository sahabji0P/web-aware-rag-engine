"""
Shared ChromaDB initialization
Used by both worker and query modules
"""

import chromadb
import logging

logger = logging.getLogger(__name__)

# Initialize ChromaDB client once
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="web_content", metadata={"hnsw:space": "cosine"}
)

logger.info(f"ChromaDB collection initialized. Current size: {collection.count()}")


def get_collection():
    """Get the ChromaDB collection instance"""
    return collection


def get_client():
    """Get the ChromaDB client instance"""
    return chroma_client
