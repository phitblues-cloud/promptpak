// ลูกค้ากดคะแนน 1-5 จากการ์ด "เช็คเอาท์เรียบร้อยค่ะ" (postback `pp_rate|<กลุ่มการจอง>|<คะแนน>`)
// 4-5 → ขอบคุณ + ชวนรีวิว Google · 1-3 → ขอโทษ + แจ้งผู้จัดการ (ส่งต่อพนักงาน) · ตอบกลับด้วย reply (ฟรี ไม่นับโควตา)
import { replyMessages, reply } from './line.js';
import { rpc } from './db.js';

const bubble = (title, a, b, text, buttons) => ({ type: 'flex', altText: title, contents: { type: 'bubble',
  header: { type: 'box', layout: 'vertical', paddingAll: '16px', background: { type: 'linearGradient', angle: '125deg', startColor: a, endColor: b }, contents: [
    { type: 'text', text: 'พบรักรีสอร์ท', color: '#FFFFFFCC', size: 'xs' },
    { type: 'text', text: title, color: '#FFFFFF', weight: 'bold', size: 'lg', wrap: true }] },
  body: { type: 'box', layout: 'vertical', contents: [{ type: 'text', text, wrap: true, size: 'sm', color: '#2B1B3A' }] },
  ...(buttons?.length ? { footer: { type: 'box', layout: 'vertical', contents: buttons } } : {}) } });

export async function handleRate(ev, userId, name) {
  const [, key, s] = String(ev.postback?.data || '').split('|');
  const score = parseInt(s, 10), test = key === 'TEST';
  if (!(score >= 1 && score <= 5) || !key || !ev.replyToken) return;
  let r = { first: true };
  if (!test) {
    try { r = await rpc('pp_am_rate', { p_key: key, p_line: userId, p_score: score }); }
    catch (e) { console.error('rate failed', e); return reply(ev.replyToken, 'ขอบคุณค่ะ 🙏').catch(() => {}); }
  }
  const log = (sender, body) => rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: sender, p_body: body }).catch(() => {});
  if (!r.first) return reply(ev.replyToken, 'ขอบคุณค่ะ เราบันทึกคะแนนของคุณไว้แล้ว 🙏').catch(() => {});
  if (!test) await log('ลูกค้า', `(ให้คะแนนการพัก ${score} ดาว)`);
  if (score >= 4) {
    const url = ((await rpc('pp_am_cfg').catch(() => ({}))) || {}).review_url || '';
    const text = url ? 'ช่วยเล่าให้คนอื่นรู้จักเราใน Google สักนิดได้ไหมคะ' : 'ดีใจที่พักสบายนะคะ ไว้พบกันใหม่นะคะ 💜';
    const m = bubble(`ขอบคุณสำหรับ ${score} ดาว ⭐`, '#9A6A10', '#C99A2E', text,
      url ? [{ type: 'button', style: 'primary', color: '#6A3AA2', height: 'sm', action: { type: 'uri', label: 'เขียนรีวิวใน Google', uri: url } }] : []);
    if (!test) await log('ระบบ', `[ส่งอัตโนมัติ] ขอบคุณสำหรับ ${score} ดาว${url ? ' + ลิงก์รีวิว Google' : ''}`);
    return replyMessages(ev.replyToken, [m]).catch(e => console.error('rate reply', e));
  }
  const m = bubble('ขอโทษค่ะ 🙏', '#7A2A4E', '#C0396B', 'ขอโทษที่การพักครั้งนี้ไม่ประทับใจ ผู้จัดการจะติดต่อกลับโดยเร็วค่ะ\nเล่าให้ฟังได้ไหมคะว่าเรื่องอะไร พิมพ์ในแชทนี้ได้เลย');
  if (!test) {
    await log('ระบบ', `[ส่งอัตโนมัติ] ขอโทษ (ลูกค้าให้ ${score} ดาว) แจ้งผู้จัดการแล้ว`);
    await rpc('pp_handoff', { p_line_user_id: userId, p_reason: `ลูกค้าให้คะแนนการพัก ${score} ดาว — ผู้จัดการควรติดต่อกลับ` }).catch(() => {});
  }
  return replyMessages(ev.replyToken, [m]).catch(e => console.error('rate reply', e));
}
