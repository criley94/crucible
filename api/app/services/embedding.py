"""Vertex AI text embedding service."""

import logging
import os

logger = logging.getLogger(__name__)

# Lazy-loaded client
_model = None


def _get_model():
    """Lazy-load the Vertex AI embedding model."""
    global _model
    if _model is None:
        from google.cloud import aiplatform
        from vertexai.language_models import TextEmbeddingModel

        project = os.environ.get("GCP_PROJECT", "deckhouse-489723")
        location = os.environ.get("GCP_LOCATION", "us-central1")
        aiplatform.init(project=project, location=location)
        _model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    return _model


def embed_text(text: str) -> list[float] | None:
    """Generate a 768-dimension embedding for the given text.

    Returns None if embedding fails (logged, not raised).
    """
    try:
        model = _get_model()
        embeddings = model.get_embeddings([text])
        return embeddings[0].values
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """Generate embeddings for multiple texts in a single batch call.

    Returns a list of embeddings (or None for failures) in the same order.
    """
    if not texts:
        return []
    try:
        model = _get_model()
        embeddings = model.get_embeddings(texts)
        return [e.values for e in embeddings]
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        return [None] * len(texts)
