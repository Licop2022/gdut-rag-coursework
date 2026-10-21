"""Download public ModelScope mirrors with per-file SHA256 verification."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
MODELS = {"generator": "Qwen/Qwen3.5-9B", "embedding": "BAAI/bge-m3", "reranker": "BAAI/bge-reranker-v2-m3"}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(task):
    role, repo, entry = task
    path = ROOT / "models" / role / entry["Path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    expected, size = entry["Sha256"], entry["Size"]
    if path.exists() and path.stat().st_size == size and sha256(path) == expected:
        print("Verified existing", role, path.name, flush=True)
        return
    url = f"https://modelscope.cn/models/{repo}/resolve/{entry['Revision']}/{urllib.parse.quote(entry['Path'])}"
    partial = path.with_name(path.name + ".part")
    for attempt in range(5):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {"User-Agent": "GDUT-RAG-Coursework/1.0"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
                append = offset > 0 and response.status == 206
                if not append:
                    offset = 0
                with partial.open("ab" if append else "wb") as output:
                    last = offset
                    while block := response.read(4 * 1024 * 1024):
                        output.write(block)
                        offset += len(block)
                        if offset - last >= 512 * 1024 * 1024:
                            print(role, path.name, f"{offset / size:.0%}", flush=True)
                            last = offset
            if partial.stat().st_size != size or sha256(partial) != expected:
                partial.unlink(missing_ok=True)
                raise RuntimeError("Size or SHA256 mismatch: " + path.name)
            partial.replace(path)
            print("Verified", role, path.name, size, flush=True)
            return
        except Exception as error:
            print("Retry", role, path.name, attempt + 1, type(error).__name__, flush=True)
            if attempt == 4:
                raise
            time.sleep(3)


def main():
    manifest = {}
    tasks = []
    allowed = {"config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
               "vocab.txt", "vocab.json", "merges.txt", "sentencepiece.bpe.model", "tokenizer.model",
               "preprocessor_config.json", "processor_config.json", "chat_template.jinja", "model.safetensors.index.json"}
    for role, repo in MODELS.items():
        url = f"https://modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true"
        with urllib.request.urlopen(url, timeout=60) as response:
            metadata = json.load(response)
        entries = [e for e in metadata["Data"]["Files"] if e["Type"] == "blob" and "/" not in e["Path"]
                   and (e["Path"] in allowed or e["Path"].endswith(".safetensors")
                        or (role == "embedding" and e["Path"] == "pytorch_model.bin"))]
        if not any(e["Path"].endswith(".safetensors") for e in entries) and not (role == "embedding" and any(e["Path"] == "pytorch_model.bin" for e in entries)):
            raise RuntimeError("No safetensors weights for " + repo)
        manifest[role] = {"repo": repo, "source": "ModelScope public mirror", "entries": entries}
        tasks += [(role, repo, e) for e in entries]
    (ROOT / "models").mkdir(exist_ok=True)
    (ROOT / "models" / "download_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Total GB", round(sum(e[2]["Size"] for e in tasks) / 1e9, 2), "files", len(tasks), flush=True)
    # Download small metadata first so model configuration is available for diagnostics.
    tasks.sort(key=lambda item: item[2]["Size"])
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        list(pool.map(fetch, tasks))
    # The official BGE-M3 mirror only provides a PyTorch state dictionary.
    # Load with the restricted weights-only unpickler and convert to safetensors.
    source = ROOT / "models/embedding/pytorch_model.bin"
    destination = ROOT / "models/embedding/model.safetensors"
    if source.exists() and not destination.exists():
        import torch
        from safetensors.torch import save_file
        state = torch.load(source, map_location="cpu", weights_only=True, mmap=True)
        save_file({name: tensor.contiguous().clone() for name, tensor in state.items()}, str(destination), metadata={"format": "pt"})
        del state
    if destination.exists():
        manifest["embedding"]["converted_safetensors"] = {"sha256": sha256(destination), "bytes": destination.stat().st_size,
                "conversion": "torch.load(weights_only=True,mmap=True) -> safetensors"}
        (ROOT / "models/download_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "models" / "DOWNLOAD_COMPLETE").write_text("All manifest SHA256 values verified.\n", encoding="utf-8")
    print("MODEL_DOWNLOAD_COMPLETED", flush=True)


if __name__ == "__main__":
    main()
