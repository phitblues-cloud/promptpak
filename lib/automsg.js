// แบบสอบถามความพึงพอใจทาง LINE (ต่อจากการ์ดดาวที่ส่งตอนเช็คเอาท์ · ดู renderer/automsg.py)
//   ขั้น 1  pp_rate|<กลุ่มการจอง>|<1-5>        ภาพรวม → ตอบการ์ดรายเรื่อง (ปัดซ้าย-ขวา)
//   ขั้น 2  pp_topic|<กลุ่ม>|<หัวข้อ>|<1|3|5>  รายเรื่อง 3 ระดับ (5=ประทับใจ 3=พอใช้ 1=ปรับปรุง) · ตอบครบ → ขั้น 3 เอง
//           pp_done|<กลุ่ม>                    ปุ่ม "ส่งคำตอบ/ข้าม" → ขั้น 3
//   ขั้น 3  ข้อความธรรมดา (ขอบคุณ/ขอโทษ) + การ์ดชวนรีวิว Google เฉพาะคนพอใจ · ไม่พอใจ → แจ้งผู้จัดการ (pp_handoff)
// ตอบด้วย reply (ฟรี ไม่นับโควตา) · key = TEST คือส่งตัวอย่างจากหน้าตั้งค่า (ไม่แตะฐานข้อมูล)
import { replyMessages } from './line.js';
import { rpc } from './db.js';

const BASE = () => (process.env.PUBLIC_URL || 'https://promptpak-eight.vercel.app').trim();
const DARK = '#2E1450', GOLD = '#B8923A', IVORY = '#FBF8F3';
const TOPICS = { room: ['ห้องพัก', 'ความสะอาด ความสบาย', 'room'], facility: ['สิ่งอำนวยความสะดวก', 'ไวไฟ น้ำอุ่น ที่จอดรถ', 'facility'],
  service: ['การบริการ', 'ความสุภาพ ความช่วยเหลือ', 'service'], food: ['อาหาร', 'อาหารเช้า', 'food'], value: ['ความคุ้มค่า', 'กับราคาที่จ่าย', 'value'] };
const LV = { 5: ['ประทับใจ', 'good'], 3: ['พอใช้', 'ok'], 1: ['ปรับปรุง', 'bad'] };
const LABEL = { 1: 'ไม่ประทับใจ', 2: 'ควรปรับปรุง', 3: 'พอใช้', 4: 'ดี', 5: 'ดีเยี่ยม' };

const first = n => (String(n || '').replace(/^(นางสาว|นาย|นาง|น\.ส\.|ด\.ช\.|ด\.ญ\.|คุณ)\s*/, '').trim().split(/\s+/)[0]) || 'ลูกค้า';
const rule = () => ({ type: 'box', layout: 'vertical', height: '2px', backgroundColor: GOLD, contents: [{ type: 'filler' }] });
const topicList = bf => Object.keys(TOPICS).filter(k => bf || k !== 'food');

// การ์ดรายเรื่อง 1 ใบ (ไอคอนเส้นบาง · หน้า 3 ระดับ)
function topicBubble(key, tk, idx, total) {
  const [name, sub, ic] = TOPICS[tk];
  const faces = [5, 3, 1].map(l => ({ type: 'box', layout: 'vertical', flex: 1, paddingAll: '8px', cornerRadius: '12px', backgroundColor: '#FFFFFF', borderColor: '#E9E0CF', borderWidth: '1px',
    alignItems: 'center', spacing: 'xs',
    action: { type: 'postback', label: `${name} ${LV[l][0]}`.slice(0, 20), data: `pp_topic|${key}|${tk}|${l}`, displayText: `${name} · ${LV[l][0]}` },
    contents: [{ type: 'image', url: `${BASE()}/brand/ic/${LV[l][1]}.png`, size: '36px', aspectMode: 'fit' },
      { type: 'text', text: LV[l][0], size: 'xs', weight: 'bold', color: DARK, align: 'center' }] }));
  return { type: 'bubble', size: 'micro',
    header: { type: 'box', layout: 'vertical', paddingAll: '14px', background: { type: 'linearGradient', angle: '135deg', startColor: DARK, endColor: '#4B2477' }, contents: [
      { type: 'box', layout: 'horizontal', alignItems: 'center', contents: [
        { type: 'image', url: `${BASE()}/brand/ic/${ic}.png`, size: '28px', aspectMode: 'fit', flex: 0 },
        { type: 'text', text: `${idx}/${total}`, size: 'xxs', color: '#D9C48A', align: 'end' }] },
      { type: 'text', text: name, size: 'md', weight: 'bold', color: '#FFFFFF', margin: 'sm', wrap: true },
      { type: 'text', text: sub, size: 'xxs', color: '#D9C48A', wrap: true }] },
    body: { type: 'box', layout: 'vertical', backgroundColor: IVORY, paddingAll: '12px', spacing: 'md', contents: [rule(),
      { type: 'text', text: 'เรื่องนี้เป็นอย่างไรบ้างคะ', size: 'xs', color: DARK, align: 'center', wrap: true },
      { type: 'box', layout: 'vertical', spacing: 'sm', contents: faces }] } };
}

