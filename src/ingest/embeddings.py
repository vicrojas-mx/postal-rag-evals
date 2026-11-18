import numpy
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from ingest.chunking import build_documents
from ingest.ingest import  build_sections

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


if __name__ == "__main__":
    sample_documents_content = []
    sample_documents = []
    sections = build_sections("data/po-209_-_2023.pdf")
    docs = build_documents(sections, "po-209_-_2023.pdf")
    for doc in docs:
        if "Name Tags" in doc.metadata["title"] or "3 Uniforms" in doc.metadata["title"] or "7-14.2" in doc.metadata["title"]:
            sample_documents_content.append(doc.page_content)
            sample_documents.append(doc.metadata["title"])
            if len(sample_documents) == 3:
                break

    embedder = LocalEmbedder("voyageai/voyage-4-nano")
    vectors = embedder.embed_documents(sample_documents_content)
    query_vector = embedder.embed_query("where do I request more rolls for the self-serve machine?git commit -m '")

    for doc, vector in zip(sample_documents, vectors):
        score = numpy.dot(vector, query_vector)
        print(f"{doc}  {score:.3f}")
