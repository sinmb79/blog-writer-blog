"""
Tistory OAuth2 토큰 발급 스크립트

사용법:
    python scripts/get_tistory_token.py

완료 후 .env에 자동으로 아래 항목이 추가됩니다:
    TISTORY_CLIENT_ID=...
    TISTORY_CLIENT_SECRET=...
    TISTORY_ACCESS_TOKEN=...
    TISTORY_BLOG_NAME=...
"""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import dotenv_values, set_key

REDIRECT_URI = "http://localhost:5000/callback"
AUTH_URL = "https://www.tistory.com/oauth/authorize"
TOKEN_URL = "https://www.tistory.com/oauth/access_token"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

_auth_code: str | None = None
_server_done = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs:
            _auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h2>&#10003; Tistory \xec\x9d\xb8\xec\xa6\x9d \xec\x99\x84\xeb\xa3\x8c!</h2>"
                b"<p>\xec\xb0\xbd\xec\x9d\x84 \xeb\x8b\xab\xec\x95\x84\xeb\x8f\x84 \xeb\x90\xa9\xeb\x8b\x88\xeb\x8b\xa4.</p>"
            )
        else:
            self.send_response(400)
            self.end_headers()
        _server_done.set()

    def log_message(self, *args):
        pass


def _start_server():
    srv = HTTPServer(("localhost", 5000), _CallbackHandler)
    srv.handle_request()


def main():
    env = dotenv_values(ENV_PATH)
    client_id = env.get("TISTORY_CLIENT_ID") or os.environ.get("TISTORY_CLIENT_ID", "")
    client_secret = env.get("TISTORY_CLIENT_SECRET") or os.environ.get("TISTORY_CLIENT_SECRET", "")

    if not client_id:
        client_id = input("TISTORY_CLIENT_ID (Kakao REST API 키): ").strip()
    if not client_secret:
        client_secret = input("TISTORY_CLIENT_SECRET (Kakao Client Secret): ").strip()

    params = urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
    })
    auth_url = f"{AUTH_URL}?{params}"

    print("\n브라우저에서 Kakao/Tistory 로그인 후 권한을 허용해주세요...")
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()
    webbrowser.open(auth_url)
    _server_done.wait(timeout=120)

    if not _auth_code:
        print("[ERROR] 인증 코드를 받지 못했습니다.")
        sys.exit(1)

    print(f"인증 코드 수신: {_auth_code[:10]}...")

    resp = requests.get(TOKEN_URL, params={
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "code": _auth_code,
        "grant_type": "authorization_code",
    }, timeout=15)

    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if not data:
        # Tistory sometimes returns query-string format
        data = dict(parse_qs(resp.text))
        data = {k: v[0] for k, v in data.items()}

    access_token = data.get("access_token", "")
    if not access_token:
        print(f"[ERROR] 토큰 발급 실패: {resp.text}")
        sys.exit(1)

    print(f"Access Token 발급 완료: {access_token[:15]}...")

    # 블로그 정보 조회
    info = requests.get("https://www.tistory.com/apis/blog/info", params={
        "access_token": access_token,
        "output": "json",
    }, timeout=10).json()

    blogs = info.get("tistory", {}).get("item", {}).get("blogs", {}).get("blog", [])
    if isinstance(blogs, dict):
        blogs = [blogs]

    blog_name = ""
    if blogs:
        print("\n등록된 블로그 목록:")
        for i, b in enumerate(blogs):
            print(f"  {i+1}. {b.get('name')} — {b.get('url')}")
        if len(blogs) == 1:
            blog_name = blogs[0].get("name", "")
        else:
            idx = input("사용할 블로그 번호: ").strip()
            blog_name = blogs[int(idx) - 1].get("name", "")

    # .env에 저장
    set_key(str(ENV_PATH), "TISTORY_CLIENT_ID", client_id)
    set_key(str(ENV_PATH), "TISTORY_CLIENT_SECRET", client_secret)
    set_key(str(ENV_PATH), "TISTORY_ACCESS_TOKEN", access_token)
    if blog_name:
        set_key(str(ENV_PATH), "TISTORY_BLOG_NAME", blog_name)

    print(f"\n.env 저장 완료:")
    print(f"  TISTORY_ACCESS_TOKEN={access_token[:15]}...")
    print(f"  TISTORY_BLOG_NAME={blog_name}")
    print("\nTistory 발행 준비 완료!")


if __name__ == "__main__":
    main()
