// เรียกฟังก์ชันในฐานข้อมูล (Supabase RPC) จากหลังบ้านเท่านั้น
import { execFileSync } from 'node:child_process';

export class DbError extends Error {}

export async function rpc(name, args = {}) {
  if (process.env.LOCAL_PG) return localRpc(name, args); // โหมดทดสอบในเครื่อง
  const url = (process.env.SUPABASE_URL || '').trim(), key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) throw new DbError('ยังไม่ได้ตั้งค่า SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY');
  const res = await fetch(`${url.replace(/\/$/, '')}/rest/v1/rpc/${name}`, {
    method: 'POST',
    // คีย์แบบใหม่ (sb_secret_...) ส่งใน apikey อย่างเดียว / คีย์แบบเก่า (JWT) ส่งทั้งสองที่
    headers: { apikey: key, ...(key.startsWith('sb_') ? {} : { Authorization: `Bearer ${key}` }), 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });
  const text = await res.text();
  if (!res.ok) {
    let msg = text;
    try { msg = JSON.parse(text).message || text; } catch {}
    throw new DbError(msg);
  }
  return text ? JSON.parse(text) : null;
}

function lit(v) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'number') return String(v);
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  const s = typeof v === 'string' ? v : JSON.stringify(v);
  return `'${s.replace(/'/g, "''")}'`;
}

function localRpc(name, args) {
  const params = Object.entries(args).map(([k, v]) => `${k} => ${lit(v)}`).join(', ');
  const sql = `select to_jsonb(${name}(${params}))`;
  try {
    const out = execFileSync('psql', [process.env.LOCAL_PG, '-q', '-t', '-A', '-v', 'ON_ERROR_STOP=1', '-c', sql],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
    return out ? JSON.parse(out) : null;
  } catch (e) {
    const m = /ERROR:\s+(.*)/.exec(String(e.stderr || e.message));
    throw new DbError(m ? m[1] : String(e.message));
  }
}
