import os
from pypdf import PdfReader
from pypdf.generic import Destination
from langchain_core.documents import Document

HEADER_MARKERS = ["August 2023", "Handbook PO-209"]

def load_handbook(path:str)->list[Document]:
    reader = PdfReader(path)
    documents = []
    for pagenum, page in enumerate(reader.pages):        
        doc = Document(
            page_content=page.extract_text(),
            metadata={"source": path, "page" : pagenum}
            )
        documents.append(doc)
    return documents

def list_reader_outline(outline: list | Destination, depth:int, reader:PdfReader, page_labels:list[str], return_list:list[dict]) -> None:
    if isinstance(outline, list):
        depth += 1
        for section in outline:
           list_reader_outline(section, depth, reader, page_labels, return_list)
    else:
        dest_page = reader.get_destination_page_number(outline)
        if dest_page is None:
            print(f"WARNING: outline -{outline}- doesn't have a destination page number")
            return
        
        printed_label = page_labels[dest_page]
        if outline.title and outline.title.strip():
            return_list.append({
                "title": outline.title.strip(),
                "depth": depth,
                "page_index": dest_page,
                "page_label": printed_label
                }
            )

def add_end_pages(sections: list[dict], total_pages: int) -> None:
    for index, section in enumerate(sections):
        if index < len(sections) - 1:
            section["end_page_index"] = sections[index+1]["page_index"]
        else:
            section["end_page_index"] = total_pages-1

def add_section_text(sections:list[dict], reader: PdfReader) -> None:
    for index, section in enumerate(sections):
        pages_total_content = ""
        for context_index in range(section["page_index"], section["end_page_index"]+1):
            text = clean_text(reader.get_page(context_index).extract_text())
            pages_total_content +=  " ".join(text.split()) + " "
        
        if index <  len(sections) -1:
            initial_title = " ".join(section["title"].split())
            start_index = find_title(pages_total_content, initial_title)
            if start_index != -1:
                ending_title = " ".join(sections[index+1]["title"].split())
                end_index = find_title(pages_total_content, ending_title, start_index)
                section["content"] = pages_total_content[start_index:end_index]
            else:
                section["content"] = "NO_TITLE_CARNAL"
        else:
            section["content"] = pages_total_content


def find_title(text:str, title:str, start:int = 0) -> int:
    index = text.find(title, start)
    if index != -1:
        return index
    else:
        title = title.replace(" ", "", 1)
        index = text.find(title, start)
    return index

def clean_text(text:str) -> str:
    output_text = ""
    if "intentionally left blank" in text:
        return ""
    else:
        lines = text.split("\n")
        if len(lines) > 1:
            if marker_exists_in_line(lines[0]): 
                output_text = "\n".join(lines[1:])
            elif marker_exists_in_line(lines[1]): 
                output_text = "\n".join(lines[2:])
            else:
                output_text = "\n".join(lines)
        else:
            if marker_exists_in_line(lines[0]): 
                output_text = ""
            else:
                output_text = lines[0]
        
    return output_text


def marker_exists_in_line(line:str) -> bool:
    return any(marker in line for marker in HEADER_MARKERS)


def main()->None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "../../data", "po-209_-_2023.pdf")
    load_handbook(pdf_path)

    reader = PdfReader(pdf_path)
    mylist:list[dict] = []
    list_reader_outline(reader.outline, 0, reader, reader.page_labels, mylist)
    print(len(mylist))
    print(mylist[:5])
    last_page = len(reader.pages)
    add_end_pages(sections=mylist, total_pages=last_page)
    add_section_text(mylist, reader)
    # print("\n@@@@@@@@")
    print(mylist[310:315])


if __name__ == "__main__":
    main()
