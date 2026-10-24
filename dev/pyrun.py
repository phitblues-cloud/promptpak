# ตัวเรียก api/app.py ในเครื่อง (ใช้โดย dev/server.mjs)
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'renderer'))
import web
from urllib.parse import parse_qs
r = json.load(sys.stdin)
st, h, body = web.handle(r['method'], parse_qs(r['query']), r.get('cookie'), r.get('body'), r.get('ip', '127.0.0.1'))
json.dump({'status': st, 'headers': h, 'body': body}, sys.stdout, ensure_ascii=False)
