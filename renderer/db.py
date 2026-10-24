# -*- coding: utf-8 -*-
"""เรียกฟังก์ชันในฐานข้อมูล Supabase (หรือ Postgres ในเครื่องตอนทดสอบ)"""
import json, os, subprocess, urllib.request, urllib.error


class DbError(Exception):
    pass


def _lit(v):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return "'" + s.replace("'", "''") + "'"


def rpc(name, args=None):
    args = args or {}
    if os.environ.get('LOCAL_PG'):
        params = ', '.join(f'{k} => {_lit(v)}' for k, v in args.items())
        r = subprocess.run(['psql', os.environ['LOCAL_PG'], '-q', '-t', '-A', '-v', 'ON_ERROR_STOP=1', '-c',
                            f'select to_jsonb({name}({params}))'], capture_output=True, text=True)
        if r.returncode:
            raise DbError(r.stderr.strip())
        out = r.stdout.strip()
        return json.loads(out) if out else None
    url, key = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise DbError('ยังไม่ได้ตั้งค่า SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY')
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    if not key.startswith('sb_'):
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(url.rstrip('/') + '/rest/v1/rpc/' + name, data=json.dumps(args).encode(),
                                 headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            body = res.read().decode()
    except urllib.error.HTTPError as e:
        raise DbError(e.read().decode()[:300])
    return json.loads(body) if body else None
