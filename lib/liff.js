// ลูกค้าจองเองผ่านหน้าจอเด้งใน LINE (LIFF) · ส่งการ์ดยืนยัน + QR พร้อมเพย์กลับในแชท
import { rpc } from './db.js';
import { push, verifyIdToken } from './line.js';
import { thDate } from './ai.js';
import { bangkokDate } from './http.js';

export const BF_PRICE = 170;   // อาหารเช้า บาท/ท่าน/คืน (ตรงกับฟอร์มของพนักงาน)
export const PROMPTPAY = () => (process.env.PROMPTPAY_ID || '0956727566').replace(/\D/g, '');
const PHOTO = { 'ตึกใหม่|เตียงเดี่ยว': 'tower-single', 'ตึกใหม่|เตียงคู่': 'tower-twin', 'ตึกใหม่|ห้องครอบครัว': 'tower-family',
  'บ้านหลัง|เตียงเดี่ยว': 'house-single', 'บ้านหลัง|เตียงคู่': 'house-twin' };
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const fmt = n => Number(n || 0).toLocaleString('en-US');

export function liffConfig() {
  return { liffId: (process.env.LIFF_ID || '').trim(), bf: BF_PRICE, today: bangkokDate(), maxRooms: 4 };
}

export async function availability(ci, co) {
  if (!ISO.test(ci || '') || !ISO.test(co || '') || co <= ci) throw new Error('วันที่ไม่ถูกต้อง');
  const a = await rpc('pp_availability', { p_check_in: ci, p_check_out: co });
  return { ...a, types: (a.types || []).map(t => ({ zone: t.zone, type: t.room_type, rate: t.rate, max: t.max_guests, bed: t.bed || '',
    free: t.free_rooms, photo: PHOTO[t.zone + '|' + t.room_type] ? `/rooms/${PHOTO[t.zone + '|' + t.room_type]}-1.jpg` : null })) };
}

function card(origin, r, body) {
  const nos = r.nos || [], first = nos[0], rooms = (r.bookings || []).map(b => b.room_id).join(', ');
  const row = (k, v, bold) => ({ type: 'box', layout: 'horizontal', contents: [
    { type: 'text', text: k, size: 'sm', color: '#6E5A68', flex: 2 },
    { type: 'text', text: v, size: 'sm', align: 'end', flex: 5, wrap: true, weight: bold ? 'bold' : 'regular', color: '#2E1F2B' }] });
  return {
    type: 'flex', altText: `รับการจองแล้ว ${first} · ยอดชำระ ${fmt(r.total)} บาท`,
    contents: { type: 'bubble',
      header: { type: 'box', layout: 'vertical', backgroundColor: '#C42A86', paddingAll: '16px', contents: [
        { type: 'text', text: 'รับการจองแล้ว ✓', color: '#FFFFFF', weight: 'bold', size: 'lg' },
        { type: 'text', text: `${first} · รอชำระเงิน`, color: '#FFFFFFCC', size: 'sm' }] },
      hero: { type: 'image', url: `${origin}/api/qr?no=${encodeURIComponent(first)}&t=${r.total}`, size: 'lg', aspectRatio: '1:1', aspectMode: 'fit' },
      body: { type: 'box', layout: 'vertical', spacing: 'sm', contents: [
        row('เข้าพัก', `${thDate(r.check_in)} – ${thDate(r.check_out)} (${r.nights} คืน)`),
        row('ห้อง', rooms), row('ผู้จอง', body.name),
        { type: 'separator', margin: 'md' }, row('ยอดชำระ', `${fmt(r.total)} บาท`, true),
        { type: 'text', text: 'สแกน QR พร้อมเพย์ด้านบน แล้วส่งรูปสลิปในแชทนี้ได้เลยค่ะ', size: 'xs', color: '#6E5A68', wrap: true, margin: 'md' }] } },
    quickReply: { items: [
      { type: 'action', action: { type: 'cameraRoll', label: 'ส่งรูปสลิป' } },
      { type: 'action', action: { type: 'camera', label: 'ถ่ายรูปสลิป' } }] },
  };
}

export async function liffBook(body, origin) {
  const who = await verifyIdToken(body.idToken);
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
  const text = `ลูกค้าจองเองผ่านหน้าจอ LINE: ${r.nos.join(', ')} · ${thDate(r.check_in)}–${thDate(r.check_out)} · ยอด ${fmt(r.total)} บาท · รอสลิป`;
  await rpc('pp_chat_log', { p_line_user_id: who.sub, p_display_name: who.name || null, p_sender: 'ระบบ', p_body: text }).catch(() => {});
  try { await push(who.sub, [card(origin, r, { name: body.name })]); }
  catch (e) { console.error('push failed', e); await rpc('pp_handoff', { p_line_user_id: who.sub, p_reason: 'ส่งการ์ดยืนยันการจองไม่สำเร็จ ติดต่อลูกค้าด้วย' }).catch(() => {}); }
  return { ok: true, nos: r.nos, total: r.total, check_in: r.check_in, check_out: r.check_out, rooms: (r.bookings || []).map(b => b.room_id) };
}
