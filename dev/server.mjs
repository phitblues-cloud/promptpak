// เซิร์ฟเวอร์ทดสอบในเครื่อง (จำลอง Vercel): เสิร์ฟ public/ + เรียก api/*.js
// ใช้: LOCAL_DEV=1 LOCAL_PG=postgres://... node dev/server.mjs
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json' };
const port = Number(process.env.PORT || 3000);

export function createServer() {
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://localhost:${port}`);
      if (url.pathname === '/' || url.pathname === '/api/app') {   // ฟังก์ชัน Python (หน้าจอ v196)
        const chunks = []; for await (const c of req) chunks.push(c);
        const r = spawnSync('python3', [path.join(root, 'dev', 'pyrun.py')], { input: JSON.stringify({ method: req.method,
          query: url.search.slice(1), cookie: req.headers.cookie || '', body: Buffer.concat(chunks).toString() }),
          encoding: 'utf8', maxBuffer: 64 << 20, env: process.env });
        if (r.status !== 0) { res.writeHead(500).end(r.stderr); return; }
        const o = JSON.parse(r.stdout);
        res.writeHead(o.status, o.headers).end(o.body);
        return;
      }
      if (url.pathname.startsWith('/api/')) {
        const name = url.pathname.slice(5).replace(/[^a-z0-9-]/gi, '');
        const mod = await import(pathToFileURL(path.join(root, 'api', name + '.js')).href);
        const fn = mod[req.method];
        if (!fn) { res.writeHead(405).end(); return; }
        const chunks = []; for await (const c of req) chunks.push(c);
        const body = chunks.length ? Buffer.concat(chunks) : undefined;
        const request = new Request(url, { method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : body });
        const r = await fn(request);
        const headers = {};
        r.headers.forEach((v, k) => { if (k !== 'set-cookie') headers[k] = v; });
        const sc = r.headers.getSetCookie?.() || [];
        if (sc.length) headers['set-cookie'] = sc;
        res.writeHead(r.status, headers).end(Buffer.from(await r.arrayBuffer()));
        return;
      }
      let p = url.pathname === '/' ? '/index.html' : url.pathname;
      if (!path.extname(p)) p += '.html';
      const file = path.join(root, 'public', path.normalize(p));
      if (!file.startsWith(path.join(root, 'public'))) { res.writeHead(403).end(); return; }
      const data = await readFile(file);
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' }).end(data);
    } catch (e) {
      if (e.code === 'ENOENT') { res.writeHead(404).end('not found'); return; }
      console.error(e); res.writeHead(500).end(String(e));
    }
  });
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  createServer().listen(port, () => console.log(`http://localhost:${port}`));
}
