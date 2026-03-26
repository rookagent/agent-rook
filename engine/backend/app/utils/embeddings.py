"""
Embedding generation for semantic memory search.

Uses sentence-transformers locally — free, no API calls needed.
Model: all-MiniLM-L6-v2 (384 dimensions, ~80MB download on first use).

Falls back gracefully if sentence-transformers isn't installed or the model
fails to load — _available flips to False and all future calls return None.
"""

import logging

logger = logging.getLogger(__name__)

_model = None
_available = True


def get_embedding(text):
    """
    Generate a 384-dim embedding vector for text.

    Returns list[float] on success, None if unavailable.
    Lazy-loads the model on first call (~2s), instant after that.
    """
    global _model, _available
    if not _available:
        return None
    try:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded all-MiniLM-L6-v2 embedding model")
        return _model.encode(text).tolist()
    except Exception as e:
        _available = False
        logger.warning(f"Embedding generation unavailable: {e}")
        return None


def is_available():
    """Check if embedding generation is available."""
    return _available
