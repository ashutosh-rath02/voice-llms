"""Ingestion CLI: real markdown docs -> chunked, embedded knowledge base.

Usage (from backend/):
    python -m app.knowledge.ingest <docs_dir> --source home_assistant_docs \\
        --base-url https://www.home-assistant.io/ --glob "**/*.markdown"

Idempotent by design: each document's (source, path) is a natural key, and a
content hash means an unchanged file is skipped entirely on re-run — only
new or edited docs pay for embedding calls. This is what "re-ingestion on
content updates" (PRD 6.7) means in practice.
"""

import argparse
import asyncio
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import structlog
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core import db
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.knowledge.chunking import chunk_markdown
from app.knowledge.embeddings import embed_texts
from app.knowledge.preprocess import clean_liquid_tags
from app.models import DocumentStatus, KnowledgeChunk, KnowledgeDocument

log = structlog.get_logger()

TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
FRONTMATTER_TITLE_RE = re.compile(r'^title:\s*"?(.+?)"?\s*$', re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def extract_title(text: str, fallback: str) -> tuple[str, str]:
    """Return (title, body_without_frontmatter)."""
    fm_match = FRONTMATTER_RE.match(text)
    frontmatter = fm_match.group(1) if fm_match else ""
    body = text[fm_match.end() :] if fm_match else text

    fm_title = FRONTMATTER_TITLE_RE.search(frontmatter)
    if fm_title:
        return fm_title.group(1).strip(), body
    h1 = TITLE_RE.search(body)
    if h1:
        return h1.group(1).strip(), body
    return fallback, body


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def url_slug(rel_path: str) -> str:
    """<name>.markdown -> <name>; <dir>/index.markdown -> <dir>.

    Turns a filesystem-relative path into the URL segment publishing sites
    conventionally use, so attribution links resolve to a real page instead
    of a raw source filename.
    """
    slug = re.sub(r"\.(markdown|md)$", "", rel_path)
    if slug.endswith("/index") or slug == "index":
        slug = slug[: -len("index")].rstrip("/")
    return slug


async def ingest_directory(
    docs_dir: Path,
    source: str,
    base_url: str | None,
    glob: str,
    limit: int | None,
) -> None:
    settings = get_settings()
    engine = db.create_engine(settings)
    sessions = db.create_session_factory(engine)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    files = sorted(docs_dir.glob(glob))
    if limit:
        files = files[:limit]
    log.info("ingest_starting", source=source, files_found=len(files))

    stats = {"indexed": 0, "skipped_unchanged": 0, "failed": 0}

    for path in files:
        rel_path = str(path.relative_to(docs_dir))
        raw = path.read_text(encoding="utf-8", errors="ignore")
        title, body = extract_title(raw, fallback=path.stem.replace("_", " ").title())
        doc_hash = content_hash(raw)
        url = f"{base_url.rstrip('/')}/{url_slug(rel_path)}/" if base_url else None

        async with sessions() as session:
            existing = (
                await session.execute(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.source == source, KnowledgeDocument.path == rel_path
                    )
                )
            ).scalar_one_or_none()

            if existing and existing.content_hash == doc_hash:
                stats["skipped_unchanged"] += 1
                continue

            try:
                chunks = chunk_markdown(clean_liquid_tags(body), doc_title=title)
                if not chunks:
                    raise ValueError("no chunks produced (empty document)")
                vectors = await embed_texts(
                    openai_client, [c.content for c in chunks], settings.embedding_model
                )
            except Exception as exc:
                stats["failed"] += 1
                log.warning("ingest_failed", path=rel_path, error=repr(exc))
                await session.execute(
                    pg_insert(KnowledgeDocument)
                    .values(
                        source=source,
                        path=rel_path,
                        title=title,
                        url=url,
                        content_hash=doc_hash,
                        status=DocumentStatus.FAILED,
                        error=repr(exc)[:2000],
                    )
                    .on_conflict_do_update(
                        index_elements=["source", "path"],
                        set_={"status": DocumentStatus.FAILED, "error": repr(exc)[:2000]},
                    )
                )
                await session.commit()
                continue

            if existing:
                document = existing
                document.title, document.url = title, url
                document.content_hash, document.chunk_count = doc_hash, len(chunks)
                document.status, document.error = DocumentStatus.INDEXED, None
                await session.execute(
                    KnowledgeChunk.__table__.delete().where(
                        KnowledgeChunk.document_id == document.id
                    )
                )
            else:
                document = KnowledgeDocument(
                    source=source,
                    path=rel_path,
                    title=title,
                    url=url,
                    content_hash=doc_hash,
                    chunk_count=len(chunks),
                    status=DocumentStatus.INDEXED,
                )
                session.add(document)
            document.last_indexed_at = datetime.now(UTC)
            await session.flush()

            session.add_all(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=i,
                    heading=c.heading,
                    content=c.content,
                    embedding=vec,
                )
                for i, (c, vec) in enumerate(zip(chunks, vectors, strict=True))
            )
            await session.commit()
            stats["indexed"] += 1
            if stats["indexed"] % 25 == 0:
                log.info("ingest_progress", **stats)

    log.info("ingest_complete", source=source, **stats)
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a markdown corpus into the knowledge base")
    parser.add_argument("docs_dir", type=Path)
    parser.add_argument("--source", required=True, help="corpus name, e.g. home_assistant_docs")
    parser.add_argument("--base-url", default=None, help="public URL prefix for attribution links")
    parser.add_argument("--glob", default="**/*.md")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.app_env != "dev")
    asyncio.run(
        ingest_directory(args.docs_dir, args.source, args.base_url, args.glob, args.limit)
    )


if __name__ == "__main__":
    main()
