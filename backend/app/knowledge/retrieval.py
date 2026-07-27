"""Hybrid retrieval: vector similarity + full-text search, fused with RRF.

Neither signal alone is reliable for support content: vector search misses
exact model numbers and error codes (they're often out-of-vocabulary or
diluted in the embedding), full-text search misses paraphrases ("won't
connect" vs "failed to pair"). Reciprocal Rank Fusion combines the two
ranked lists without needing to calibrate their scores against each other,
which cosine similarity and ts_rank are not on the same scale to do.
"""

import time
from dataclasses import dataclass

from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.knowledge.embeddings import embed_query
from app.models import KnowledgeChunk, KnowledgeDocument, RetrievalEvent

RRF_K = 60  # standard constant from the original RRF paper; flattens the
# influence of any single ranker's exact position beyond the top few results.
CANDIDATE_MULTIPLIER = 4  # pull more candidates per ranker than top_k so RRF
# has enough overlap to fuse meaningfully.


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    document_url: str | None
    heading: str | None
    content: str
    vector_rank: int | None
    fts_rank: int | None
    score: float


async def _vector_candidates(
    session: AsyncSession, query_vector: list[float], limit: int
) -> list[str]:
    rows = (
        await session.execute(
            select(KnowledgeChunk.id)
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
    ).scalars().all()
    return [str(r) for r in rows]


async def _fts_candidates(session: AsyncSession, query: str, limit: int) -> list[str]:
    tsv = func.to_tsvector("english", KnowledgeChunk.content)
    tsq = func.plainto_tsquery("english", query)
    rows = (
        await session.execute(
            select(KnowledgeChunk.id)
            .where(tsv.op("@@")(tsq))
            .order_by(func.ts_rank(tsv, tsq).desc())
            .limit(limit)
        )
    ).scalars().all()
    return [str(r) for r in rows]


async def hybrid_search(
    session: AsyncSession,
    openai_client: AsyncOpenAI,
    settings: Settings,
    query: str,
    top_k: int | None = None,
    conversation_id: str | None = None,
) -> list[RetrievedChunk]:
    """Search the knowledge base and log the attempt as a RetrievalEvent.

    Every call is logged — including zero-result ones — because "the agent
    searched and found nothing" is exactly the signal that should route to
    escalation instead of a hallucinated answer.
    """
    top_k = top_k or settings.retrieval_top_k
    start = time.perf_counter()

    query_vector = await embed_query(openai_client, query, settings.embedding_model)
    candidate_limit = top_k * CANDIDATE_MULTIPLIER
    vector_ids = await _vector_candidates(session, query_vector, candidate_limit)
    fts_ids = await _fts_candidates(session, query, candidate_limit)

    vector_rank = {cid: i + 1 for i, cid in enumerate(vector_ids)}
    fts_rank = {cid: i + 1 for i, cid in enumerate(fts_ids)}
    all_ids = set(vector_rank) | set(fts_rank)

    def rrf_score(cid: str) -> float:
        s = 0.0
        if cid in vector_rank:
            s += 1.0 / (RRF_K + vector_rank[cid])
        if cid in fts_rank:
            s += 1.0 / (RRF_K + fts_rank[cid])
        return s

    ranked_ids = sorted(all_ids, key=rrf_score, reverse=True)[:top_k]

    results: list[RetrievedChunk] = []
    if ranked_ids:
        rows = (
            await session.execute(
                select(KnowledgeChunk, KnowledgeDocument)
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeChunk.id.in_(ranked_ids))
            )
        ).all()
        by_id = {str(chunk.id): (chunk, doc) for chunk, doc in rows}
        for cid in ranked_ids:
            chunk, doc = by_id[cid]
            results.append(
                RetrievedChunk(
                    chunk_id=cid,
                    document_id=str(doc.id),
                    document_title=doc.title,
                    document_url=doc.url,
                    heading=chunk.heading,
                    content=chunk.content,
                    vector_rank=vector_rank.get(cid),
                    fts_rank=fts_rank.get(cid),
                    score=rrf_score(cid),
                )
            )

    latency_ms = round((time.perf_counter() - start) * 1000)
    session.add(
        RetrievalEvent(
            conversation_id=conversation_id,
            query=query,
            strategy="hybrid_rrf",
            top_k=top_k,
            results=[
                {
                    "chunk_id": r.chunk_id,
                    "document_title": r.document_title,
                    "document_url": r.document_url,
                    "score": r.score,
                    "vector_rank": r.vector_rank,
                    "fts_rank": r.fts_rank,
                }
                for r in results
            ],
            latency_ms=latency_ms,
        )
    )
    await session.commit()
    return results
