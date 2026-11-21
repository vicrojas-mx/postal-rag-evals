# tests/integration/test_embeddings.py
import numpy as np
import pytest
from ingest.embeddings import LocalEmbedder

@pytest.fixture(scope="module")
def embedder():
    return LocalEmbedder("voyageai/voyage-4-nano")

def test_query_vector_is_normalized(embedder):
    vector = embedder.embed_query("how do I order supplies?")
    assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-2)

def test_document_vectors_are_normalized(embedder):
    vectors = embedder.embed_documents(["text one", "text two", "text kimo rocks"])
    for vector in vectors:
        assert len(vector) == 1024
        assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-2)




