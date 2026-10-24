import { login } from '../lib/auth.js';
import { json } from '../lib/http.js';

export async function POST(request) {
  const { email, password } = await request.json().catch(() => ({}));
  if (!email || !password) return json({ error: 'กรอกอีเมลและรหัสผ่าน' }, 400);
  const r = await login(String(email).trim(), String(password));
  if (!r.ok) return json({ error: 'อีเมลหรือรหัสผ่านไม่ถูกต้อง' }, 401);
  return json({ ok: true }, 200, r.cookies);
}
