#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 8133
SECRET_TOKEN = "YOUR_SECRET_TOKEN"
META_FEED_PATH = Path("/opt/kameleon/orchestrator/meta_feed.json")


class CommandHandler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            if META_FEED_PATH.exists():
                try:
                    with open(META_FEED_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._set_headers(200)
                    self.wfile.write(
                        json.dumps({"status": "ok", "meta": data}).encode()
                    )
                except Exception as e:
                    self._set_headers(500)
                    self.wfile.write(
                        json.dumps({"status": "error", "message": str(e)}).encode()
                    )
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"status": "not available"}).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"status": "not found"}).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0 or content_length > 4096:
                self._set_headers(400)
                self.wfile.write(
                    json.dumps({"status": "invalid content length"}).encode()
                )
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            command = data.get("command", "").lower()
            token = data.get("token", "")

            if token != SECRET_TOKEN:
                self._set_headers(403)
                self.wfile.write(json.dumps({"status": "unauthorized"}).encode())
                return

            if command == "distill":
                subprocess.Popen(
                    ["python3", "-m", "distillation_engine"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                response = {"status": "distillation started"}

            elif command == "lockdown":
                subprocess.Popen(
                    [
                        "python3",
                        "/media/4tb/Kameleon/cell/system/super-orkestrator.py",
                        "lockdown",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                response = {"status": "lockdown activated"}

            elif command == "snapshot":
                subprocess.Popen(
                    [
                        "python3",
                        "/media/4tb/Kameleon/cell/system/super-orkestrator.py",
                        "snapshot_create",
                        "bridge",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                response = {"status": "snapshot triggered"}

            else:
                response = {"status": "unknown command"}

            self._set_headers(200)
            response_bytes = json.dumps(response).encode()
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(
                json.dumps({"status": "error", "message": str(e)}).encode()
            )


def run(server_class=HTTPServer, handler_class=CommandHandler):
    server_address = ("127.0.0.1", PORT)
    httpd = server_class(server_address, handler_class)
    print(f"[+] WebUI command bridge teče na http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
