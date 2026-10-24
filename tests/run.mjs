// ทดสอบทั้งเส้นทางในเครื่อง: LINE → AI (จำลอง) → ฐานข้อมูล → หน้าเว็บ API
// ต้องมี Postgres ในเครื่อง: LOCAL_PG=postgresql://... node tests/run.mjs
import { createHmac } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

process.env.LOCAL_DEV = '1';
process.env.LINE_CHANNEL_SECRET = 'test-secret';
const PG = process.env.LOCAL_PG;
if (!PG) { console.error('ต้องตั้ง LOCAL_PG'); process.exit(1); }
const psql = (...a) => execFileSync('psql', [PG, '-q', '-v', 'ON_ERROR_STOP=1', ...a], { encoding: 'utf8' });
psql('-c', 'drop schema public cascade; create schema public;');
psql('-f', 'supabase/01_schema.sql'); psql('-f', 'supabase/02_seed.sql');

globalThis.__ppLineOutbox = [];
const script = []; const seenPayloads = [];
globalThis.__ppFakeClaude = async p => { seenPayloads.push(p); const f = script.shift(); assert.ok(f, 'Claude ถูกเรียกเกินสคริปต์'); return f(p); };
const toolUse = (name, input) => () => ({ stop_reason: 'tool_use', content: [{ type: 'tool_use', id: 'tu_' + Math.random(), name, input }] });
const say = text => () => ({ stop_reason: 'end_turn', content: [{ type: 'text', text }] });

const { createServer } = await import('../dev/server.mjs');
const srv = createServer().listen(0);
const base = `http://localhost:${srv.address().port}`;
let jar = '';
const call = async (path, opts = {}) => {
  const r = await fetch(base + path, { ...opts, headers: { 'Content-Type': 'application/json', cookie: jar, ...(opts.headers || {}) } });
  const sc = r.headers.getSetCookie(); if (sc.length) jar = sc.map(c => c.split(';')[0]).join('; ');
  return { status: r.status, body: await r.json().catch(() => null) };
};
let evn = 0;
const lineEvent = (userId, text, id) => ({ type: 'message', webhookEventId: id || 'ev' + (++evn), replyToken: 'rt' + evn,
  source: { type: 'user', userId }, message: { type: 'text', id: 'm' + evn, text } });
async function webhook(events, secret = 'test-secret') {
  const raw = JSON.stringify({ destination: 'x', events });
  const sig = createHmac('sha256', secret).update(raw).digest('base64');
  const r = await fetch(base + '/api/line-webhook', { method: 'POST', body: raw, headers: { 'x-line-signature': sig, 'content-type': 'application/json' } });
  return r.status;
}
const replies = () => globalThis.__ppLineOutbox.filter(x => x.path === '/message/reply');
let pass = 0; const ok = (name) => { pass++; console.log('✓', name); };

// 1) ล็อกอิน
assert.equal((await call('/api/dashboard')).status, 401); ok('ยังไม่ล็อกอิน → 401');
assert.equal((await call('/api/login', { method: 'POST', body: JSON.stringify({ email: 'demo@local', password: 'x' }) })).status, 401); ok('รหัสผิด → ปฏิเสธ');
assert.equal((await call('/api/login', { method: 'POST', body: JSON.stringify({ email: 'demo@local', password: 'demo' }) })).status, 200); ok('ล็อกอินสำเร็จ');

// 2) หน้าแรก ตรงกับต้นแบบ
const d0 = (await call('/api/dashboard')).body;
assert.equal(d0.rooms_total, 31);
console.log('  วันนี้', d0.date, 'มีแขกคืนนี้', d0.occupied_tonight, 'เข้า', d0.arrivals.length, 'พัก', d0.in_house.length, 'ออก', d0.departures.length);
ok('dashboard โหลดได้');

// 3) ลายเซ็นผิด
assert.equal(await webhook([lineEvent('Ubad', 'hi')], 'wrong'), 401); ok('ลายเซ็น LINE ผิด → ปฏิเสธ');

