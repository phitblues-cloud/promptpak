// ลูกค้าจองเองผ่านหน้าจอเด้งใน LINE (LIFF) · ส่งการ์ดยืนยัน + QR พร้อมเพย์กลับในแชท
import { rpc } from './db.js';
import { push, verifyIdToken } from './line.js';
import { thDate } from './ai.js';
import { bangkokDate } from './http.js';
import { uploadMedia } from './storage.js';

export const BF_PRICE = 170;   // อาหารเช้า บาท/ท่าน/คืน (ตรงกับฟอร์มของพนักงาน)
export const DEP_PRICE = 200;  // เงินประกันห้อง บาท/ห้อง (คืนหลังเช็คเอาท์ · ตรงกับหน้าเช็คอินของพนักงาน)
export const PROMPTPAY = () => (process.env.PROMPTPAY_ID || '0956727566').replace(/\D/g, '');
const PHOTO = { 'ตึกใหม่|เตียงเดี่ยว': 'tower-single', 'ตึกใหม่|เตียงคู่': 'tower-twin', 'ตึกใหม่|ห้องครอบครัว': 'tower-family',
  'บ้านหลัง|เตียงเดี่ยว': 'house-single', 'บ้านหลัง|เตียงคู่': 'house-twin' };
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const fmt = n => Number(n || 0).toLocaleString('en-US');

export function liffConfig() {
  const e = k => (process.env[k] || '').trim();
  // ข้อมูลโรงแรมที่แสดงในหน้ารายละเอียดการจอง (ตั้งใน Vercel · ไม่ใช่รหัสลับ · ถ้าไม่ตั้ง หน้าจอจะไม่แสดงบรรทัดนั้น)
  return { liffId: e('LIFF_ID'), bf: BF_PRICE, dep: DEP_PRICE, today: bangkokDate(), maxRooms: 4,
    hotel: { phone: e('HOTEL_PHONE'), breakfast: e('HOTEL_BREAKFAST'), map: e('HOTEL_MAP_URL'), address: e('HOTEL_ADDRESS') } };
}

export async function availability(ci, co) {
  if (!ISO.test(ci || '') || !ISO.test(co || '') || co <= ci) throw new Error('วันที่ไม่ถูกต้อง');
  const a = await rpc('pp_availability', { p_check_in: ci, p_check_out: co });
  return { ...a, types: (a.types || []).map(t => ({ zone: t.zone, type: t.room_type, rate: t.rate, max: t.max_guests, bed: t.bed || '',
    free: t.free_rooms, photo: PHOTO[t.zone + '|' + t.room_type] ? `/rooms/${PHOTO[t.zone + '|' + t.room_type]}-1.jpg` : null })) };
}

const detailUri = no => { const id = (process.env.LIFF_ID || '').trim(); return id ? `https://liff.line.me/${id}?no=${encodeURIComponent(no)}` : 'https://line.me'; };

// ถ้ายังไม่ได้รัน 21_liff_detail.sql หน้ารายละเอียดจะเปิดไม่ได้ → การ์ดใช้แบบเดิม (มี QR) กันลูกค้าจ่ายเงินไม่ได้
let _detailOk = false;
async function detailReady() {
  if (_detailOk) return true;
  try { await rpc('pp_liff_detail', { p_line_user_id: '-', p_no: '-' }); _detailOk = true; } catch { return false; }
  return _detailOk && !!(process.env.LIFF_ID || '').trim();
}