// ใบสุดท้ายของการ์ดปัด: ส่งคำตอบ / ข้าม
function doneBubble(key) {
  const btn = (label, data, primary) => ({ type: 'box', layout: 'vertical', paddingAll: '10px', cornerRadius: '99px', margin: 'sm',
    backgroundColor: primary ? DARK : '#FFFFFF', borderColor: primary ? DARK : '#E9E0CF', borderWidth: '1px',
    action: { type: 'postback', label, data, displayText: label },
    contents: [{ type: 'text', text: label, size: 'sm', weight: 'bold', align: 'center', color: primary ? '#F4E9C8' : '#7D7090' }] });
  return { type: 'bubble', size: 'micro',
    body: { type: 'box', layout: 'vertical', backgroundColor: IVORY, paddingAll: '16px', justifyContent: 'center', contents: [rule(),
      { type: 'text', text: 'ตอบครบแล้วหรือยังคะ', size: 'sm', weight: 'bold', color: DARK, align: 'center', margin: 'lg', wrap: true },
      { type: 'text', text: 'ถ้าไม่อยากตอบเรื่องไหน ข้ามได้ค่ะ', size: 'xxs', color: '#8C7FA0', align: 'center', wrap: true, margin: 'sm' },
      btn('เสร็จแล้ว', `pp_done|${key}`, true), btn('ข้าม', `pp_done|${key}`, false)] } };
}

export function topicCarousel(key, bf) {
  const ts = topicList(bf);
  return { type: 'flex', altText: 'ขอถามเพิ่มอีกนิดนะคะ ปัดดูแต่ละเรื่องแล้วแตะเลือกได้เลยค่ะ',
    contents: { type: 'carousel', contents: [...ts.map((tk, i) => topicBubble(key, tk, i + 1, ts.length)), doneBubble(key)] } };
}

// การ์ดชวนรีวิว Google (ไม่มีรูปดาว)
function reviewCard(url) {
  return { type: 'flex', altText: 'ช่วยบอกต่อให้เราหน่อยนะคะ รีวิวใน Google', contents: { type: 'bubble', size: 'mega',
    header: { type: 'box', layout: 'vertical', paddingAll: '18px', background: { type: 'linearGradient', angle: '135deg', startColor: '#6B4A0E', endColor: GOLD }, contents: [
      { type: 'text', text: 'ช่วยบอกต่อให้เราหน่อยนะคะ', size: 'lg', weight: 'bold', color: '#FFFFFF', wrap: true }] },
    body: { type: 'box', layout: 'vertical', backgroundColor: IVORY, paddingAll: '16px', contents: [
      { type: 'text', text: 'รีวิวสั้นๆ ใน Google ช่วยให้ผู้เข้าพักท่านอื่นรู้จักพบรักรีสอร์ทมากขึ้นค่ะ', size: 'sm', color: '#2B1B3A', wrap: true }] },
    footer: { type: 'box', layout: 'vertical', backgroundColor: IVORY, paddingAll: '12px', contents: [
      { type: 'box', layout: 'vertical', paddingAll: '12px', cornerRadius: '99px', backgroundColor: DARK, action: { type: 'uri', label: 'เขียนรีวิวใน Google', uri: url },
        contents: [{ type: 'text', text: 'เขียนรีวิวใน Google', size: 'sm', weight: 'bold', color: '#F4E9C8', align: 'center' }] }] } } };
}

const text = t => ({ type: 'text', text: t });

