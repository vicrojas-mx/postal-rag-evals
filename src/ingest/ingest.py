import os
from pypdf import PdfReader
from langchain_core.documents import Document

def load_handbook(path):
    reader = PdfReader(path)
    documents = []
    for pagenum, page in enumerate(reader.pages):        
        doc = Document(
            page_content=page.extract_text(),
            metadata={"source": path, "page" : pagenum}
            )
        documents.append(doc)

    return documents

def print_reader_outline(outline, depth, reader:PdfReader, page_labels):
    depth += 4
    if isinstance(outline, list):
        for section in outline:
           print_reader_outline(section, depth, reader, page_labels)
    else:
        spaces= " " * depth
        dest_page = reader.get_destination_page_number(outline)
        printed_label = page_labels[dest_page]
        print(f"{spaces} {outline.title} {dest_page} {printed_label}")


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "../../data", "po-209_-_2023.pdf")
    load_handbook(pdf_path)

    reader = PdfReader(pdf_path)
    print_reader_outline(reader.outline, 0, reader, reader.page_labels)


if __name__ == "__main__":
    main()
