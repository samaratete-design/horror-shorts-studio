from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from originality_engine.vector_store import VectorStore
from originality_engine.engine import EmbeddingDimensionMismatchError

from app.core.container import build_originality_engine, ProviderConfigurationError
from app.core.deps import get_vector_store
from app.schemas.stories import OriginalityCheckRequest, OriginalityCheckResponse

router = APIRouter(prefix="/originality", tags=["originality"])


@router.post("/check", response_model=OriginalityCheckResponse)
async def check_originality(
    payload: OriginalityCheckRequest, vector_store: VectorStore = Depends(get_vector_store)
):
    try:
        engine = build_originality_engine(vector_store)
        decision = await engine.check(payload.dna)
    except EmbeddingDimensionMismatchError as exc:
        # A real configuration bug (dims drifted between DB/provider) - not
        # the caller's fault, but also not something to hide as a 500.
        raise HTTPException(status_code=500, detail=f"Embedding configuration error: {exc}") from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is currently unavailable. Please retry.") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid Story DNA: {exc}") from exc

    return OriginalityCheckResponse(decision=decision)
