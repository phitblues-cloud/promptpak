// หน้าตรวจการตั้งค่า (แสดงแค่ว่าตั้งค่าแล้วหรือยัง ไม่เปิดเผยค่าลับ)
import { rpc } from '../lib/db.js';
import { json } from '../lib/http.js';

export async function GET() {
  const need = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'APP_SECRET', 'OWNER_PIN', 'STAFF_PIN', 'LINE_CHANNEL_SECRET',
    'LINE_CHANNEL_ACCESS_TOKEN', 'ANTHROPIC_API_KEY'];
  const env = Object.fromEntries(need.map(k => [k, Boolean(process.env[k])]));
  let database = 'ok';
  try {
    const d = await rpc('pp_availability', { p_check_in: '2030-01-01', p_check_out: '2030-01-02' });
    if (!d?.types?.length) database = 'เชื่อมได้ แต่ยังไม่มีข้อมูลห้อง (ยังไม่ได้รัน 02_seed.sql)';
  } catch (e) { database = 'ผิดพลาด: ' + e.message; }
  return json({ env, database, supabase_key_type: keyType(process.env.SUPABASE_SERVICE_ROLE_KEY), model: process.env.ANTHROPIC_MODEL || 'claude-sonnet-5-5' });
}

// บอกชนิดของคีย์ Supabase โดยไม่เปิดเผยตัวคีย์ (ต้องเป็น sb_secret หรือ jwt:service_role)
function keyType(k) {
  if (!k) return 'ไม่มี';
  k = k.trim();
  if (k.startsWith('sb_secret_')) return 'sb_secret (ถูกต้อง)';
  if (k.startsWith('sb_publishable_')) return 'sb_publishable (ผิดตัว: เป็นคีย์สาธารณะ)';
  const parts = k.split('.');
  if (parts.length === 3) {
    try {
      const role = JSON.parse(Buffer.from(parts[1], 'base64url').toString()).role;
      return 'jwt:' + role + (role === 'service_role' ? ' (ถูกต้อง)' : ' (ผิดตัว)');
    } catch { return 'jwt อ่านไม่ได้'; }
  }
  return 'ไม่รู้จักรูปแบบ (ยาว ' + k.length + ' ตัวอักษร ขึ้นต้น ' + k.slice(0, 3) + '…)';
}