function card(origin, r, body, withDetail = true) {
  const arrival = body.pay === 'arrival', dep = body.dep || 0, due = r.total + dep;
  const nos = r.nos || [], first = nos[0], rooms = (r.bookings || []).map(b => b.room_id).join(', ');
  const row = (k, v, bold) => ({ type: 'box', layout: 'horizontal', contents: [
    { type: 'text', text: k, size: 'sm', color: '#6E5A68', flex: 2 },
    { type: 'text', text: v, size: 'sm', align: 'end', flex: 5, wrap: true, weight: bold ? 'bold' : 'regular', color: '#2E1F2B' }] });
  return {
    type: 'flex', altText: `รับการจองแล้ว ${first} · ยอด ${fmt(due)} บาท${arrival ? ' · ชำระวันเข้าพัก' : ''}`,
    contents: { type: 'bubble',
      header: { type: 'box', layout: 'vertical', paddingAll: '16px',
        background: { type: 'linearGradient', angle: '125deg', startColor: '#4B2477', endColor: '#C04C9C' }, contents: [
        { type: 'text', text: 'พบรักรีสอร์ท', color: '#FFFFFFCC', size: 'xs' },
        { type: 'text', text: 'รับการจองแล้ว ✓', color: '#FFFFFF', weight: 'bold', size: 'lg' },
        { type: 'text', text: `${first} · ${arrival ? 'ชำระวันเข้าพัก' : 'รอชำระเงิน'}`, color: '#FFFFFFCC', size: 'sm' }] },
      ...(arrival || withDetail ? {} : { hero: { type: 'image', url: `${origin}/api/qr?no=${encodeURIComponent(first)}&t=${due}`, size: 'lg', aspectRatio: '1:1', aspectMode: 'fit' } }),
      body: { type: 'box', layout: 'vertical', spacing: 'sm', contents: [
        row('เข้าพัก', `${thDate(r.check_in)} – ${thDate(r.check_out)} (${r.nights} คืน)`),
        row('ห้อง', rooms), row('ผู้จอง', body.name),
        { type: 'separator', margin: 'md' }, row(arrival ? 'ชำระที่เคาน์เตอร์' : 'ยอดโอน', `${fmt(due)} บาท`, true),
        { type: 'text', text: `${dep ? 'รวม' : '+ '}เงินประกันห้อง ${fmt(dep || body.depAll || 0)} บาท ${dep ? '' : 'ชำระที่เคาน์เตอร์ตอนเช็คอิน '}(คืนหลังเช็คเอาท์)`, size: 'xxs', color: '#8A6A1F', wrap: true },
        { type: 'text', text: arrival ? 'ชำระที่เคาน์เตอร์ตอนเช็คอินได้เลยค่ะ (เงินสด / โอน) แล้วพบกันนะคะ 🙏' : withDetail ? 'ยังไม่ได้โอน? กด "ดูรายละเอียดการจอง" เพื่อชำระเงินและแนบสลิปได้ค่ะ' : 'ถ้ายังไม่ได้แนบสลิปในหน้าจอจอง สแกน QR ด้านบน แล้วส่งรูปสลิปในแชทนี้ภายใน 24 ชม.ค่ะ',
          size: 'xs', color: '#6E5A68', wrap: true, margin: 'md' }] },
      ...(withDetail ? { footer: { type: 'box', layout: 'vertical', contents: [{ type: 'button', style: 'primary', color: '#6A3AA2', height: 'sm',
          action: { type: 'uri', label: 'ดูรายละเอียดการจอง', uri: detailUri(first) } }] },
        action: { type: 'uri', label: 'ดูรายละเอียดการจอง', uri: detailUri(first) } } : {}) },
    ...(arrival ? {} : { quickReply: { items: [
      { type: 'action', action: { type: 'cameraRoll', label: 'ส่งรูปสลิป' } },
      { type: 'action', action: { type: 'camera', label: 'ถ่ายรูปสลิป' } }] } }),
  };
}

const mask = d => d && d.length === 13 ? `x-xxxx-xxxxx-${d.slice(10, 12)}-${d[12]}` : null;
const maskPhone = p => { const d = String(p || '').replace(/\D/g, ''); return d.length >= 9 ? `${d.slice(0, 3)}-xxx-${d.slice(-4)}` : (p || ''); };

// ข้อมูลจากการจองครั้งก่อน (ใช้ข้อมูลเดิม) · เลขบัตรไม่ส่งออกไปเต็มๆ
export async function liffPrev(body) {
  const who = await verifyIdToken(body.idToken);
  const p = await rpc('pp_liff_prev', { p_line_user_id: who.sub });
  if (!p || !p.name) return { prev: null };
  return { prev: { name: p.name, phone: maskPhone(p.phone), email: p.email || '', since: p.since, doc: mask(p.doc_no), tax: p.tax || null } };
}

