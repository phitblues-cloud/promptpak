// ล็อกอินจริงด้วย Supabase Auth (อีเมล + รหัสผ่าน) เก็บสถานะในคุกกี้ HttpOnly
import { getCookie, cookie, json } from './http.js';

const AT = 'pp_at', RT = 'pp_rt';
const base = () => (process.env.SUPABASE_URL || '').replace(/\/$/, '');
const anon = () => process.env.SUPABASE_ANON_KEY || '';

async function gotrue(path, body) {
  const res = await fetch(`${base()}/auth/v1/${path}`, {
    method: 'POST', headers: { apikey: anon(), 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
}

function sessionCookies(s) {
  return [cookie(AT, s.access_token, s.expires_in || 3600), cookie(RT, s.refresh_token, 60 * 60 * 24 * 30)];
}

export async function login(email, password) {
  if (process.env.LOCAL_DEV) {
    if (email === 'demo@local' && password === 'demo')
      return { ok: true, cookies: sessionCookies({ access_token: 'dev', refresh_token: 'dev' }) };
    return { ok: false };
  }
  const r = await gotrue('token?grant_type=password', { email, password });
  if (!r.ok) return { ok: false };
  return { ok: true, cookies: sessionCookies(r.data) };
}

export function logoutCookies() { return [cookie(AT, '', 0), cookie(RT, '', 0)]; }

async function getUser(token) {
  const res = await fetch(`${base()}/auth/v1/user`, { headers: { apikey: anon(), Authorization: `Bearer ${token}` } });
  return res.ok ? res.json() : null;
}

// คืน { user, cookies } หรือ { response } (401) ถ้ายังไม่ได้ล็อกอิน
export async function requireUser(request) {
  const at = getCookie(request, AT), rt = getCookie(request, RT);
  if (process.env.LOCAL_DEV) {
    return at === 'dev' || rt === 'dev' ? { user: { email: 'demo@local' }, cookies: [] }
      : { response: json({ error: 'ต้องล็อกอิน' }, 401) };
  }
  if (at) {
    const u = await getUser(at).catch(() => null);
    if (u) return { user: u, cookies: [] };
  }
  if (rt) {
    const r = await gotrue('token?grant_type=refresh_token', { refresh_token: rt });
    if (r.ok) return { user: r.data.user, cookies: sessionCookies(r.data) };
  }
  return { response: json({ error: 'ต้องล็อกอิน' }, 401, logoutCookies()) };
}
