from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1500
CHUNK_OVERLAP=200

splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

def build_documents(sections:list[dict], source:str) -> list[Document]:
    documents = []
    for section in sections:

        title_glued = section["title"].replace(" ", "", 1)
        if section["title"].strip() == section["content"].strip() or title_glued == section["content"].strip():
            continue

        chunks = splitter.split_text(section["content"])
        for chunk_index, chunk in enumerate(chunks):
            doc = Document(
                page_content=f"{section['breadcrumbs']}\n\n{chunk}",
                metadata={
                    "title": section["title"],
                    "breadcrumbs": section["breadcrumbs"],
                    "page_label": section["page_label"],
                    "depth": section["depth"],
                    "chunk_index": chunk_index,
                    "source": source
                }
            )
            documents.append(doc)

    return documents

