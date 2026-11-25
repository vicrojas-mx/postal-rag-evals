import json

from ingest.vectorstore import restore_vector_store, EMBEDDING_MODEL, INDEX_PATH
from ingest.embeddings import LocalEmbedder
from pathlib import Path

TAG_TYPE = ["direct", "disambiguation", "paraphrase"]
LANGS = ["en", "es", "spanglish"]

def matches(retrieved, expected):
    hit = 0
    recall = 0
    rank = None
    for expected_value in expected:
        for rank_index, retrieved_value in enumerate(retrieved):
            if expected_value == retrieved_value or retrieved_value.startswith(expected_value + "."):
                hit = 1
                recall += 1
                if not rank:
                    rank = rank_index + 1
                else:
                    if rank_index + 1 < rank:
                        rank = rank_index + 1
                break

    return hit, recall/len(expected), rank

def summarize(rows):
    hits = [row["hit"] for row in rows]
    hit_average = sum(hits)/len(hits)

    recalls = [row["recall"] for row in rows]
    recalls_average = sum(recalls)/len(recalls)

    mrrs = [1/row["rank"] if row["rank"] else 0  for row in rows]
    mrrs_average = sum(mrrs)/len(recalls)

    return hit_average, recalls_average, mrrs_average

if __name__ == "__main__":
    embedder = LocalEmbedder(EMBEDDING_MODEL)
    store = restore_vector_store(INDEX_PATH, embedder=embedder)

    cases_path = Path(__file__).parent / "retrieval_cases.json"
    results_path = Path(__file__).parent.parent.parent / "results" / "retrieval_baseline.jsonl"
    summary_path = Path(__file__).parent.parent.parent / "results" / "summary.txt"

    with open(cases_path, "r", encoding="utf-8") as file:
        questions = json.load(file)

    data_results = []
    for index, question in enumerate(questions):
        retrieved_sections = []
        similar_documents = store.similarity_search_with_score(question["question"], k=4)
        for document, score in similar_documents:
            retrieved_sections.append(document.metadata["title"].split()[0])

        match, recall, rank = matches(retrieved_sections, question["expected"])
        case  =  {"id": question["id"], "tags": question["tags"], "retrieved":retrieved_sections, "hit":match, "recall":recall, "rank":rank}
        data_results.append(case)

    with open(results_path, "w", encoding="utf-8") as file_output:
        for case in data_results:
            file_output.write(json.dumps(case, ensure_ascii=False) + "\n")

    with open(summary_path, "w", encoding="utf-8") as file_output:
        summary = summarize(data_results)
        file_output.write(f"OVERALL({len(data_results)})    hit@4 {summary[0]}      recall@4 {summary[1]}      MRR {summary[2]}\n")
        file_output.write("by type:\n")
        for tag in TAG_TYPE:
            data_tags = [case for case in data_results if case["tags"][0] == tag]
            summary = summarize(data_tags)
            file_output.write(f"   {tag}({len(data_tags)})    hit@4 {summary[0]}      recall@4 {summary[1]}      MRR {summary[2]}\n")

        file_output.write("\n")
        file_output.write("by lang:\n")
        for language in LANGS:
            data_languages = [case for case in data_results if case["tags"][1] == language]
            summary = summarize(data_languages)
            file_output.write(f"   {language}({len(data_languages)})    hit@4 {summary[0]}      recall@4 {summary[1]}      MRR {summary[2]}\n")
