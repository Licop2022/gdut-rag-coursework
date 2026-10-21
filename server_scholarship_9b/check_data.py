import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return [json.loads(line) for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines()]


articles = {a["id"]: a for a in read("articles.jsonl")}
chunks = read("chunks.jsonl")
assert len(articles) == 26 and len(chunks) == 27
assert len({c["id"] for c in chunks}) == len(chunks)
for aid, article in articles.items():
    coverage = set()
    for chunk in chunks:
        if chunk["article_id"] == aid:
            assert chunk["text"] == article["text"][chunk["start"]:chunk["end"]]
            coverage.update(range(chunk["start"], chunk["end"]))
            assert all(196 <= p["pdf_page"] <= 201 and p["pdf_page"] - p["printed_page"] == 3 for p in chunk["source_pages"])
    assert coverage == set(range(len(article["text"])))
heldout = {aid for t in read("eval.jsonl") for aid in t["expected_articles"]}
train = {aid for s in read("lora_train.jsonl") for aid in s["article_ids"]}
dev = {aid for s in read("lora_dev.jsonl") for aid in s["article_ids"]}
assert not (train & heldout or dev & heldout or train & dev)
for amount in ["18000", "15000", "12000", "10000", "6000", "2000"]:
    assert amount in articles["A05"]["text"]
print("DATA_CHECK_PASSED: 26 articles, 27 chunks, full character coverage, page provenance, article-isolated train/dev/test")
