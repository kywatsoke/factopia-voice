"""A stand-in for llama-server used by the tests: same command-line shape, same
/health and /completion endpoints, and an answer that shows what it was asked.

    python fake_llama_server.py -m model.gguf --host 127.0.0.1 --port 1234 ... [--fail-gpu]
"""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


def main():
    args = sys.argv[1:]
    if "--version" in args:
        print("version: 0 (fake llama-server)")
        return
    port = int(args[args.index("--port") + 1])
    model = args[args.index("-m") + 1]
    gpu = args[args.index("-ngl") + 1] != "0"
    if gpu and os.environ.get("FAKE_LLAMA_FAIL_GPU"):
        sys.exit("no GPU here")
    if not os.path.exists(model):
        sys.exit("model not found")
    if gpu:
        print("llama_model_load_from_file_impl: using device FakeGPU (Fake GPU)", file=sys.stderr, flush=True)
    log = os.environ.get("FAKE_LLAMA_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"args": args}) + "\n")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.reply(200, {"status": "ok"}) if self.path == "/health" else self.reply(404, {})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if log:
                with open(log, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"prompt": body["prompt"], "gpu": gpu}) + "\n")
            target = re.search(r"into ([A-Za-z ()-]+?):", body["prompt"]).group(1)
            text = body["prompt"].split(":\n\n\n", 1)[1].split("<end_of_turn>")[0]
            self.reply(200, {"content": f'"[{target}] {text}"'})

    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
