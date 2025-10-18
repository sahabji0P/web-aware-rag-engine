from fastapi import FastAPI
from app.db.metadata import init_db
from app.api import ingest, query

app = FastAPI(title="RAG Scraper API")

# Initialize SQLite tables
init_db()

# Include routes
app.include_router(ingest.router)
app.include_router(query.router)


@app.get("/")
def root():
    return {"message": "RAG Engine is live!"}
