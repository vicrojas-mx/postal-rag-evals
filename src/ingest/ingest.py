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

def list_reader_outline(outline, depth, reader:PdfReader, page_labels, return_list):
    if isinstance(outline, list):
        depth += 1
        for section in outline:
           list_reader_outline(section, depth, reader, page_labels, return_list)
    else:
        dest_page = reader.get_destination_page_number(outline)
        printed_label = page_labels[dest_page]
        if outline.title and outline.title.strip():
            return_list.append({
                "title": outline.title.strip(),
                "depth": depth,
                "page_index": dest_page,
                "page_label": printed_label
                }
            )

def add_end_pages(sections, total_pages):
    for index, section in enumerate(sections):
        if index < len(sections) - 1:
            section["end_page_index"] = sections[index+1]["page_index"]
        else:
            section["end_page_index"] = total_pages-1


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "../../data", "po-209_-_2023.pdf")
    load_handbook(pdf_path)

    reader = PdfReader(pdf_path)
    mylist = []
    list_reader_outline(reader.outline, 0, reader, reader.page_labels, mylist)
    print(len(mylist))
    print(mylist[:5])
    last_page = len(reader.pages)
    add_end_pages(sections=mylist, total_pages=last_page)
    print(mylist)




if __name__ == "__main__":
    main()
