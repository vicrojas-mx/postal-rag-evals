from anthropic import Anthropic
from langchain_core.vectorstores import InMemoryVectorStore

from ingest.embeddings import LocalEmbedder
from ingest.vectorstore import restore_vector_store, EMBEDDING_MODEL, INDEX_PATH

from dotenv import load_dotenv
import anthropic

def answer(question:str, client: Anthropic, store: InMemoryVectorStore, k:int = 4)->str:

    results = store.similarity_search_with_score(question, k)
    context = "\n\n---\n\n".join(f"[Source: {doc.metadata['breadcrumbs']} | p. {doc.metadata['page_label']}] \n\n {doc.page_content}" for doc, _ in results)

    response = client.beta.messages.create(
        model  = "claude-opus-5-5",
        max_tokens = 16000,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        messages=[{"role":"user", "content": f"Context:\n {context}\n\nQuestion:{question}"}]
    )

    content = []
    if response.stop_reason == "refusal":
        content.append(f"Question: {question} was rejected")
    else:
        for block in response.content:
            if block.type == "text":
                content.append(block.text)

    return ("\n".join(content))


SYSTEM_PROMPT = ("You are a helpful assistant. "
                 "Answer the question ONLY using the provided context, Cite the section number (e.g. 'per 7-14.2'), "
                 "If it's not there, answer exactly: 'I don't know.', answer in the same language as the question.")

if __name__ == "__main__":
    question = "¿dónde pido más rollos pa' la máquina self-serve, carnal?"
    load_dotenv(override=True)
    client = anthropic.Anthropic()
    embedder = LocalEmbedder(EMBEDDING_MODEL)

    store = restore_vector_store(INDEX_PATH, embedder=embedder)
    print(answer(question, client=client, store=store, k=4))
