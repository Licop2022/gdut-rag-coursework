"""Versioned live chunk configurations; original experiment data stays immutable."""
import hashlib
import json
import os
from pathlib import Path
import re
import time


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def build_chunks(articles, size, overlap):
    if type(size) is not int or not 80 <= size <= 800:
        raise ValueError("chunk 长度必须是 80—800 的整数")
    if type(overlap) is not int or not 0 <= overlap <= size // 2:
        raise ValueError("重叠长度必须是 0 到 chunk 长度一半之间的整数")
    chunks = []
    for article in articles:
        text = article["text"]
        for number, start in enumerate(range(0, len(text), size - overlap), 1):
            end = min(start + size, len(text))
            chunks.append({**article, "id": f"{article['id']}-C{number:02d}",
                           "article_id": article["id"], "start": start, "end": end, "text": text[start:end]})
            if end == len(text):
                break
    return chunks


class ChunkStore:
    def __init__(self, root):
        self.root = Path(root)
        self.folder = self.root / "runs/live_chunks"
        self.pointer = self.root / "cache/live_chunk_version.json"
        self.articles = read_jsonl(self.root / "data/articles.jsonl")

    def original(self):
        return {"config": {"version": "original", "chunk_size": 380, "overlap": 60,
                           "created_at": None}, "chunks": read_jsonl(self.root / "data/chunks.jsonl")}

    def active(self):
        if not self.pointer.exists():
            return self.original()
        version = json.loads(self.pointer.read_text(encoding="utf-8"))["version"]
        if version == "original":
            return self.original()
        if not re.fullmatch(r"[0-9a-f]{24}", version):
            raise ValueError("Invalid saved chunk version")
        return json.loads((self.folder / f"{version}.json").read_text(encoding="utf-8"))

    def preview(self, size, overlap):
        chunks = build_chunks(self.articles, size, overlap)
        return {"config": {"chunk_size": size, "overlap": overlap}, "chunks": chunks}

    def commit(self, snapshot):
        config = dict(snapshot["config"])
        if config.get("version") != "original":
            config["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            config["articles_sha256"] = hashlib.sha256((self.root / "data/articles.jsonl").read_bytes()).hexdigest()
            config["version"] = hashlib.sha256((json.dumps(snapshot, ensure_ascii=False) + str(time.time_ns())).encode()).hexdigest()[:24]
            snapshot = {"config": config, "chunks": snapshot["chunks"]}
            self.folder.mkdir(parents=True, exist_ok=True)
            (self.folder / f"{config['version']}.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        self.pointer.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.pointer.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": config["version"]}), encoding="utf-8")
        os.replace(temporary, self.pointer)
        return snapshot
