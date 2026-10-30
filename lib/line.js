// เชื่อม LINE Messaging API
import { createHmac, timingSafeEqual } from 'node:crypto';

const API = 'https://api.line.me/v2/bot';
const token = () => (process.env.LINE_CHANNEL_ACCESS_TOKEN || '').trim();

export function verifySignature(rawBody, signature) {
  const secret = (process.env.LINE_CHANNEL_SECRET || '').trim();
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

// ในกลุ่ม/ห้องแชท: ชื่อกลุ่ม และชื่อคนที่พิมพ์
export async function getGroupName(src) {
  if (globalThis.__ppLineOutbox) return src.type === 'group' ? 'กลุ่มทดสอบ' : null;
  if (src.type !== 'group') return null;
  try { return (await call(`/group/${encodeURIComponent(src.groupId)}/summary`, null, 'GET')).groupName || null; } catch { return null; }
}
export async function getMemberName(src) {
  if (!src.userId) return null;
  if (globalThis.__ppLineOutbox) return 'ผู้ทดสอบ';
  const base = src.type === 'group' ? `/group/${encodeURIComponent(src.groupId)}` : `/room/${encodeURIComponent(src.roomId)}`;
  try { return (await call(`${base}/member/${encodeURIComponent(src.userId)}`, null, 'GET')).displayName || null; } catch { return null; }
}

// ดึงรูป/ไฟล์ที่ลูกค้าส่งมา (LINE เก็บไว้ชั่วคราว ต้องดึงมาเก็บเอง)
export async function getContent(messageId) {
  if (globalThis.__ppLineOutbox) return { buf: Buffer.from('fake-image'), type: 'image/jpeg' };
  const res = await fetch(`https://api-data.line.me/v2/bot/message/${encodeURIComponent(messageId)}/content`, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!res.ok) throw new Error(`LINE content ${res.status}`);
  return { buf: Buffer.from(await res.arrayBuffer()), type: res.headers.get('content-type') || 'application/octet-stream' };
}

// ข้อความหลายรูปแบบ (การ์ด Flex / ปุ่มด่วน) — ตอบกลับ
export function replyMessages(replyToken, messages) {
  return call('/message/reply', { replyToken, messages: messages.slice(0, 5) });
}

// ส่งหาลูกค้าเอง (นับโควตาข้อความของ LINE OA)
export function push(to, messages) {
  return call('/message/push', { to, messages: messages.slice(0, 5) });
}

// ตรวจ ID token จากหน้าจอเด้ง (LIFF) → ได้ userId และชื่อจริงจาก LINE
export async function verifyIdToken(idToken) {
  if (process.env.LOCAL_DEV && String(idToken || '').startsWith('dev:')) return { sub: idToken.slice(4), name: 'ผู้ทดสอบ LIFF' };
  const cid = (process.env.LINE_LOGIN_CHANNEL_ID || '').trim();
  if (!cid) throw new Error('ยังไม่ได้ตั้งค่า LINE_LOGIN_CHANNEL_ID');
  const res = await fetch('https://api.line.me/oauth2/v2.1/verify', {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ id_token: String(idToken || ''), client_id: cid }),
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok || !j.sub) throw new Error('ยืนยันตัวตน LINE ไม่สำเร็จ กรุณาเปิดจากแอป LINE อีกครั้ง');
  return j;
}
