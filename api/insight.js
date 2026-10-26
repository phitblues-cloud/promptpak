// ศูนย์ไอเดีย: Agent Insight วิเคราะห์ข้อมูลจริง (วันละครั้ง)
// GET = ใช้ผลล่าสุด (สร้างใหม่ถ้าหมดรอบ) · POST {force:true} = เจ้าของสั่งทำใหม่
import { roleFrom } from '../lib/session.js';
import { feed } from '../lib/feed.js';
import { json, errorJson } from '../lib/http.js';

export async function GET(request) {
  if (!roleFrom(request)) return json({ error: 'ต้องเข้าสู่ระบบ' }, 401);
  try { return json(await feed('insight')); } catch (e) { return errorJson(e); }
}

export async function POST(request) {
  const role = roleFrom(request);
  if (!role) return json({ error: 'ต้องเข้าสู่ระบบ' }, 401);
  if (role !== 'owner') return json({ error: 'เฉพาะเจ้าของเท่านั้น' }, 403);
  try { return json(await feed('insight', { force: true })); } catch (e) { return errorJson(e); }
}
