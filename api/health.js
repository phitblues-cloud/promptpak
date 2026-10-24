// หน้าตรวจการตั้งค่า (แสดงแค่ว่าตั้งค่าแล้วหรือยัง ไม่เปิดเผยค่าลับ)
import { rpc } from '../lib/db.js';
import { json } from '../lib/http.js';

export async function GET() {
  const need = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'LINE_CHANNEL_SECRET',
    'LINE_CHANNEL_ACCESS_TOKEN', 'ANTHROPIC_API_KEY'];
  const env = Object.fromEntries(need.map(k => [k, Boolean(process.env[k])]));
  let database = 'ok';
  try {
    const d = await rpc('pp_dashboard', {});
    if (!d?.rooms_total) database = 'เชื่อมได้ แต่ยังไม่มีข้อมูลห้อง (ยังไม่ได้รัน 02_seed.sql)';
  } catch (e) { database = 'ผิดพลาด: ' + e.message; }
  return json({ env, database, model: process.env.ANTHROPIC_MODEL || 'claude-sonnet-5-5' });
}
