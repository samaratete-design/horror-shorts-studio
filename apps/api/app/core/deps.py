from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from originality_engine.vector_store import VectorStore

from app.db.session import get_db
from app.db.pgvector_store import PgVectorStore


async def get_vector_store(db: AsyncSession = Depends(get_db)) -> VectorStore:
    """
    Production default: pgvector-backed store using the request's DB session.
    Tests override this dependency (via app.dependency_overrides) with an
    InMemoryVectorStore so /originality/check can be exercised without a
    live Postgres instance.
    """
    return PgVectorStore(db)
