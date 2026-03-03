import os
import logging
from typing import List, Tuple

import faiss
import numpy as np
from django.conf import settings
from django.db.models import QuerySet

from .models import Document, DocumentChunk
from .embedding_utils import embed_texts

logger = logging.getLogger("law_school")


def _index_path_for_document(document_id: str) -> str:
    filename = f"{document_id}.faiss"
    return os.path.join(settings.FAISS_INDEX_PATH, filename)


def build_index_for_document(document: Document) -> int:
    """
    Build or rebuild a FAISS index for all chunks of a document.

    Returns:
        Number of vectors indexed.
    """
    chunks: QuerySet[DocumentChunk] = document.chunks.order_by("chunk_index")
    texts: List[str] = [c.chunk_text for c in chunks]

    if not texts:
        logger.warning("No chunks found for document %s. Skipping FAISS index build.", document.id)
        return 0

    embeddings = embed_texts(texts)
    num_vectors, dim = embeddings.shape

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    index_path = _index_path_for_document(str(document.id))
    faiss.write_index(index, index_path)
    logger.info("Built FAISS index for document %s with %s vectors at %s", document.id, num_vectors, index_path)

    return num_vectors


def _iter_index_files() -> List[Tuple[str, str]]:
    """
    Return list of (document_id, index_path) tuples for all FAISS index files.
    """
    if not os.path.isdir(settings.FAISS_INDEX_PATH):
        return []

    entries: List[Tuple[str, str]] = []
    for name in os.listdir(settings.FAISS_INDEX_PATH):
        if not name.endswith(".faiss"):
            continue
        doc_id = name.rsplit(".", 1)[0]
        path = os.path.join(settings.FAISS_INDEX_PATH, name)
        entries.append((doc_id, path))

    return entries


def search_across_documents(query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
    """
    Search all per-document FAISS indexes and return the top_k chunks globally.

    Args:
        query_embedding: np.ndarray of shape (dim,) or (1, dim)
        top_k: maximum number of chunks to return

    Returns:
        List of (DocumentChunk, distance) tuples sorted by ascending distance.
    """
    if query_embedding.ndim == 1:
        query_embedding = np.expand_dims(query_embedding, axis=0)

    if query_embedding.ndim != 2:
        raise ValueError("query_embedding must be 2D array.")

    all_results: List[Tuple[DocumentChunk, float]] = []

    for doc_id, index_path in _iter_index_files():
        try:
            index = faiss.read_index(index_path)
        except Exception as exc:
            logger.error("Failed to read FAISS index %s: %s", index_path, exc)
            continue

        try:
            distances, indices = index.search(query_embedding, top_k)
        except Exception as exc:
            logger.error("FAISS search failed for index %s: %s", index_path, exc)
            continue

        # indices and distances are arrays of shape (1, top_k)
        distances = distances[0]
        indices = indices[0]

        try:
            document = Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            logger.warning("Document %s referenced by FAISS index not found in DB.", doc_id)
            continue

        for rank, (dist, idx) in enumerate(zip(distances, indices)):
            if idx < 0:
                continue

            try:
                chunk = DocumentChunk.objects.get(document=document, chunk_index=int(idx))
            except DocumentChunk.DoesNotExist:
                logger.warning(
                    "Chunk with index %s not found for document %s (index file %s)",
                    idx,
                    doc_id,
                    index_path,
                )
                continue

            all_results.append((chunk, float(dist)))

    # Sort globally by ascending distance (smaller distance = more similar)
    all_results.sort(key=lambda pair: pair[1])
    return all_results[:top_k]

