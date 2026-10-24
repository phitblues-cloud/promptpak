# หน้าจอ PROMPT PAK (v196) พร้อมข้อมูลจริง — Vercel Python Function
import os, sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'renderer'))
import web  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _run(self, method):
        q = parse_qs(urlparse(self.path).query)
        n = int(self.headers.get('content-length') or 0)
        body = self.rfile.read(n).decode() if n else ''
        ip = (self.headers.get('x-forwarded-for') or self.client_address[0] or '').split(',')[0].strip()
        status, headers, out = web.handle(method, q, self.headers.get('cookie'), body, ip)
        data = out.encode('utf-8')
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._run('GET')

    def do_POST(self):
        self._run('POST')
