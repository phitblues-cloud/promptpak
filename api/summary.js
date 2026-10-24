// AI สรุปให้เจ้าของ (แสดงในกล่อง "สถานการณ์ลูกค้าตอนนี้" ของ CRM)
import { roleFrom } from '../lib/session.js';
import { ownerSummary } from '../lib/ai.js';
import { json, errorJson } from '../lib/http.js';

export async function POST(request) {
  if (!roleFrom(request)) return json({ error: 'ต้องเข้าสู่ระบบ' }, 401);
  try {
    return json(await ownerSummary());
  } catch (e) { return errorJson(e); }
}
