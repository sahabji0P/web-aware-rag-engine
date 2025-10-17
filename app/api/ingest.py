from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from app.db.metadata import SessionLocal, URLMetadata, IngestionStatus
import redis
from rq import Queue

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Connect to Redis
redis_conn = redis.Redis(host="localhost", port=6379, db=0)
q = Queue("ingestion_queue", connection=redis_conn)


# Request schema
class IngestRequest(BaseModel):
    url: HttpUrl


@router.post("/url", status_code=202)
def ingest_url(request: IngestRequest):
    db = SessionLocal()

    try:
        existing = (
            db.query(URLMetadata).filter(URLMetadata.url == str(request.url)).first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="URL already submitted")

        metadata = URLMetadata(url=str(request.url), status=IngestionStatus.pending)
        db.add(metadata)
        db.commit()
        db.refresh(metadata)

        try:
            q.enqueue("app.worker.worker.process_url", metadata.id)
        except Exception as e:
            # If queue fails, mark as failed so user knows
            metadata.status = IngestionStatus.failed
            metadata.error_message = f"Failed to queue job: {str(e)}"
            db.commit()
            raise HTTPException(status_code=500, detail="Failed to queue job")

        return {
            "message": "URL submitted successfully",
            "url_id": metadata.id,
            "status": metadata.status,
        }
    finally:
        db.close()


@router.get("/status/{url_id}")
def get_ingest_status(url_id: int):
    db = SessionLocal()
    try:
        metadata = db.query(URLMetadata).filter(URLMetadata.id == url_id).first()
        if not metadata:
            raise HTTPException(status_code=404, detail="URL not found")

        return {
            "url_id": metadata.id,
            "url": metadata.url,
            "status": metadata.status,
            "created_at": metadata.created_at,
            "updated_at": metadata.updated_at,
            "error_message": metadata.error_message,
        }
    finally:
        db.close()
