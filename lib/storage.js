// เก็บรูป/ไฟล์ในแชทไว้ที่ Supabase Storage (ถัง chat · เปิดสาธารณะ เพราะ LINE ต้องดึงรูปจากลิงก์)
import { randomBytes } from 'node:crypto';

const EXT = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif', 'application/pdf': 'pdf', 'video/mp4': 'mp4', 'audio/m4a': 'm4a' };

export async function uploadMedia(buf, contentType, ext) {
  const url = (process.env.SUPABASE_URL || '').trim(), key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  const type = contentType || 'application/octet-stream';
  if (!url || !key || process.env.LOCAL_PG) {   // เครื่องทดสอบ: เก็บเป็น data URL (เฉพาะไฟล์เล็ก)
    return buf.length < 400000 ? `data:${type};base64,${buf.toString('base64')}` : null;
  }
  const path = `${new Date().toISOString().slice(0, 10)}/${randomBytes(12).toString('hex')}.${ext || EXT[type] || 'bin'}`;
  const res = await fetch(`${url.replace(/\/$/, '')}/storage/v1/object/chat/${path}`, {
    method: 'POST',
    headers: { apikey: key, ...(key.startsWith('sb_') ? {} : { Authorization: `Bearer ${key}` }), 'Content-Type': type, 'x-upsert': 'true' },
    body: buf,
  });
  if (!res.ok) throw new Error('อัปโหลดไฟล์ไม่สำเร็จ ' + res.status + ' ' + (await res.text()).slice(0, 120));
  return `${url.replace(/\/$/, '')}/storage/v1/object/public/chat/${path}`;
}
