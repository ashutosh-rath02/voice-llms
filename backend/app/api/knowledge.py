import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.knowledge.retrieval import hybrid_search
from app.models import KnowledgeDocument, RoleName
from app.schemas.knowledge import DocumentOut, SearchRequest, SearchResponse, SearchResultOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Retrieval quality is an operational/engineering concern (PRD 6.12 dashboard
# view), not a customer-facing feature — customers get answers via the voice
# agent, not by querying the index directly.
_staff_only = require_roles(RoleName.ADMIN, RoleName.SUPPORT_AGENT, RoleName.SUPPORT_MANAGER)


@router.get("/documents", response_model=list[DocumentOut], dependencies=[Depends(_staff_only)])
async def list_documents(session: DbSession) -> list[KnowledgeDocument]:
    result = await session.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.source, KnowledgeDocument.path)
    )
    return list(result.scalars().all())


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(_staff_only)])
async def search(body: SearchRequest, request: Request, session: DbSession) -> SearchResponse:
    """Ad-hoc retrieval inspection: same code path the voice agent uses
    mid-call, exposed here so retrieval quality can be checked directly."""
    settings = request.app.state.settings
    start = time.perf_counter()
    results = await hybrid_search(
        session, request.app.state.openai_client, settings, body.query, top_k=body.top_k
    )
    latency_ms = round((time.perf_counter() - start) * 1000)
    return SearchResponse(
        query=body.query,
        results=[SearchResultOut(**vars(r)) for r in results],
        latency_ms=latency_ms,
    )