// ข้อความขั้น 3 ตามคะแนน → { msgs, alert, kind }
export function finalMessages({ name, overall, topics, bf }, reviewUrl) {
  const n = first(name);
  const poor = Object.keys(topics || {}).filter(k => topics[k] === 1 && TOPICS[k]).map(k => TOPICS[k][0]);
  if (poor.length || overall <= 2) {
    const what = poor.length ? `ที่เรื่อง${poor.join(' และ')} ยังไม่ประทับใจ` : 'ที่การพักครั้งนี้ยังไม่ประทับใจ';
    return { kind: 'sorry', msgs: [text(`ขอโทษด้วยนะคะคุณ${n} ${what} 🙏\nผู้จัดการจะติดต่อกลับโดยเร็วค่ะ ถ้าสะดวกเล่าให้ฟังได้ว่าเกิดอะไรขึ้น พิมพ์ในแชทนี้ได้เลย`)],
      alert: `ลูกค้าให้ภาพรวม ${overall} ดาว${poor.length ? ' · ไม่ประทับใจเรื่อง: ' + poor.join(', ') : ''} — ผู้จัดการควรติดต่อกลับ` };
  }
  if (overall >= 4) {
    const msgs = [text(`ขอบคุณมากค่ะคุณ${n} ดีใจที่พักสบายนะคะ 🙏`)];
    if (reviewUrl) msgs.push(reviewCard(reviewUrl));
    return { kind: 'thanks', msgs };
  }
  return { kind: 'neutral', msgs: [text('ขอบคุณที่บอกเรานะคะ จะนำไปปรับปรุงให้ดียิ่งขึ้นค่ะ 🙏')] };
}

const log = (userId, name, sender, body) => rpc('pp_chat_log', { p_line_user_id: userId, p_display_name: name, p_sender: sender, p_body: body }).catch(() => {});
const rep = (ev, msgs) => replyMessages(ev.replyToken, msgs).catch(e => console.error('survey reply', e));

async function finish(ev, userId, name, key, test) {
  const cfg = (await rpc('pp_am_cfg').catch(() => ({}))) || {};
  const url = cfg.review_url || '';
  if (test) {   // ตัวอย่างจากหน้าตั้งค่า: แสดงข้อความกรณีพอใจ
    return rep(ev, finalMessages({ name: 'ธนกฤต', overall: 5, topics: {} }, url).msgs);
  }
  let s;
  try { s = await rpc('pp_am_finish', { p_key: key, p_line: userId }); }
  catch (e) { console.error('survey finish', e); return rep(ev, [text('ขอบคุณค่ะ 🙏')]); }
  if (!s.first) return;   // ส่งขั้น 3 ไปแล้ว
  const f = finalMessages({ name: s.name, overall: Number(s.overall), topics: s.topics, bf: s.breakfast }, url);
  await log(userId, name, 'ระบบ', `[ส่งอัตโนมัติ] ขอบคุณ/${f.kind === 'sorry' ? 'ขอโทษ' : 'ปิดแบบสอบถาม'} (ภาพรวม ${s.overall} ดาว)${f.kind === 'thanks' && url ? ' + ลิงก์รีวิว Google' : ''}`);
  if (f.alert) await rpc('pp_handoff', { p_line_user_id: userId, p_reason: f.alert }).catch(() => {});
  return rep(ev, f.msgs);
}

export async function handleRate(ev, userId, name) {
  const [kind, key, a, b] = String(ev.postback?.data || '').split('|');
  if (!key || !ev.replyToken) return;
  const test = key === 'TEST';
  if (kind === 'pp_done') return finish(ev, userId, name, key, test);

  if (kind === 'pp_rate') {
    const score = parseInt(a, 10);
    if (!(score >= 1 && score <= 5)) return;
    if (test) return rep(ev, [topicCarousel(key, true)]);
    let r;
    try { r = await rpc('pp_am_rate', { p_key: key, p_line: userId, p_score: score }); }
    catch (e) { console.error('rate failed', e); return rep(ev, [text('ขอบคุณค่ะ 🙏')]); }
    if (!r.first) return rep(ev, [text('ขอบคุณค่ะ เราบันทึกคะแนนของคุณไว้แล้ว 🙏')]);
    await log(userId, name, 'ลูกค้า', `(ให้คะแนนภาพรวมการพัก ${score} ดาว · ${LABEL[score]})`);
    let bf = true;
    try { bf = !!(await rpc('pp_am_survey', { p_key: key, p_line: userId })).breakfast; } catch { /* ถามครบทุกเรื่อง */ }
    return rep(ev, [topicCarousel(key, bf)]);
  }

  if (kind === 'pp_topic') {
    const lvl = parseInt(b, 10);
    if (!TOPICS[a] || ![1, 3, 5].includes(lvl) || test) return;   // ตัวอย่าง: แตะแล้วไม่ต้องทำอะไร (มีข้อความยืนยันของลูกค้าขึ้นอยู่แล้ว)
    let s;
    try { s = await rpc('pp_am_topic', { p_key: key, p_line: userId, p_topic: a, p_lvl: lvl }); }
    catch (e) { console.error('topic failed', e); return; }
    const need = topicList(s.breakfast);
    if (!s.done && need.every(k => s.topics?.[k])) return finish(ev, userId, name, key, false);   // ตอบครบ → ขั้น 3
  }
}
