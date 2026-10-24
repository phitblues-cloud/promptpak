// รับข้อความจาก LINE OA → บันทึก → ให้ AI ตอบ/รับจอง → ตอบกลับลูกค้า
import { verifySignature, reply, showLoading, getProfile } from '../lib/line.js';
import { rpc } from '../lib/db.js';
import { bookingAgent } from '../lib/ai.js';

const WELCOME = 'สวัสดีค่ะ ยินดีต้อนรับสู่ พบรักรีสอร์ท 🙏\nจองห้องได้ทางแชทนี้เลยค่ะ พิมพ์วันเข้าพัก วันออก และจำนวนห้องที่ต้องการ เช่น "ขอห้องตึก 2 ห้อง 27-29 ต.ค."';

async function handleEvent(ev) {
  const userId = ev.source?.userId;
  if (!userId) return;
  if (ev.webhookEventId && (await rpc('pp_event_seen', { p_event_id: ev.webhookEventId }))) return; // ซ้ำ ข้าม
  const profile = await getProfile(userId);
  const name = profile.displayName || null;

  if (ev.type === 'follow') {
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ระบบ', p_body: '(เพิ่มเพื่อน LINE OA)' });
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'AI', p_body: WELCOME });
    if (ev.replyToken) await reply(ev.replyToken, WELCOME);
    return;
  }
  if (ev.type !== 'message') return;

  if (ev.message?.type !== 'text') {
    const t = 'ตอนนี้น้องพบรักอ่านได้เฉพาะข้อความตัวอักษรนะคะ รบกวนพิมพ์มาได้เลยค่ะ 🙏';
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ลูกค้า', p_body: `[${ev.message?.type || 'ไฟล์'}]` });
    await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'AI', p_body: t });
    await reply(ev.replyToken, t);
    return;
  }

  await rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: 'ลูกค้า', p_body: ev.message.text });

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
