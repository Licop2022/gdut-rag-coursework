"""Authenticated loopback gateway for the HTTPS tunnel; never expose web_demo directly."""
import argparse
from collections import defaultdict, deque
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
ALLOWED_PATHS = {'/api/chunks', '/api/ask', '/api/compare'}
ORIGIN = 'https://licop2022.github.io'


def make_handler(key, upstream, allowed_origin=ORIGIN):
    active = threading.BoundedSemaphore(1)
    attempts = defaultdict(deque)
    throttle_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = 'GDUT-Gateway'

        def log_message(self, fmt, *args):
            # Never log request bodies, access keys or query strings.
            print(time.strftime('%Y-%m-%d %H:%M:%S'), self.command, self.path.split('?')[0], args[-1] if args else '', flush=True)

        def origin_ok(self):
            origin = self.headers.get('Origin', '')
            return not origin or origin.lower() == allowed_origin.lower()

        def reply(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            origin = self.headers.get('Origin', '')
            if origin and self.origin_ok():
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
                self.send_header('Access-Control-Max-Age', '600')
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            if not self.origin_ok(): return self.reply(403, {'error':'此网页来源不受允许'})
            if self.path not in ALLOWED_PATHS: return self.reply(404, {'error':'接口不存在'})
            self.reply(200, {'ok':True})

        def handle_api(self):
            if not self.origin_ok(): return self.reply(403, {'error':'此网页来源不受允许'})
            if self.path == '/health' and self.command == 'GET':
                try:
                    with urllib.request.urlopen(upstream+'/health', timeout=3) as r:
                        ready = bool(json.load(r).get('ready'))
                    return self.reply(200, {'ready':ready,'service':'gdut-9b-online'})
                except Exception:
                    return self.reply(503, {'ready':False,'error':'模型服务暂未就绪'})
            if self.path not in ALLOWED_PATHS:
                return self.reply(404, {'error':'接口不存在'})
            supplied = self.headers.get('Authorization', '')
            if not hmac.compare_digest(supplied.encode(), ('Bearer '+key).encode()):
                return self.reply(401, {'error':'访问密钥不正确，请重新连接'})
            if self.command == 'GET' and self.path != '/api/chunks':
                return self.reply(405, {'error':'请求方法不受支持'})
            body = None
            if self.command == 'POST':
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 16000: raise ValueError()
                    body = self.rfile.read(length)
                    if not isinstance(json.loads(body), dict): raise ValueError()
                except (ValueError, TypeError):
                    return self.reply(400, {'error':'请求必须为有效JSON对象，且不超过16000字节'})
                now = time.monotonic()
                with throttle_lock:
                    window = attempts['authenticated']
                    while window and window[0] < now-60: window.popleft()
                    if len(window) >= 10:
                        return self.reply(429, {'error':'请求较频繁，请稍后重试（每分钟最多10次）'})
                    window.append(now)
            if not active.acquire(blocking=False):
                return self.reply(409, {'error':'服务器正在处理上一条请求，请稍后重试'})
            try:
                req = urllib.request.Request(upstream+self.path, body,
                         headers={'Content-Type':'application/json'}, method=self.command)
                try:
                    with urllib.request.urlopen(req, timeout=115) as r:
                        response = json.load(r)
                        self.reply(r.status, response)
                except urllib.error.HTTPError as error:
                    # Retain validation messages, but hide internal model/system errors.
                    response = json.loads(error.read())
                    message = str(response.get('error','请求失败'))
                    if error.code not in [400,409] or len(message)>180:
                        message='模型服务处理失败，请稍后重试或联系部署者'
                    self.reply(error.code, {'error':message})
                except Exception:
                    self.reply(502, {'error':'模型服务连接中断或超时，请稍后重试'})
            finally:
                active.release()

        do_GET = handle_api
        do_POST = handle_api

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8767)
    args=parser.parse_args()
    key_path=ROOT/'.public-private/access.key'
    if os.name!='nt' and key_path.stat().st_mode & 0o077:
        raise RuntimeError('Access key file must have permission 600')
    key=key_path.read_text().strip()
    if len(key)<40: raise RuntimeError('A strong access key is required')
    endpoint=json.loads((ROOT/'cache/demo_endpoint.json').read_text())
    upstream=f"http://127.0.0.1:{int(endpoint['port'])}"
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(key,upstream))
    print(f'GATEWAY_READY 127.0.0.1:{args.port}',flush=True)
    server.serve_forever()


if __name__=='__main__': main()