export async function liffBook(body, origin) {
  const who = await verifyIdToken(body.idToken);
  if (body.usePrev) {   // ใช้ข้อมูลเดิม: เติมเบอร์/เลขบัตร/ใบกำกับภาษีจากฐานข้อมูลฝั่งเซิร์ฟเวอร์
    const p = await rpc('pp_liff_prev', { p_line_user_id: who.sub });
    if (!p || !p.name) throw new Error('ไม่พบข้อมูลเดิม กรุณากรอกใหม่');
    body = { ...body, name: body.name || p.name, phone: /x/.test(body.phone || 'x') ? p.phone : body.phone,
      idno: /^\d{13}$/.test(String(body.idno || '').replace(/\D/g, '')) ? body.idno : (p.doc_no || ''),
      email: body.email || p.email || '', tax: body.tax === undefined ? (p.tax ? { name: p.tax.name, id: p.tax.id, addr: p.tax.addr, hq: p.tax.hq, branch: p.tax.branch } : null) : body.tax };
  }
  const items = (Array.isArray(body.items) ? body.items : []).slice(0, 10).map(x => ({ zone: String(x.zone || ''), room_type: String(x.type || ''),
    count: Math.max(0, Math.min(4, parseInt(x.count, 10) || 0)), bf: !!x.bf })).filter(x => x.count > 0);
  const img = String(body.img || '');
  if (img && (!/^data:image\/(jpeg|png|webp);base64,/.test(img) || img.length > 900000)) throw new Error('รูปบัตรใหญ่เกินไป ลองถ่ายใหม่อีกครั้ง');
  const tax = body.tax && body.tax.name ? { name: String(body.tax.name).slice(0, 160), id: String(body.tax.id || '').slice(0, 20),
    addr: String(body.tax.addr || '').slice(0, 300), hq: body.tax.hq === 'สาขา' ? 'สาขา' : 'สำนักงานใหญ่', branch: String(body.tax.branch || '').slice(0, 5) } : null;
  const r = await rpc('pp_liff_book', { p: {
    line_user_id: who.sub, line_name: who.name || '', name: String(body.name || '').trim().slice(0, 120), phone: String(body.phone || '').slice(0, 20),
    check_in: body.ci, check_out: body.co, adults: body.adults, kids: body.kids, purpose: String(body.purpose || '').slice(0, 20),
    email: String(body.email || '').slice(0, 120), items, doc_no: String(body.idno || ''), img, consent: !!body.consent, tax, bf_price: BF_PRICE } });
  const pay = body.pay === 'arrival' ? 'arrival' : 'now', nRooms = r.nos.length, dep = pay === 'now' && body.dep ? DEP_PRICE * nRooms : 0;
  await rpc('pp_liff_setpay', { p_nos: r.nos, p_pay: pay, p_dep: dep ? DEP_PRICE : 0 }).catch(e => console.error('setpay (ยังไม่ได้รัน 19_liff_pay.sql?)', e));
  const text = `ลูกค้าจองเองผ่านหน้าจอ LINE: ${r.nos.join(', ')} · ${thDate(r.check_in)}–${thDate(r.check_out)} · ยอด ${fmt(r.total + dep)} บาท${dep ? ` (รวมเงินประกัน ${fmt(dep)})` : ''} · ${pay === 'arrival' ? 'ชำระวันเข้าพัก' : 'รอสลิป'}`;
  await rpc('pp_chat_log', { p_line_user_id: who.sub, p_display_name: who.name || null, p_sender: 'ระบบ', p_body: text }).catch(() => {});
  try { await push(who.sub, [card(origin, r, { name: body.name, pay, dep, depAll: DEP_PRICE * nRooms }, await detailReady())]); }
  catch (e) { console.error('push failed', e); await rpc('pp_handoff', { p_line_user_id: who.sub, p_reason: 'ส่งการ์ดยืนยันการจองไม่สำเร็จ ติดต่อลูกค้าด้วย' }).catch(() => {}); }
  return { ok: true, pay, nos: r.nos, total: r.total + dep, room: r.total, dep, qr: pay === 'now' ? `/api/qr?no=${encodeURIComponent(r.nos[0])}&t=${r.total + dep}` : null, check_in: r.check_in, check_out: r.check_out, rooms: (r.bookings || []).map(b => b.room_id) };
}