// 4) บทสนทนาจองจริง 2 ห้อง
const U = 'Uabc123';
const plus = n => { const t = new Date(d0.date + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };
const ci = plus(3), co = plus(5);
script.push(toolUse('check_availability', { check_in: ci, check_out: co }), say('ว่างค่ะ ตึกสแตนดาร์ด 700 บาท/คืน 2 ห้อง 2 คืน รวม 2,800 บาท ขอชื่อและเบอร์โทรค่ะ'));
assert.equal(await webhook([lineEvent(U, 'ขอห้องตึก 2 ห้อง')]), 200);
assert.equal(replies().length, 1); assert.match(replies()[0].body.messages[0].text, /ว่างค่ะ/);
const sys = seenPayloads[0].system;
assert.match(sys, /พรุ่งนี้/); assert.match(sys, /700 บาท/);
const avail = seenPayloads[1].messages.at(-1).content[0];
assert.equal(avail.type, 'tool_result'); assert.match(avail.content, /free_rooms/);
ok('AI เช็คห้องว่างจากฐานข้อมูลจริงแล้วตอบลูกค้า');

script.push(toolUse('create_booking', { guest_name: 'สมชาย ทดสอบ', phone: '081-111-2222', company: 'บริษัททดสอบ', check_in: ci, check_out: co,
  items: [{ room_type: 'สแตนดาร์ด (เตียงคู่)', count: 2 }] }), p => {
  const res = JSON.parse(p.messages.at(-1).content[0].content);
  return say(`จองสำเร็จค่ะ เลขที่ ${res.bookings.map(b => b.booking_no).join(', ')} รวม ${res.room_total} บาท`)();
});
await webhook([lineEvent(U, 'สมชาย ทดสอบ 0811112222 ยืนยันค่ะ')]);
assert.match(replies().at(-1).body.messages[0].text, /จองสำเร็จค่ะ เลขที่ BK\d+, BK\d+ รวม 2800 บาท/);
const d1 = (await call('/api/dashboard')).body;
assert.equal(d1.latest_ai.length, 2); assert.equal(d1.ai_bookings_today, 2);
const bk = (await call(`/api/bookings?from=${ci}&to=${co}`)).body.bookings.filter(b => b.created_by === 'ai');
assert.equal(bk.length, 2); assert.equal(bk[0].check_in, ci); assert.equal(bk[0].room_total, 1400);
ok('AI สร้างการจองจริง → ขึ้นหน้าแรก + รายการ/ปฏิทินทันที');

// 5) ประวัติแชทถูกส่งให้ AI ครบและสลับบทบาทถูกต้อง
const msgs2 = seenPayloads[2].messages;
assert.equal(msgs2[0].role, 'user'); assert.equal(msgs2.at(-1).role, 'user');
for (let i = 1; i < msgs2.length; i++) assert.notEqual(msgs2[i].role, msgs2[i - 1].role);
ok('ประวัติแชทส่งให้ AI ถูกลำดับ');

// 6) webhook ซ้ำ (LINE ส่งซ้ำ) → ไม่ตอบซ้ำ
const before = replies().length;
script.push(say('x')); await webhook([lineEvent(U, 'ซ้ำ', 'ev-dup')]);
await webhook([lineEvent(U, 'ซ้ำ', 'ev-dup')]);
assert.equal(replies().length, before + 1);
ok('ข้อความซ้ำไม่ถูกประมวลผลสองครั้ง');

// 7) ราวกันตก: AI พยายามจอง 5 ห้อง → ฐานข้อมูลปฏิเสธ → AI ได้รับ error
script.push(toolUse('create_booking', { guest_name: 'ทีมใหญ่', phone: '0899999999', check_in: ci, check_out: co, items: [{ room_type: 'บ้านพัก', count: 5 }] }),
  p => { assert.equal(p.messages.at(-1).content[0].is_error, true); return say('ขอส่งให้พนักงานค่ะ')(); });
await webhook([lineEvent('Ubig', 'จอง 5 หลัง')]);
const big = (await call(`/api/bookings?from=${ci}&to=${co}`)).body.bookings.filter(b => b.guest_name === 'ทีมใหญ่');
assert.equal(big.length, 0);
ok('AI จอง 5 ห้องเองไม่ได้ (ฐานข้อมูลปฏิเสธ)');

// 8) ส่งต่อพนักงาน → AI เงียบจนพนักงานกดจบเรื่อง
script.push(toolUse('handoff_to_staff', { reason: 'ขอเครดิตบริษัท' }), say('พนักงานจะติดต่อกลับค่ะ'));
await webhook([lineEvent('Ucredit', 'ขอวางบิลบริษัทได้ไหม')]);
const nReply = replies().length;
await webhook([lineEvent('Ucredit', 'ว่าไงครับ')]);
assert.equal(replies().length, nReply); // AI ไม่ตอบ
let ts = (await call('/api/chats')).body;
const th = ts.find(t => t.needs_staff && t.handoff_reason === 'ขอเครดิตบริษัท');
assert.ok(th); assert.equal((await call('/api/dashboard')).body.chats_need_staff, 1);
await call('/api/chats', { method: 'POST', body: JSON.stringify({ id: th.id, action: 'resolve' }) });
script.push(say('ยินดีค่ะ'));
await webhook([lineEvent('Ucredit', 'ขอบคุณครับ')]);
assert.equal(replies().length, nReply + 1);
const conv = (await call('/api/chats?id=' + th.id)).body;
assert.ok(conv.messages.some(m => m.meta?.actions?.[0]?.tool === 'handoff_to_staff'));
ok('ส่งต่อพนักงาน: AI หยุดตอบ → กดจบเรื่อง → AI กลับมาตอบ');

// 9) AI ล่ม → ลูกค้าได้ข้อความขอโทษ + ส่งต่อพนักงาน
script.push(() => { throw new Error('API down'); });
await webhook([lineEvent('Udown', 'สวัสดี')]);
assert.match(replies().at(-1).body.messages[0].text, /ขัดข้องชั่วคราว/);
ok('AI ล่ม → ตอบขอโทษและส่งต่อพนักงาน');

// 10) AI สรุปให้เจ้าของ
script.push(p => { const data = JSON.parse(p.messages[0].content); assert.ok(data.next7.length === 7); return say('• ทดสอบสรุป')(); });
const s = (await call('/api/summary', { method: 'POST' })).body;
assert.equal(s.text, '• ทดสอบสรุป'); assert.ok(s.data.new_bookings_24h.length >= 2);
ok('AI สรุปได้ และส่งข้อมูลจริงให้ AI');

// 11) health
const h = await (await fetch(base + '/api/health')).json();
assert.equal(h.database, 'ok'); ok('หน้าตรวจการตั้งค่าทำงาน');

assert.equal(script.length, 0, 'สคริปต์ AI ใช้ไม่หมด');
srv.close();
console.log(`\nผ่านทั้งหมด ${pass} ข้อ`);
