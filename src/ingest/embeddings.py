from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


class LocalEmbedder(Embeddings):

    def __init__(self, model: str):
        self.model = SentenceTransformer(model, trust_remote_code=True, truncate_dim=1024)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise ValueError("texts is empty")

        doc_embeddings =  self.model.encode_document(texts)
        return doc_embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text:
            raise ValueError("text is empty")

        query_embeddings = self.model.encode_query(text)
        return query_embeddings.tolist()
