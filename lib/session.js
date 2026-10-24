// ตรวจคุกกี้เข้าสู่ระบบ (ลายเซ็นเดียวกับ renderer/session.py)
import { createHmac, timingSafeEqual } from 'node:crypto';
import { getCookie } from './http.js';

export function roleFrom(request) {
  const v = getCookie(request, 'pp_sess') || '';
  const [role, exp, sig] = v.split('.');
  const secret = (process.env.APP_SECRET || '').trim();
  if (!secret || !role || !exp || !sig) return null;
  const good = createHmac('sha256', secret).update(`${role}.${exp}`).digest('hex');
  if (sig.length !== good.length || !timingSafeEqual(Buffer.from(sig), Buffer.from(good))) return null;
  if (Number(exp) * 1000 < Date.now() || !['owner', 'staff'].includes(role)) return null;
  return role;
}
