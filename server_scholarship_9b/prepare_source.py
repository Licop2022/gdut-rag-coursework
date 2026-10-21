"""Extract only handbook printed pages 193-198, retaining source provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
TITLE = "广东工业大学研究生奖学金评审办法"


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    from pypdf import PdfReader
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    reader = PdfReader(args.pdf)
    pages = []
    for number in range(196, 202):
        raw = reader.pages[number - 1].extract_text()
        assert TITLE in raw
        lines = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("广东工业大学研究生手册") or line == str(number - 3):
                continue
            if re.fullmatch(r"第[一二三四五六七八九十]+章\s*.*", line):
                continue
            lines.append(line)
        pages.append({"pdf_page": number, "printed_page": number - 3,
                      "raw_text": raw, "text": "".join(lines)})
    write_jsonl(data / "source_pages.jsonl", pages)
    combined = "".join(p["text"] for p in pages)
    matches = list(re.finditer(r"第[一二三四五六七八九十]+条", combined))
    assert len(matches) == 26, len(matches)
    articles = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(combined)
        text = combined[match.start():end]
        position = 0
        source = []
        for page in pages:
            page_end = position + len(page["text"])
            if match.start() < page_end and end > position:
                source.append({"pdf_page": page["pdf_page"], "printed_page": page["printed_page"]})
            position = page_end
        # Reconstruct merged-cell table rows explicitly; values were checked visually.
        if index == 4:
            text = ("第五条 研究生学业奖学金奖励标准：\n"
                    "类型 | 等级 | 金额 | 二年级及以上比例\n"
                    "博士生 | 一等奖 | 18000元/年 | 20%\n"
                    "博士生 | 二等奖 | 15000元/年 | 25%\n"
                    "博士生 | 三等奖 | 12000元/年 | 35%\n"
                    "硕士生 | 一等奖 | 10000元/年 | 20%\n"
                    "硕士生 | 二等奖 | 6000元/年 | 25%\n"
                    "硕士生 | 三等奖 | 2000元/年 | 35%\n"
                    "注：一年级研究生学业奖学金由研究生院根据当年研究生招生简章提出等级，不设固定比例。")
        articles.append({"id": f"A{index + 1:02d}", "article": match.group(), "title": TITLE,
                         "text": text, "source_pages": source})
    write_jsonl(data / "articles.jsonl", articles)
    chunks = []
    for article in articles:
        text = article["text"]
        for start in range(0, len(text), 320):
            end = min(start + 380, len(text))
            chunks.append({**article, "id": f"{article['id']}-C{sum(c.get('article_id') == article['id'] for c in chunks) + 1:02d}",
                           "article_id": article["id"], "start": start, "end": end, "text": text[start:end]})
            if end == len(text):
                break
    write_jsonl(data / "chunks.jsonl", chunks)
    metadata = {"source_name": args.pdf.name, "sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                "section": TITLE, "document_number": "广工大规字〔2023〕10号",
                "printed_pages": [193, 198], "pdf_pages": [196, 201], "articles": len(articles),
                "chunks": len(chunks), "chunk_size_unicode_characters": 380, "overlap_unicode_characters": 60,
                "notes": ["仅此节作为知识库；不含相邻国家奖学金及助学金办法。",
                          "第五条表格补全合并单元格中的博士生/硕士生类型，逐行保留金额及比例。",
                          "第七条原文有两个（六），保留，不擅自修改条目编号。",
                          "第十五条公式保留原文，跨页条款合并后再切分。",
                          "仅代表用户提供的2026手册版本，未核实后续政策变更。"]}
    (data / "source_manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = f"# {TITLE}\n\n文号：广工大规字〔2023〕10号。手册印刷页193-198，PDF页196-201。\n\n"
    markdown += "\n\n".join(f"## {a['id']} {a['article']}（印刷页{','.join(str(p['printed_page']) for p in a['source_pages'])}）\n\n{a['text']}" for a in articles)
    (data / "奖学金评审办法_核对正文.md").write_text(markdown + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
