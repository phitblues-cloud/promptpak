// รับข้อความจาก LINE OA → บันทึก (ข้อความ/สติกเกอร์/รูป/ไฟล์) → แจ้งพนักงานตอบเอง
// AI ไม่ตอบลูกค้าอัตโนมัติ (เจ้าของไม่ต้องการแชทบอท) · เปิดได้ด้วย AI_AUTOREPLY=1
import { verifySignature, reply, showLoading, getProfile, getContent } from '../lib/line.js';
import { uploadMedia } from '../lib/storage.js';
import { rpc } from '../lib/db.js';
import { bookingAgent } from '../lib/ai.js';

const AI_ON = () => process.env.AI_AUTOREPLY === '1';
const WELCOME_AI = 'สวัสดีค่ะ ยินดีต้อนรับสู่ พบรักรีสอร์ท 🙏\nจองห้องได้ทางแชทนี้เลยค่ะ พิมพ์วันเข้าพัก วันออก และจำนวนห้องที่ต้องการ เช่น "ขอห้องตึก 2 ห้อง 27-29 ต.ค."';
const WELCOME = 'สวัสดีค่ะ ขอบคุณที่เพิ่มเพื่อน พบรักรีสอร์ท 🙏 สอบถามหรือจองห้องพิมพ์มาได้เลยค่ะ พนักงานจะตอบกลับโดยเร็วค่ะ';

// ป้ายข้อความ + ข้อมูลแนบ ของข้อความที่ไม่ใช่ตัวอักษร
async function mediaOf(m) {
  if (m.type === 'sticker') return { body: '[สติกเกอร์]', meta: { type: 'sticker', pkg: m.packageId, sid: m.stickerId } };
  if (m.type === 'location') return { body: `[ตำแหน่ง] ${m.title || ''} ${m.address || ''}`.trim(), meta: { type: 'location', lat: m.latitude, lng: m.longitude } };
  if (['image', 'video', 'audio', 'file'].includes(m.type)) {
    const label = { image: '[รูปภาพ]', video: '[วิดีโอ]', audio: '[ข้อความเสียง]', file: `[ไฟล์] ${m.fileName || ''}`.trim() }[m.type];
    let url = null, err = null;
    try {
      const c = await getContent(m.id);
      const ext = m.type === 'file' ? (String(m.fileName || '').split('.').pop() || 'bin').slice(0, 8) : null;
      url = await uploadMedia(c.buf, c.type, ext);
    } catch (e) { err = String(e.message).slice(0, 120); }
    return { body: label, meta: { type: m.type, url, name: m.fileName || null, size: m.fileSize || null, err } };
  }
  return { body: `[${m.type || 'ข้อความ'}]`, meta: { type: m.type || 'unknown' } };
}

async function handleEvent(ev) {
  const userId = ev.source?.userId;
  if (!userId) return;
  if (ev.webhookEventId && (await rpc('pp_event_seen', { p_event_id: ev.webhookEventId }))) return; // ซ้ำ ข้าม
  const profile = await getProfile(userId);
  const name = profile.displayName || null;

  if (ev.type === 'follow') {
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ระบบ', p_body: '(เพิ่มเพื่อน LINE OA)' });
    const w = AI_ON() ? WELCOME_AI : WELCOME;
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ระบบ', p_body: w });
    if (ev.replyToken) await reply(ev.replyToken, w);
    return;
  }
  if (ev.type !== 'message') return;

  if (ev.message?.type !== 'text') {
    const { body, meta } = await mediaOf(ev.message || {});
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ลูกค้า', p_body: body, p_meta: meta });
    await rpc('pp_handoff', { p_line_user_id: userId, p_reason: 'ลูกค้าส่ง' + body });
    return;
  }

  await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ลูกค้า', p_body: ev.message.text });

  // ไม่มีแชทบอท: ทุกข้อความรอพนักงานตอบจากหน้า "แชทลูกค้า LINE"
  if (!AI_ON()) { await rpc('pp_handoff', { p_line_user_id: userId, p_reason: 'ลูกค้าทักมา' }); return; }

  // ถ้าเรื่องนี้ส่งต่อพนักงานแล้ว AI จะเงียบ ให้พนักงานตอบเองใน LINE OA (AI กลับมาตอบเองหลัง 6 ชั่วโมง)
  if (await rpc('pp_staff_active', { p_line_user_id: userId })) return;

  await showLoading(userId, 40);
  let text, actions = [];
  try {
    ({ text, actions } = await bookingAgent(userId, name));
  } catch (e) {
    console.error('AI error', e);
    text = 'ขออภัยค่ะ ระบบตอบอัตโนมัติขัดข้องชั่วคราว พนักงานจะติดต่อกลับโดยเร็วค่ะ 🙏';
    await rpc('pp_handoff', { p_line_user_id: userId, p_reason: 'AI ขัดข้อง: ' + String(e.message).slice(0, 120) }).catch(() => {});
  }
  await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'AI', p_body: text, p_meta: actions.length ? { actions } : null });
  await reply(ev.replyToken, text);
}

export async function handleEvents(events) {
  for (const ev of events) {
    try { await handleEvent(ev); } catch (e) { console.error('event failed', e); }
  }
}

export async function POST(request) {
  const raw = await request.text();
  if (!verifySignature(raw, request.headers.get('x-line-signature'))) {
    return new Response('invalid signature', { status: 401 });
  }
  let body;
  try { body = JSON.parse(raw); } catch { return new Response('bad json', { status: 400 }); }
  const work = handleEvents(body.events || []);
  // ตอบ LINE ทันที แล้วให้ AI ทำงานต่อเบื้องหลัง (ถ้าแพลตฟอร์มรองรับ) ไม่งั้นรอจนเสร็จ
  const vf = await import('@vercel/functions').catch(() => null);
  if (vf?.waitUntil) vf.waitUntil(work); else await work;
  return new Response('ok');
}

export function GET() {
  return new Response('PROMPT PAK LINE webhook is running');
}
