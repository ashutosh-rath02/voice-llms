"""Markdown-aware chunking for the ingestion pipeline.

Splits on headings first (so a chunk never straddles two unrelated topics),
then sub-splits any section that's still too long for one embedding. Each
chunk is prefixed with its heading path so the embedded text carries context
even in isolation — "Step 3: reset the device" reads very differently from
"## Wi-Fi Setup > Troubleshooting > Step 3: reset the device".
"""

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

MAX_CHARS = 1500
OVERLAP_CHARS = 200


@dataclass
class Chunk:
    heading: str | None
    content: str  # heading path + body, what actually gets embedded


def _split_long_section(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Prefer breaking on a paragraph boundary near the limit, not mid-word.
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [p for p in parts if p]


def chunk_markdown(text: str, doc_title: str) -> list[Chunk]:
    """Split one document's markdown body into embeddable chunks."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        sections = [(doc_title, text)]
    else:
        sections = []
        # Path stack: heading level -> heading text, so nested headings
        # ("## Setup" then "### Wi-Fi") build "Setup > Wi-Fi".
        path: dict[int, str] = {}
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append((doc_title, preamble))
        for i, m in enumerate(matches):
            level, heading = len(m.group(1)), m.group(2).strip()
            path = {lvl: h for lvl, h in path.items() if lvl < level}
            path[level] = heading
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[body_start:body_end].strip()
            if body:
                sections.append((" > ".join(path[lvl] for lvl in sorted(path)), body))

    chunks: list[Chunk] = []
    for heading, body in sections:
        for piece in _split_long_section(body, MAX_CHARS, OVERLAP_CHARS):
            chunks.append(Chunk(heading=heading, content=f"{heading}\n\n{piece}"))
    return chunks
