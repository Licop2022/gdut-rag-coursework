"""Single-request local web demo; access through an SSH tunnel."""
import argparse
import errno
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time

from engine import ROOT, SETTINGS, Generator, Retriever, gpu_guard, save_json
from chunk_config import ChunkStore
from chunk_compare import run_comparison

HTML = (ROOT / "demo.html").read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--adapter", type=Path)
    args = parser.parse_args()
    gpu_guard()
    store = ChunkStore(ROOT)
    active = store.active()
    retriever, generator = Retriever(active["chunks"]), Generator(args.adapter)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, payload, content_type="application/json; charset=utf-8"):
            data = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                self.respond(200, HTML, "text/html; charset=utf-8")
            elif self.path == "/health":
                self.respond(200, {"ready": True, "project": "gdut-scholarship-9b-20261021", "model": "Qwen3.5-9B", "adapter_available": bool(args.adapter), "chunk_editor": True, "chunk_compare": True})
            elif self.path == "/api/chunks":
                if not lock.acquire(blocking=False):
                    self.respond(409, {"error": "正在处理问答或索引，请稍后重试"})
                    return
                try:
                    self.respond(200, active)
                finally:
                    lock.release()
            else:
                self.respond(404, {"error": "Not found"})

        def do_POST(self):
            nonlocal active
            if self.path not in ["/api/ask", "/api/chunks", "/api/compare"]:
                self.respond(404, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16000:
                    raise ValueError("请求长度不正确")
                request = json.loads(self.rfile.read(length))
                if self.path == "/api/chunks":
                    if not lock.acquire(blocking=False):
                        self.respond(409, {"error": "正在处理问答或索引，请稍后重试"})
                        return
                    try:
                        action = request.get("action")
                        if action not in ["preview", "apply", "reset"]:
                            raise ValueError("未知分块操作")
                        if action != "preview" and request.get("expected_version") != active["config"]["version"]:
                            self.respond(409, {"error": "分块配置已变化，请刷新页面后重试"})
                            return
                        snapshot = store.original() if action == "reset" else store.preview(request.get("chunk_size"), request.get("overlap"))
                        if action != "preview":
                            prepared = retriever.prepare_index(snapshot["chunks"])
                            committed = store.commit(snapshot)
                            retriever.use_index(prepared)
                            active = committed
                        self.respond(200, snapshot if action == "preview" else active)
                    finally:
                        lock.release()
                    return
                question = str(request.get("question", "")).strip()
                if not question or len(question) > 1000:
                    raise ValueError("请输入不超过1000字的问题")
                use_lora = bool(request.get("lora"))
                if use_lora and not args.adapter:
                    raise ValueError("当前服务尚未加载LoRA adapter")
                if not lock.acquire(blocking=False):
                    self.respond(409, {"error": "正在处理上一条问题，请稍后"})
                    return
                try:
                    if self.path == "/api/compare":
                        result = run_comparison(store, retriever, generator, question, request.get('profiles'),
                                                request.get('route', 'rerank'), use_lora, SETTINGS)
                        result['active_chunk_config'] = dict(active['config'])
                        result['run_id'] = str(time.time_ns())
                        save_json(ROOT / 'runs' / 'chunk_compare' / (result['run_id'] + '.json'), result)
                        self.respond(200, result)
                        return
                    if request.get("expected_version", active["config"]["version"]) != active["config"]["version"]:
                        self.respond(409, {"error": "分块配置已变化，请刷新页面后重新提问"})
                        return
                    result = retriever.retrieve(question)
                    result["chunk_config"] = dict(active["config"])
                    for route in ["baseline", "rerank"]:
                        result[route + "_generation"] = generator.generate(question, result[route + "_context"], use_adapter=use_lora)
                    result["used_lora"] = use_lora
                    save_json(ROOT / "runs" / "live" / f"{time.time_ns()}.json", result)
                finally:
                    lock.release()
                self.respond(200, result)
            except Exception as error:
                self.respond(400, {"error": str(error)})

    server = None
    for port in range(args.port, args.port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise
    if server is None:
        raise RuntimeError("No available local demo port in requested range")
    port = server.server_address[1]
    save_json(ROOT / "cache/demo_endpoint.json", {"host": "127.0.0.1", "port": port, "ready": True})
    print(f"DEMO_READY http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
