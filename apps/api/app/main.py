from fastapi import FastAPI

from app.routers import stories, originality

app = FastAPI(
    title="Horror Shorts Studio API",
    version="0.1.0",
    description="AI-powered horror Shorts content factory - Phase 1 (architecture, DB, Story DNA, Originality Engine)",
)

app.include_router(stories.router)
app.include_router(originality.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
