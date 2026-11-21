from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

from ingest.chunking import build_documents
from ingest.ingest import  build_sections
from ingest.embeddings import LocalEmbedder
from pathlib import Path

EMBEDDING_MODEL = "voyageai/voyage-4-nano"
INDEX_PATH = "data/voyageai_voyage-4-nano_vector_store.json"

def build_index(docs: list[Document], embedder:Embeddings) -> InMemoryVectorStore:
    vector_store = InMemoryVectorStore(embedding=embedder)
    vector_store.add_documents(docs)
    return vector_store

def save_vector_store(vector_store: InMemoryVectorStore, path: str) -> None:
    if path is None:
        raise TypeError("Path to save Vector Store cannot be None")
    vector_store.dump(path)

def restore_vector_store(path: str, embedder:Embeddings) -> InMemoryVectorStore:
    if path is None:
        raise TypeError("Path to restore Vector Store cannot be None")
    return InMemoryVectorStore.load(path, embedding=embedder)


if __name__ == "__main__":

    embedder = LocalEmbedder(EMBEDDING_MODEL)
    file_path = Path(INDEX_PATH)

    if not file_path.exists():
        sections = build_sections("data/po-209_-_2023.pdf")
        docs = build_documents(sections, "po-209_-_2023.pdf")
        vector_store = build_index(docs, embedder)
        save_vector_store(vector_store, str(file_path))

    vector_store_restored = restore_vector_store(str(file_path), embedder=embedder)
    results = vector_store_restored.similarity_search_with_score("¿dónde pido más rollos pa' la máquina self-serve, carnal?", k=4)

    for doc, score in results:
        print(f"{doc.metadata["title"]}: {score}")
