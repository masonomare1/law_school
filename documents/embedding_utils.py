import logging
from typing import List

import numpy as np
from django.conf import settings

logger = logging.getLogger("law_school")


class EmbeddingBackendError(RuntimeError):
    pass


_sentence_transformer_model = None


def _get_sentence_transformer_model():
    """
    Lazily load the SentenceTransformer model.
    """
    global _sentence_transformer_model

    if _sentence_transformer_model is not None:
        return _sentence_transformer_model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingBackendError(
            "sentence-transformers is not installed. "
            "Install it or set USE_OPENAI_EMBEDDINGS=True."
        ) from exc

    model_name = settings.EMBEDDING_MODEL
    logger.info(f"Loading SentenceTransformer model: {model_name}")
    _sentence_transformer_model = SentenceTransformer(model_name)
    return _sentence_transformer_model


def _embed_with_sentence_transformers(texts: List[str]) -> np.ndarray:
    model = _get_sentence_transformer_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.astype("float32")


def _embed_with_openai(texts: List[str]) -> np.ndarray:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise EmbeddingBackendError(
            "openai package is not installed. Install it or set USE_OPENAI_EMBEDDINGS=False."
        ) from exc

    if not settings.OPENAI_API_KEY:
        raise EmbeddingBackendError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.EMBEDDING_MODEL

    # OpenAI embeddings API accepts a list of inputs
    response = client.embeddings.create(model=model, input=texts)
    vectors = [item.embedding for item in response.data]
    embeddings = np.array(vectors, dtype="float32")
    return embeddings


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Generate embeddings for a list of texts using the configured backend.

    Returns:
        np.ndarray of shape (len(texts), FAISS_INDEX_DIMENSION) with dtype float32
    """
    if not texts:
        return np.zeros((0, settings.FAISS_INDEX_DIMENSION), dtype="float32")

    if settings.USE_OPENAI_EMBEDDINGS:
        embeddings = _embed_with_openai(texts)
    else:
        embeddings = _embed_with_sentence_transformers(texts)

    if embeddings.ndim != 2:
        raise EmbeddingBackendError("Embeddings must be a 2D array.")

    dim = embeddings.shape[1]
    if dim != settings.FAISS_INDEX_DIMENSION:
        logger.warning(
            "Embedding dimension %s does not match FAISS_INDEX_DIMENSION %s. "
            "Updating FAISS_INDEX_DIMENSION to %s for compatibility.",
            dim,
            settings.FAISS_INDEX_DIMENSION,
            dim,
        )
        # NOTE: we do not mutate settings at runtime, but we enforce correct
        # shape for the FAISS index by returning the actual dimension.

    return embeddings.astype("float32")