// แนบสลิปในหน้าจอจอง (ชำระทันที) → บันทึกชำระแบบรอตรวจ + ส่งการ์ด "ได้รับสลิปแล้ว" ในแชท
export async function liffSlip(body) {
  const who = await verifyIdToken(body.idToken);
  const m = /^data:(image\/(?:jpeg|png|webp));base64,(.+)$/.exec(String(body.img || ''));
  if (!m) throw new Error('กรุณาแนบรูปสลิป');
  const buf = Buffer.from(m[2], 'base64');
  if (buf.length > 1500000) throw new Error('รูปสลิปใหญ่เกินไป ลองแนบใหม่อีกครั้ง');
  const url = await uploadMedia(buf, m[1]);
  const s = await rpc('pp_liff_slip', { p_line_user_id: who.sub, p_url: url });
  if (!s || !s.matched) throw new Error('ไม่พบการจองที่รอชำระ (อาจส่งสลิปไปแล้ว)');
  const t = `ได้รับสลิปแล้วค่ะ ✓ (${s.nos.join(', ')} · ${fmt(s.total)} บาท)\nพนักงานจะตรวจยอดอีกครั้ง แล้วพบกันวันเข้าพักนะคะ 🙏`;
  await rpc('pp_chat_log', { p_line_user_id: who.sub, p_display_name: who.name || null, p_sender: 'ลูกค้า', p_body: '[รูปภาพ] สลิปจากหน้าจอจอง', p_meta: { type: 'image', url } }).catch(() => {});
  await rpc('pp_chat_log', { p_line_user_id: who.sub, p_display_name: who.name || null, p_sender: 'ระบบ', p_body: t }).catch(() => {});
  await rpc('pp_handoff', { p_line_user_id: who.sub, p_reason: 'ส่งสลิปการจองผ่าน LINE · รอตรวจยอด' }).catch(() => {});
  try {
    await push(who.sub, [{ type: 'flex', altText: `ได้รับสลิปแล้ว ${s.nos[0]} · ${fmt(s.total)} บาท`, contents: { type: 'bubble',
      header: { type: 'box', layout: 'vertical', paddingAll: '16px', background: { type: 'linearGradient', angle: '125deg', startColor: '#1F7A50', endColor: '#2E9C6A' }, contents: [
        { type: 'text', text: 'พบรักรีสอร์ท', color: '#FFFFFFCC', size: 'xs' },
        { type: 'text', text: 'ได้รับสลิปแล้ว ✓', color: '#FFFFFF', weight: 'bold', size: 'lg' },
        { type: 'text', text: `${s.nos.join(', ')} · รอพนักงานตรวจยอด`, color: '#FFFFFFCC', size: 'sm', wrap: true }] },
      body: { type: 'box', layout: 'vertical', spacing: 'sm', contents: [
        { type: 'box', layout: 'horizontal', contents: [{ type: 'text', text: 'โอนแล้ว', size: 'sm', color: '#6E5A68' }, { type: 'text', text: `${fmt(s.total)} บาท`, size: 'sm', weight: 'bold', align: 'end' }] },
        { type: 'text', text: 'แล้วพบกันวันเข้าพักนะคะ 🙏', size: 'xs', color: '#6E5A68', wrap: true, margin: 'md' }] } } }]);
  } catch (e) { console.error('push slip card failed', e); }
  return { ok: true, nos: s.nos, total: s.total };
}

// หน้ารายละเอียดการจอง (เปิดจากการ์ดในแชท) · ตรวจตัวตนด้วย ID token แล้วให้ดูเฉพาะการจองของตัวเอง
export async function liffDetail(body) {
  const who = await verifyIdToken(body.idToken);
  const no = String(body.no || '').trim().slice(0, 40);
  if (!/^[A-Za-z0-9_-]+$/.test(no)) throw new Error('ไม่พบการจอง');
  let d;
  try { d = await rpc('pp_liff_detail', { p_line_user_id: who.sub, p_no: no }); }
  catch (e) { console.error('liff detail (ยังไม่ได้รัน 21_liff_detail.sql?)', e); throw new Error('ยังเปิดรายละเอียดไม่ได้ในขณะนี้ ลองใหม่ภายหลังหรือทักแชทได้เลยค่ะ'); }
  if (!d) throw new Error('ไม่พบการจองนี้ในบัญชี LINE ของคุณ');
  const due = d.room_total + d.bf_total + d.dep_online;
  return { ...d, due, qr: d.pay_mode === 'now' && !d.paid && !d.cancelled && due > 0 ? `/api/qr?no=${encodeURIComponent(d.nos[0])}&t=${due}` : null };
}
