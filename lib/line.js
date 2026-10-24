// เชื่อม LINE Messaging API
import { createHmac, timingSafeEqual } from 'node:crypto';

const API = 'https://api.line.me/v2/bot';
const token = () => process.env.LINE_CHANNEL_ACCESS_TOKEN || '';

export function verifySignature(rawBody, signature) {
  const secret = process.env.LINE_CHANNEL_SECRET;
  if (!secret || !signature) return false;
  const expected = createHmac('sha256', secret).update(rawBody).digest();
  let got;
  try { got = Buffer.from(signature, 'base64'); } catch { return false; }
  return got.length === expected.length && timingSafeEqual(got, expected);
}

async function call(path, body, method = 'POST') {
  if (globalThis.__ppLineOutbox) { globalThis.__ppLineOutbox.push({ path, body }); return {}; } // โหมดทดสอบ
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { Authorization: `Bearer ${token()}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`LINE ${path} ${res.status}: ${await res.text()}`);
  const t = await res.text();
  return t ? JSON.parse(t) : {};
}

// ตอบกลับ (ฟรี ไม่นับโควตา) — ข้อความละไม่เกิน 5,000 ตัวอักษร สูงสุด 5 ข้อความ
export function reply(replyToken, texts) {
  const messages = (Array.isArray(texts) ? texts : [texts]).filter(Boolean).slice(0, 5)
    .map(t => ({ type: 'text', text: String(t).slice(0, 4900) }));
  return call('/message/reply', { replyToken, messages });
}

// แสดงจุดกำลังพิมพ์ระหว่างรอ AI (สูงสุด 60 วินาที)
export function showLoading(userId, seconds = 30) {
  return call('/chat/loading/start', { chatId: userId, loadingSeconds: seconds }).catch(() => {});
}

export async function getProfile(userId) {
  if (globalThis.__ppLineOutbox) return { displayName: 'ผู้ทดสอบ' };
  try { return await call(`/profile/${encodeURIComponent(userId)}`, null, 'GET'); } catch { return {}; }
}
