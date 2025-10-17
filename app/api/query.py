import os
import logging
from typing import Optional
import google.generativeai as genai
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.db.metadata import SessionLocal, URLMetadata, IngestionStatus
from app.db.vector import get_collection


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize ChromaDB
collection = get_collection()

# API Router
router = APIRouter(prefix="/query", tags=["Query"])


# Request/Response schemas
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5  # Number of chunks to retrieve
    min_similarity: float = 0.5  # Minimum similarity threshold (0-1)


class RetrievedChunk(BaseModel):
    url: str
    url_id: int
    chunk_index: int
    total_chunks: int
    content: str
    similarity: float


class QueryResponse(BaseModel):
    query: str
    retrieved_chunks: list[RetrievedChunk]
    grounded_answer: str
    sources: list[str]  # Unique URLs used


def generate_query_embedding(query: str) -> list[float]:
    model = "models/text-embedding-004"

    try:
        result = genai.embed_content(
            model=model, content=query, task_type="retrieval_query"
        )
        # api response is a disctionary with "embedding" key
        return result["embedding"]

    except Exception as e:
        logger.error(f"Error generating query embedding: {str(e)}")
        raise ValueError(f"Failed to generate query embedding: {str(e)}")


def retrieve_relevant_chunks(
    query_embedding: list[float], top_k: int = 5, min_similarity: float = 0.5
) -> list[RetrievedChunk]:
    try:
        results = collection.query(
            # query embedding expected to be a list of list, therefore the query_embedding param is wrapped in []
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []

        if not results["documents"] or len(results["documents"]) == 0:
            return chunks

        for idx, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][idx]
            similarity = 1 - distance  # Convert distance to similarity

            # Filter by minimum similarity
            if similarity < min_similarity:
                continue

            metadata = results["metadatas"][0][idx]

            chunk = RetrievedChunk(
                url=metadata["url"],
                url_id=int(metadata["url_id"]),
                chunk_index=int(metadata["chunk_index"]),
                total_chunks=int(metadata["total_chunks"]),
                content=doc,
                similarity=round(similarity, 4),
            )
            chunks.append(chunk)

        return chunks

    except Exception as e:
        logger.error(f"Error retrieving chunks: {str(e)}")
        raise ValueError(f"Failed to retrieve chunks: {str(e)}")


def generate_grounded_answer(query: str, retrieved_chunks: list[RetrievedChunk]) -> str:
    """
    Generate answer using Gemini with retrieved chunks as context
    """
    if not retrieved_chunks:
        return "No relevant information found in the knowledge base."

    # Build context from retrieved chunks
    context = "\n\n".join(
        [
            f"Source: {chunk.url}\n"
            f"Chunk {chunk.chunk_index + 1}/{chunk.total_chunks}:\n"
            f"{chunk.content}"
            for chunk in retrieved_chunks
        ]
    )

    # Prompt for grounded answer generation
    prompt = f"""You are a helpful assistant answering questions based on provided sources.

RETRIEVED SOURCES:
{context}

USER QUERY: {query}

INSTRUCTIONS:
1. Answer the question based ONLY on the provided sources.
2. If the answer is not in the sources, say "I don't have enough information to answer this question."
3. Cite the source URLs when referencing information.
4. Be concise and factual.
5. Format your answer clearly.

ANSWER:"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        raise ValueError(f"Failed to generate answer: {str(e)}")


@router.post("/search", response_model=QueryResponse)
def search_and_answer(request: QueryRequest):

    logger.info(f"🔃Processing query: {request.query[:100]}...")

    # Validate inputs
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if request.top_k < 1 or request.top_k > 10:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 10")

    if request.min_similarity < 0 or request.min_similarity > 1:
        raise HTTPException(
            status_code=400, detail="min_similarity must be between 0 and 1"
        )

    try:
        # Step 1: Generate embedding for query
        logger.info("Generating query embedding...")
        query_embedding = generate_query_embedding(request.query)

        # Step 2: Retrieve relevant chunks
        logger.info(f"Retrieving top {request.top_k} chunks...")
        retrieved_chunks = retrieve_relevant_chunks(
            query_embedding=query_embedding,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )

        logger.info(f"🆗Retrieved {len(retrieved_chunks)} relevant chunks")

        # Step 3: Generate grounded answer
        logger.info("🔃Generating answer...")
        answer = generate_grounded_answer(request.query, retrieved_chunks)

        # Step 4: Extract unique sources
        sources = list(set([chunk.url for chunk in retrieved_chunks]))

        logger.info(f"🆗Query completed. Found {len(sources)} source(s)")

        return QueryResponse(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            grounded_answer=answer,
            sources=sources,
        )

    except ValueError as e:
        logger.error(f"Query processing error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
def get_query_stats():
    db = SessionLocal()
    try:
        total_urls = db.query(URLMetadata).count()
        completed_urls = (
            db.query(URLMetadata)
            .filter(URLMetadata.status == IngestionStatus.completed)
            .count()
        )
        failed_urls = (
            db.query(URLMetadata)
            .filter(URLMetadata.status == IngestionStatus.failed)
            .count()
        )
        processing_urls = (
            db.query(URLMetadata)
            .filter(URLMetadata.status == IngestionStatus.processing)
            .count()
        )

        # Get ChromaDB stats
        total_chunks = collection.count()

        return {
            "total_urls_submitted": total_urls,
            "completed_urls": completed_urls,
            "failed_urls": failed_urls,
            "processing_urls": processing_urls,
            "total_chunks_indexed": total_chunks,
            "average_chunks_per_url": (
                round(total_chunks / completed_urls, 2) if completed_urls > 0 else 0
            ),
        }

    finally:
        db.close()
