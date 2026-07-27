"""Thin wrapper around the OpenAI embeddings API.

Kept as one function so the ingestion CLI and the live retrieval path share
exactly one code path to the provider — a model/provider swap happens here
once, not in N call sites.
"""

from openai import AsyncOpenAI

# OpenAI batches embedding requests server-side; keeping our own batches
# well under its input-array limit avoids a single oversized request failing
# and losing an entire ingestion run.
MAX_BATCH_SIZE = 100


async def embed_texts(
    client: AsyncOpenAI, texts: list[str], model: str
) -> list[list[float]]:
    """Embed a list of texts, batching to stay within provider limits.

    Order is preserved: result[i] is the embedding for texts[i].
    """
    if not texts:
        return []
    vectors: list[list[float]] = []
    for start in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[start : start + MAX_BATCH_SIZE]
        response = await client.embeddings.create(model=model, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors


async def embed_query(client: AsyncOpenAI, text: str, model: str) -> list[float]:
    result = await embed_texts(client, [text], model)
    return result[0]
