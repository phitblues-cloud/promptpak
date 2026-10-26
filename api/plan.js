// แผนการตลาดจาก AI (ศูนย์ไอเดีย) · POST {mode:'new'|'revise', items[], segments[], promos[], price, ask?, plan?}
import { roleFrom } from '../lib/session.js';
import { makePlans } from '../lib/plan.js';
import { json, errorJson } from '../lib/http.js';

export async function POST(request) {
  if (!roleFrom(request)) return json({ error: 'ต้องเข้าสู่ระบบ' }, 401);
  let body;
  try { body = await request.json(); } catch { return json({ error: 'ข้อมูลไม่ถูกต้อง' }, 400); }
  try { return json(await makePlans(body)); } catch (e) { return errorJson(e); }
}
