// AI เล่าตัวตนกลุ่มลูกค้า (CRM › ภาพรวมลูกค้า › ป๊อปอัปกลุ่มลูกค้า) · POST {segs:{B,W3,L}} · เจ้าของ/พนักงานที่ล็อกอินแล้ว
import { roleFrom } from '../lib/session.js';
import { segmentStory } from '../lib/segment.js';
import { json, errorJson } from '../lib/http.js';

export async function POST(request) {
  if (!roleFrom(request)) return json({ error: 'ต้องเข้าสู่ระบบ' }, 401);
  let body;
  try { body = await request.json(); } catch { return json({ error: 'ข้อมูลไม่ถูกต้อง' }, 400); }
  try { return json(await segmentStory(body)); } catch (e) { return errorJson(e); }
}
