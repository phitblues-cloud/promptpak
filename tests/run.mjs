// ทดสอบทั้งเส้นทางในเครื่อง: LINE → AI (จำลอง) → ฐานข้อมูล → หน้าจอ v196
// ใช้: LOCAL_PG=postgresql://... node tests/run.mjs
import { createHmac } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

Object.assign(process.env, { AI_AUTOREPLY: '1', LOCAL_DEV: '1', LINE_CHANNEL_SECRET: 'test-secret', APP_SECRET: 'test-app', OWNER_PIN: '246810', STAFF_PIN: '135790' });
const PG = process.env.LOCAL_PG;
if (!PG) { console.error('ต้องตั้ง LOCAL_PG'); process.exit(1); }
const psql = (...a) => execFileSync('psql', [PG, '-q', '-t', '-A', '-v', 'ON_ERROR_STOP=1', ...a], { encoding: 'utf8' }).trim();
psql('-c', 'drop schema public cascade; create schema public;');
psql('-f', 'supabase/01_schema.sql'); psql('-f', 'supabase/02_seed.sql');
const rpc = (sql) => JSON.parse(psql('-c', `select to_jsonb(${sql})`));

globalThis.__ppLineOutbox = [];
const script = []; const seen = [];
globalThis.__ppFakeClaude = async p => { seen.push(p); const f = script.shift(); assert.ok(f, 'Claude ถูกเรียกเกินสคริปต์'); return f(p); };
const toolUse = (name, input) => () => ({ stop_reason: 'tool_use', content: [{ type: 'tool_use', id: 'tu_' + Math.random(), name, input }] });
const say = text => () => ({ stop_reason: 'end_turn', content: [{ type: 'text', text }] });

const { createServer } = await import('../dev/server.mjs');
const srv = createServer().listen(0);
const base = `http://localhost:${srv.address().port}`;
let jar = '';
const call = async (path, opts = {}) => {
  const r = await fetch(base + path, { ...opts, headers: { 'Content-Type': 'application/json', cookie: jar, ...(opts.headers || {}) } });
  const sc = r.headers.getSetCookie(); if (sc.length) jar = sc.map(c => c.split(';')[0]).join('; ');
  const text = await r.text();
  let body = text; try { body = JSON.parse(text); } catch {}
  return { status: r.status, body };
};
let evn = 0;
const lineEvent = (userId, text, id) => ({ type: 'message', webhookEventId: id || 'ev' + (++evn), replyToken: 'rt' + evn,
  source: { type: 'user', userId }, message: { type: 'text', id: 'm' + evn, text } });
async function webhook(events, secret = 'test-secret') {
  const raw = JSON.stringify({ destination: 'x', events });
  const sig = createHmac('sha256', secret).update(raw).digest('base64');
  return (await fetch(base + '/api/line-webhook', { method: 'POST', body: raw, headers: { 'x-line-signature': sig, 'content-type': 'application/json' } })).status;
}
const replies = () => globalThis.__ppLineOutbox.filter(x => x.path === '/message/reply');
let pass = 0; const ok = name => { pass++; console.log('✓', name); };

// 1) ล็อกอินด้วย PIN — ก่อนล็อกอินต้องไม่มีข้อมูลลูกค้าในหน้า
let r = await call('/');
assert.equal(r.status, 200); assert.ok(!r.body.includes('ธนกฤต')); assert.ok(r.body.length < 200000);
ok('ยังไม่ล็อกอิน: เห็นแค่หน้าล็อกอิน ไม่มีข้อมูลลูกค้า');
assert.equal((await call('/api/app?part=mods&since=x')).status, 401); ok('ยังไม่ล็อกอิน: ขอข้อมูลโมดูลไม่ได้');
assert.equal((await call('/api/summary', { method: 'POST' })).status, 401); ok('ยังไม่ล็อกอิน: เรียก AI สรุปไม่ได้');
assert.equal((await call('/api/app?part=pin', { method: 'POST', body: JSON.stringify({ role: 'owner', pin: '135790' }) })).status, 401);
ok('PIN พนักงานใช้กับบัตรเจ้าของไม่ได้');
assert.equal((await call('/api/app?part=pin', { method: 'POST', body: JSON.stringify({ role: 'owner', pin: '246810' }) })).status, 200);
r = await call('/');
assert.ok(r.body.includes('applyRole(PP.role,PP.name)')); assert.ok(r.body.length > 1500000);
ok('PIN ถูก → ได้แอป v196 เต็มพร้อมข้อมูล');

// 2) ตัวเลขวันนี้ ตรงกับต้นแบบ
const d0 = rpc('pp_dashboard()');
assert.equal(d0.rooms_total, 31);
console.log('  วันนี้', d0.date, 'มีแขกคืนนี้', d0.occupied_tonight, 'เข้า', d0.arrivals.length, 'พัก', d0.in_house.length, 'ออก', d0.departures.length);
ok('ข้อมูลวันนี้โหลดได้');

// 3) ลายเซ็นผิด
assert.equal(await webhook([lineEvent('Ubad', 'hi')], 'wrong'), 401); ok('ลายเซ็น LINE ผิด → ปฏิเสธ');

// 4) บทสนทนาจองจริง 2 ห้อง
const stamp0 = (await call('/api/app?part=mods&since=x')).body.stamp;
const U = 'Uabc123';
const plus = n => { const t = new Date(d0.date + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };
const ci = plus(3), co = plus(5);
script.push(toolUse('check_availability', { check_in: ci, check_out: co }), say('ว่างค่ะ ตึกใหม่เตียงเดี่ยว 700 บาท/คืน 2 ห้อง 2 คืน รวม 2,800 บาท ขอชื่อและเบอร์โทรค่ะ'));
assert.equal(await webhook([lineEvent(U, 'ขอห้องตึก 2 ห้อง')]), 200);
assert.match(replies()[0].body.messages[0].text, /ว่างค่ะ/);
assert.match(seen[0].system, /พรุ่งนี้/); assert.match(seen[0].system, /700 บาท/); assert.match(seen[0].system, /เตียงสองชั้น/);
const av = JSON.parse(seen[1].messages.at(-1).content[0].content);
assert.equal(av.types.length, 5); assert.equal(av.types.reduce((a, t) => a + t.total_rooms, 0), 31);
assert.ok(av.types.every(t => 'free_ground_floor' in t));
ok('AI เช็คห้องว่างจากฐานข้อมูลจริงแล้วตอบลูกค้า');

script.push(toolUse('create_booking', { guest_name: 'สมชาย ทดสอบ', phone: '081-111-2222', company: 'บริษัททดสอบ', check_in: ci, check_out: co,
  items: [{ zone: 'ตึกใหม่', room_type: 'เตียงเดี่ยว', count: 2 }] }), p => {
  const res = JSON.parse(p.messages.at(-1).content[0].content);
  return say(`จองสำเร็จค่ะ เลขที่ ${res.bookings.map(b => b.booking_no).join(', ')} รวม ${res.room_total} บาท`)();
});
await webhook([lineEvent(U, 'สมชาย ทดสอบ 0811112222 ยืนยันค่ะ')]);
assert.match(replies().at(-1).body.messages[0].text, /จองสำเร็จค่ะ เลขที่ BK\d+, BK\d+ รวม 2800 บาท/);
const bk = rpc(`pp_bookings('${ci}','${co}')`).bookings.filter(b => b.created_by === 'ai');
assert.equal(bk.length, 2); assert.equal(bk[0].room_total, 1400);
ok('AI สร้างการจองจริงในฐานข้อมูล');

// 5) หน้าจอ v196 ได้ข้อมูลใหม่ (โมดูลการจอง / หน้าแรก / แชท)
const mods = (await call('/api/app?part=mods&since=' + encodeURIComponent(stamp0))).body;
assert.notEqual(mods.stamp, stamp0);
assert.deepEqual(Object.keys(mods.mods).sort(), ['book', 'cust', 'fin', 'hk', 'home', 'linechat', 'rep']);
assert.ok(mods.mods.book.includes(bk[0].booking_no), 'การจองต้องอยู่ในโมดูลการจอง');
assert.ok(mods.mods.linechat.includes('จองสำเร็จค่ะ'), 'แชทจริงต้องอยู่ในโมดูลแชท');
const same = (await call('/api/app?part=mods&since=' + encodeURIComponent(mods.stamp))).body;
assert.equal(same.mods, undefined);
ok('การจองจาก LINE เข้าโมดูลการจองและแชทเดิม · ข้อมูลไม่เปลี่ยนก็ไม่ส่งซ้ำ');
for (const [k, v] of Object.entries(mods.mods)) assert.ok(!/(?<![A-Za-z0-9#])[AB]0\d\d(?![0-9A-Za-z])/.test(v), 'รหัสห้องเก่าเหลือในโมดูล ' + k);
assert.ok(mods.mods.book.includes('"code":"C15"') && mods.mods.book.includes("'บ้านหลัง'") && !mods.mods.book.includes("'B014').open=false"));
ok('หน้าจอใช้รหัสห้อง/ชื่อโซนจริง ไม่มีรหัสเก่าเหลือ');

// 6) ประวัติแชทถูกส่งให้ AI ถูกลำดับ
const msgs2 = seen[2].messages;
assert.equal(msgs2[0].role, 'user');
for (let i = 1; i < msgs2.length; i++) assert.notEqual(msgs2[i].role, msgs2[i - 1].role);
ok('ประวัติแชทส่งให้ AI ถูกลำดับ');

// 7) webhook ซ้ำ → ไม่ตอบซ้ำ
const before = replies().length;
script.push(say('x')); await webhook([lineEvent(U, 'ซ้ำ', 'ev-dup')]);
await webhook([lineEvent(U, 'ซ้ำ', 'ev-dup')]);
assert.equal(replies().length, before + 1);
ok('ข้อความซ้ำไม่ถูกประมวลผลสองครั้ง');

// 8) ราวกันตก: AI จอง 5 ห้อง → ฐานข้อมูลปฏิเสธ
script.push(toolUse('create_booking', { guest_name: 'ทีมใหญ่', phone: '0899999999', check_in: ci, check_out: co, items: [{ zone: 'บ้านหลัง', room_type: 'เตียงเดี่ยว', count: 5 }] }),
  p => { assert.equal(p.messages.at(-1).content[0].is_error, true); return say('ขอส่งให้พนักงานค่ะ')(); });
await webhook([lineEvent('Ubig', 'จอง 5 หลัง')]);
assert.equal(rpc(`pp_bookings('${ci}','${co}')`).bookings.filter(b => b.guest_name === 'ทีมใหญ่').length, 0);
ok('AI จอง 5 ห้องเองไม่ได้ (ฐานข้อมูลปฏิเสธ)');

// 8b) ห้องจริง: ขอชั้นล่าง → ได้ห้อง A (ชั้น 1) · ชั้นล่างไม่พอ → ไม่จอง · ไม่ระบุโซนเมื่อชื่อประเภทซ้ำ → ปฏิเสธ
const ci2 = plus(40), co2 = plus(41);
script.push(toolUse('create_booking', { guest_name: 'คุณแม่ ชั้นล่าง', phone: '0812223333', check_in: ci2, check_out: co2, prefer_ground_floor: true,
  items: [{ zone: 'ตึกใหม่', room_type: 'เตียงเดี่ยว', count: 1 }] }), p => {
  const res = JSON.parse(p.messages.at(-1).content[0].content);
  assert.equal(res.bookings[0].floor, 1); return say('จองห้อง ' + res.bookings[0].room_id + ' ค่ะ')(); });
await webhook([lineEvent('Ufloor', 'ขอห้องชั้นล่างนะคะ เดินขึ้นบันไดไม่ไหว')]);
assert.match(replies().at(-1).body.messages[0].text, /จองห้อง A0\d ค่ะ/);
const freeG = rpc(`pp_availability('${ci2}','${co2}')`).types.find(t => t.zone === 'ตึกใหม่' && t.room_type === 'เตียงเดี่ยว').free_ground_floor;
const bookG = n => psql('-c', `select pp_book('{"guest_name":"x","phone":"0811111111","check_in":"${ci2}","check_out":"${co2}","prefer_ground_floor":true,"items":[{"zone":"ตึกใหม่","room_type":"เตียงเดี่ยว","count":${n}}]}')`);
assert.throws(() => bookG(freeG + 1), /ห้องชั้นล่าง/);
assert.throws(() => psql('-c', `select pp_book('{"guest_name":"x","phone":"0811111111","check_in":"${ci2}","check_out":"${co2}","items":[{"room_type":"เตียงเดี่ยว","count":1}]}')`), /ต้องระบุโซน/);
const fam = JSON.parse(psql('-c', `select pp_book('{"guest_name":"ครอบครัว","phone":"0811111112","check_in":"${ci2}","check_out":"${co2}","items":[{"room_type":"ห้องครอบครัว","count":1}]}')`));
assert.match(fam.bookings[0].room_id, /^A0[45]$/); assert.equal(fam.bookings[0].rate, 800);
ok('ห้องจริง: ขอชั้นล่างได้ห้องชั้น 1 · ชั้นล่างไม่พอไม่จอง · ห้องครอบครัว 800 บาท');

// 9) ส่งต่อพนักงาน → AI เงียบ → ครบ 6 ชม. AI กลับมาตอบ
script.push(toolUse('handoff_to_staff', { reason: 'ขอเครดิตบริษัท' }), say('พนักงานจะติดต่อกลับค่ะ'));
await webhook([lineEvent('Ucredit', 'ขอวางบิลบริษัทได้ไหม')]);
const n = replies().length;
await webhook([lineEvent('Ucredit', 'ว่าไงครับ')]);
assert.equal(replies().length, n);
assert.equal(rpc('pp_dashboard()').chats_need_staff, 1);
psql('-c', "update chat_threads set handoff_at = now() - interval '7 hours' where line_user_id = 'Ucredit'");
script.push(say('ยินดีค่ะ'));
await webhook([lineEvent('Ucredit', 'ขอบคุณครับ')]);
assert.equal(replies().length, n + 1);
ok('ส่งต่อพนักงาน: AI หยุดตอบ แล้วกลับมาตอบเองหลัง 6 ชั่วโมง');

// 10) AI ล่ม → ข้อความขอโทษ + ส่งต่อพนักงาน
script.push(() => { throw new Error('API down'); });
await webhook([lineEvent('Udown', 'สวัสดี')]);
assert.match(replies().at(-1).body.messages[0].text, /ขัดข้องชั่วคราว/);
ok('AI ล่ม → ตอบขอโทษและส่งต่อพนักงาน');

// 11) AI สรุปในกล่อง CRM: รูปแบบถูก กันโค้ดแปลกปลอม และเก็บไว้ใช้ซ้ำ
script.push(p => { assert.ok(JSON.parse(p.messages[0].content).next7.length === 7);
  return say('```json\n{"items":[{"tp":"แชท LINE","tn":"bad","h":"รอพนักงาน <b>1</b> เรื่อง <img src=x onerror=alert(1)>","ev":["a"],"st":["โทรกลับ"]},{"tp":"ห้องว่าง","tn":"weird","h":"ว่าง <b>20</b>"}]}\n```')(); });
let s = (await call('/api/summary', { method: 'POST' })).body;
assert.equal(s.items.length, 2);
assert.equal(s.items[0].h, 'รอพนักงาน <b>1</b> เรื่อง &lt;img src=x onerror=alert(1)&gt;');
assert.equal(s.items[1].tn, 'info'); assert.deepEqual(s.items[1].st, ['ติดตามต่อ']);
s = (await call('/api/summary', { method: 'POST' })).body;   // ครั้งที่สอง: ไม่เรียก AI ซ้ำ (script ว่าง)
assert.equal(s.items.length, 2);
ok('AI สรุปกล่อง CRM: กันโค้ดแปลกปลอม + ไม่เรียก AI ซ้ำเมื่อข้อมูลไม่เปลี่ยน');

// 11b) ปุ่มหน้าเคาน์เตอร์บันทึกลงฐานข้อมูลจริง (รีเฟรชแล้วไม่หาย · การเงินเห็นยอด)
{
  const act = d => call('/api/app?part=act', { method: 'POST', body: JSON.stringify(d) });
  assert.equal((await fetch(base + '/api/app?part=act', { method: 'POST', body: '{"k":"checkin","no":"x"}' })).status, 401);
  const today = d0.date, out2 = plus(2);
  const room = psql('-c', `select id from rooms r where not exists (select 1 from bookings b where b.room_id = r.id and b.status <> 'ยกเลิก' and daterange(b.check_in, b.check_out) && daterange('${today}'::date, '${plus(4)}'::date)) order by id limit 1`);
  let a = (await act({ k: 'book', guest: 'แขก หน้าเคาน์เตอร์', phone: '0812345678', check_in: today, check_out: out2, rooms: [{ room }], channel: 'Walk-in' })).body;
  assert.equal(a.ok, true); const no = a.nos[0];
  const rate = rpc(`pp_bookings('${today}','${out2}')`).bookings.find(b => b.booking_no === no).rate;
  assert.equal((await act({ k: 'pay', no, m: 'cash', room_amt: rate * 2, dep: 300 })).body.ok, true);
  assert.equal((await act({ k: 'checkin', no })).body.ok, true);
  const mods = async () => (await call('/api/app?part=mods&since=x')).body.mods;
  let M = await mods();
  const bill = h => { const i = h.indexOf('let BILLS='); const arr = JSON.parse(h.slice(i + 10, h.indexOf(';\n', i))); return arr.find(x => x.no === no); };
  let fb = bill(M.fin);
  assert.equal(fb.paid, rate * 2); assert.equal(fb.dep, 'held');
  const card = h => { const i = h.indexOf('let B = '); return JSON.parse(h.slice(i + 8, h.indexOf(';\n', i))).find(x => x.bk === no); };
  assert.equal(card(M.home).stage, 'stay');
  ok('พนักงานจอง + รับเงิน + เช็คอิน → รีเฟรชแล้วยังอยู่ · การเงินเห็นยอดและเงินประกัน');

  // พักต่อห้องเดิม 1 คืน + จ่าย แล้วย้อนกลับได้
  a = (await act({ k: 'extend', no, segs: [{ room, from: out2, n: 1, rate }] })).body;
  assert.equal(rpc(`pp_bookings('${today}','${plus(4)}')`).bookings.find(b => b.booking_no === no).check_out, plus(3));
  await act({ k: 'undo', id: a.id });
  assert.equal(rpc(`pp_bookings('${today}','${plus(4)}')`).bookings.find(b => b.booking_no === no).check_out, out2);
  ok('พักต่อบันทึกจริง และกดย้อนกลับได้');

  // เช็คเอาท์ + คืนเงินประกัน (หัก 100)
  await act({ k: 'checkout', no }); await act({ k: 'dep_out', no, amt: 200, ded: 100, m: 'cash' });
  M = await mods(); fb = bill(M.fin);
  assert.equal(fb.dep, 'back');
  const c = card(M.home); assert.equal(c.stage, 'outdone');
  ok('เช็คเอาท์ + คืนเงินประกัน บันทึกจริง (การ์ดยังอยู่หน้าแรกวันนี้)');

  // ปิดห้อง → AI/ห้องว่างไม่นับ · เปิดคืน
  const before = rpc(`pp_availability('${plus(90)}','${plus(91)}')`).types.reduce((s, t) => s + t.free_rooms, 0);
  await act({ k: 'room', room, open: false });
  assert.equal(rpc(`pp_availability('${plus(90)}','${plus(91)}')`).types.reduce((s, t) => s + t.free_rooms, 0), before - 1);
  M = await mods(); assert.ok(M.book.includes(`"code":"${room}","zone":`) && /"open":false/.test(M.book));
  await act({ k: 'room', room, open: true });
  ok('ปิด/เปิดห้องบันทึกจริง (ห้องที่ปิด AI จองไม่ได้)');

  // ยกเลิกการจอง + ข้อผิดพลาดแจ้งกลับ
  a = (await act({ k: 'book', guest: 'ยกเลิก ทดสอบ', phone: '0811110000', check_in: plus(5), check_out: plus(6), rooms: [{ room }] })).body;
  await act({ k: 'cancel', no: a.nos[0], refund: 0, why: 'ลูกค้าเปลี่ยนแผน' });
  assert.equal(rpc(`pp_bookings('${plus(5)}','${plus(6)}')`).bookings.find(b => b.booking_no === a.nos[0]).status, 'ยกเลิก');
  const bad = await act({ k: 'book', guest: 'ชน', phone: '0811110001', check_in: today, check_out: out2, rooms: [{ room: (psql('-c', `select room_id from bookings where status <> 'ยกเลิก' and check_in <= '${today}' and check_out > '${today}' limit 1`)) }] });
  assert.equal(bad.status, 500); assert.match(bad.body.error, /no_double_booking|conflicting|ทับ/);
  ok('ยกเลิกบันทึกจริง · จองทับห้องที่มีแขก → ฐานข้อมูลปฏิเสธและแจ้งกลับ');
  // ไม่มาตามนัด -> ยกเลิกอัตโนมัติ · ลืมเช็คเอาท์ -> ค้างกล่องเช็คเอาท์ และห้องยังไม่ว่าง
  const r2 = psql('-c', `select id from rooms r where r.zone='บ้านหลัง' and not exists (select 1 from bookings b where b.room_id = r.id and b.status <> 'ยกเลิก' and daterange(b.check_in, b.check_out) && daterange('${plus(-3)}'::date, '${plus(3)}'::date)) order by id limit 2`).split('\n');
  psql('-c', `insert into bookings (booking_no, guest_name, phone, room_id, check_in, check_out, rate, created_by) values
    ('BKT001','ไม่มา','0800000001','${r2[0]}','${plus(-2)}','${plus(1)}',400,'staff'),
    ('BKT002','ลืมออก','0800000002','${r2[1]}','${plus(-2)}','${plus(0)}',400,'staff');
    insert into ops (role, kind, booking_no, data) values ('staff','checkin','BKT002','{}');`);
  M = await mods();
  assert.equal(rpc(`pp_bookings('${plus(-3)}','${plus(3)}')`).bookings.find(b => b.booking_no === 'BKT001').status, 'ยกเลิก');
  const cOut = (() => { const i = M.home.indexOf('let B = '); return JSON.parse(M.home.slice(i + 8, M.home.indexOf(';\n', i))).find(x => x.bk === 'BKT002'); })();
  assert.equal(cOut.stage, 'out');
  const freeT = () => rpc(`pp_availability('${today}','${plus(1)}')`).types.find(t => t.zone === 'บ้านหลัง' && t.room_type === 'เตียงเดี่ยว').free_rooms;
  const f1 = freeT(); await act({ k: 'checkout', no: 'BKT002' }); assert.equal(freeT(), f1 + 1);
  ok('ไม่มาตามนัด → ยกเลิกเอง · ลืมเช็คเอาท์ → ค้างในกล่องเช็คเอาท์');
  // รายละเอียดการจองครบ: อาหารเช้า/ส่วนลด → ยอดเงินตรง · มัดจำ 30% · เครดิตบริษัท · ไม่ขึ้น "ผูก LINE"
  const r3 = psql('-c', `select id from rooms r where not exists (select 1 from bookings b where b.room_id = r.id and b.status <> 'ยกเลิก' and daterange(b.check_in, b.check_out) && daterange('${plus(60)}'::date, '${plus(63)}'::date)) order by id limit 3`).split('\n');
  const rateOf = id => +psql('-c', `select rate from rooms where id = '${id}'`);
  a = (await act({ k: 'book', guest: 'รายละเอียด ครบ', phone: '0822222222', check_in: plus(60), check_out: plus(62), pay: 'now', m: 'cash',
    details: { adults: 2, kids: 1, purpose: 'ท่องเที่ยว', email: 'a@b.c' }, rooms: [{ room: r3[0], bf: 340, disc: 100, pax: 3 }] })).body;
  const nNow = a.nos[0];
  a = (await act({ k: 'book', guest: 'บจก. ทดสอบเครดิต', phone: '0833333333', company: 'บจก. ทดสอบเครดิต', check_in: plus(60), check_out: plus(61), pay: 'credit', cred_days: 45,
    details: { co: { name: 'บจก. ทดสอบเครดิต', tax: '0105555555555', addr: 'ขอนแก่น', hq: 'สำนักงานใหญ่' } }, rooms: [{ room: r3[1] }] })).body;
  const nCr = a.nos[0];
  a = (await act({ k: 'book', guest: 'บจก. มัดจำ', phone: '0844444444', company: 'บจก. มัดจำ', check_in: plus(60), check_out: plus(61), pay: 'dep', m: 'transfer',
    details: { co: { name: 'บจก. มัดจำ' } }, rooms: [{ room: r3[2] }] })).body;
  const nDep = a.nos[0];
  M = await mods();
  const billOf = n => { const i = M.fin.indexOf('let BILLS='); return JSON.parse(M.fin.slice(i + 10, M.fin.indexOf(';\n', i))).find(y => y.no === n); };
  const net = rateOf(r3[0]) * 2 + 340 - 100;
  assert.equal(billOf(nNow).total, net); assert.equal(billOf(nNow).paid, net);
  assert.ok(billOf(nCr).credit, 'ต้องเป็นเครดิตบริษัท'); assert.equal(billOf(nCr).paid, 0);
  assert.equal(billOf(nDep).paid, Math.round(rateOf(r3[2]) * 0.3));
  const bkItem = h => { const i = h.indexOf('B.push(...'); return JSON.parse(h.slice(i + 10, h.indexOf(');\n', i))); };
  const bi = bkItem(M.book).find(y => y.no === nNow);
  assert.equal(bi.adults, 2); assert.equal(bi.kids, 1); assert.equal(bi.purpose, 'ท่องเที่ยว'); assert.equal(bi.lineOn, false); assert.equal(bi.bf, 340);
  ok('จองจากเว็บ: อาหารเช้า/ส่วนลด ยอดเงินตรง · มัดจำ 30% · เครดิตบริษัท · ไม่ขึ้นผูก LINE');

  // ตั้งค่าห้อง: แก้ราคาทั้งประเภท → AI/ห้องว่างใช้ราคาใหม่ · เพิ่มห้อง · ย้อนกลับได้
  a = (await act({ k: 'roomtype', zone: 'บ้านหลัง', type: 'เตียงคู่', new_type: 'เตียงคู่', rate: 550 })).body;
  assert.equal(rpc(`pp_availability('${plus(90)}','${plus(91)}')`).types.find(t => t.zone === 'บ้านหลัง' && t.room_type === 'เตียงคู่').rate, 550);
  M = await mods(); assert.ok(/"code":"C13","zone":"B","type":"เตียงคู่","rate":550/.test(M.book));
  await act({ k: 'undo', id: a.id });
  assert.equal(rpc(`pp_availability('${plus(90)}','${plus(91)}')`).types.find(t => t.zone === 'บ้านหลัง' && t.room_type === 'เตียงคู่').rate, 500);
  a = (await act({ k: 'roomset', room: 'C16', zone: 'บ้านหลัง', type: 'เตียงเดี่ยว', rate: 400, max: 2, open: true })).body;
  assert.equal(rpc('pp_dashboard()').rooms_total, 32);
  M = await mods(); assert.ok(M.book.includes('"code":"C16"'));
  await act({ k: 'undo', id: a.id }); assert.equal(rpc('pp_dashboard()').rooms_total, 31);
  ok('ตั้งค่าราคา/ประเภทห้อง และเพิ่มห้อง บันทึกจริง (AI ใช้ราคาใหม่) และย้อนกลับได้');
  const hm = (await call('/')).body;
  assert.ok(hm.includes('ppSave(') && hm.includes('part=act'));
}

// 11c) หน้าแชท LINE: ส่งข้อความ/ปิดเคส/ชื่อแชท/หมายเหตุ บันทึกจริง
{
  const chat = d => call('/api/app?part=chat', { method: 'POST', body: JSON.stringify(d) });
  const tid = psql('-c', "select id from chat_threads where not is_seed order by id limit 1");
  let a = await chat({ k: 'send', key: 'db:' + tid, body: 'สวัสดีค่ะ พนักงานตอบเอง' });
  assert.equal(a.body.line, 'sent');
  assert.equal(psql('-c', `select meta->>'line' from chat_messages where thread_id=${tid} and sender='พนักงาน' order by id desc limit 1`), 'sent');
  assert.equal(psql('-c', `select needs_staff from chat_threads where id=${tid}`), 'f');
  assert.equal((await chat({ k: 'send', key: 'T002', body: 'แชทตัวอย่าง' })).body.line, 'sample');
  await chat({ k: 'name', key: 'T002', alias: 'คุณฝ้าย VIP' });
  await chat({ k: 'notes', key: 'T002', notes: ['ชอบห้องชั้นล่าง'] });
  await chat({ k: 'close', key: 'db:' + tid });
  assert.equal((await chat({ k: 'send', key: 'db:999999', body: 'x' })).status, 500);
  const L = (await call('/api/app?part=mods&since=x')).body.mods.linechat;
  assert.ok(L.includes('คุณฝ้าย VIP') && L.includes('ชอบห้องชั้นล่าง') && L.includes('แชทตัวอย่าง') && L.includes('part=chat'));
  ok('หน้าแชท LINE: ส่งข้อความ (แชทจริงเข้า LINE) / ชื่อแชท / หมายเหตุ / ปิดเคส บันทึกจริง');
}

// 11d) ลูกค้าและสมาชิก: แก้ข้อมูล/เพศ/ผูกบริษัท/สมัครสมาชิก บันทึกจริง
{
  const cust = d => call('/api/app?part=cust', { method: 'POST', body: JSON.stringify(d) });
  assert.equal((await cust({ k: 'edit', gid: 'G02', data: { gender: 'หญิง', special: 'ขอห้องเงียบ', nid: '1234567890123' } })).body.ok, true);
  assert.equal((await cust({ k: 'edit', gid: 'G02', data: { gender: 'x' } })).status, 500);
  assert.equal((await cust({ k: 'company', gid: 'G02', company: 'C001' })).body.ok, true);
  const a = (await cust({ k: 'member', gid: 'G02', base: 24 })).body;
  assert.equal(a.memberNo, 'M025');
  assert.equal((await cust({ k: 'member', gid: 'G02', base: 24 })).status, 500);
  const n = (await cust({ k: 'member', gid: 'NTEST1', is_new: true, base: 24, data: { name: 'คุณใหม่ ทดสอบ', phone: '0899999999' } })).body;
  assert.equal(n.memberNo, 'M026');
  assert.ok(!psql('-c', "select data::text from cust_state where gid='G02'").includes('1234567890123'));
  const C = (await call('/api/app?part=mods&since=x')).body.mods.cust;
  assert.ok(C.includes('"gender":"หญิง"') && C.includes('"memberNo":"M025"') && C.includes('คุณใหม่ ทดสอบ') && C.includes('part=cust'));
  ok('ลูกค้าและสมาชิก: แก้ข้อมูล/เพศ/ผูกบริษัท/สมัครสมาชิก บันทึกจริง (ไม่เก็บเลขบัตร)');
}

// 11e) เลขบัตร/หนังสือเดินทาง + ภาพบัตรเมื่อยินยอม · พนักงานเห็นแบบปิดเลข
{
  const cust = d => call('/api/app?part=cust', { method: 'POST', body: JSON.stringify(d) });
  const img = 'data:image/jpeg;base64,' + Buffer.from('fake-jpeg').toString('base64');
  assert.equal((await cust({ k: 'idcard', gid: 'G02', doc_type: 'id', doc_no: '1101700230700' })).status, 400);
  assert.equal((await cust({ k: 'idcard', gid: 'G02', doc_type: 'id', doc_no: '1-1017-00230-70-8', img })).status, 500);
  assert.equal((await cust({ k: 'idcard', gid: 'G02', doc_type: 'id', doc_no: '1-1017-00230-70-8', img, consent: true })).body.ok, true);
  assert.equal((await cust({ k: 'idcard', gid: 'G03', doc_type: 'passport', doc_no: 'aa123456' })).body.ok, true);
  assert.equal((await call('/api/app?part=idimg&gid=G02')).body.img, img);
  let C = (await call('/api/app?part=mods&since=x')).body.mods.cust;
  assert.ok(C.includes('"no":"1101700230708"') && C.includes('"mask":"1-xxxx-xxxxx-xx-8"') && C.includes('"no":"AA123456"'));
  assert.ok(!C.includes('fake-jpeg') && !C.includes(img));
  await cust({ k: 'idcard', gid: 'NOSTAY1', doc_type: 'id', doc_no: '1101700230708', img, consent: true });
  psql('-c', "update cust_id set img_at = now() - interval '400 days' where gid in ('G02','NOSTAY1')");
  await call('/api/app?part=mods&since=x');
  assert.equal(psql('-c', "select img is null from cust_id where gid='NOSTAY1'"), 't');   // ไม่ได้พักภายใน 1 ปี → ลบภาพ
  assert.equal(psql('-c', "select img is null from cust_id where gid='G02'"), 'f');       // ยังพักภายใน 1 ปี → เก็บไว้
  ok('เอกสารยืนยันตัวตน: ตรวจเลขบัตร, ภาพต้องยินยอม, ไม่ฝังภาพในหน้า, ลบภาพเกิน 1 ปี');
}

// 11f) เพิ่มบริษัทใหม่ → ทุกโมดูลเห็น และผูกลูกค้าได้
{
  const cust = d => call('/api/app?part=cust', { method: 'POST', body: JSON.stringify(d) });
  assert.equal((await cust({ k: 'comp', gid: 'KTEST1', data: { name: 'บริษัท ทดสอบ', tax: '0405561000120' } })).status, 400);
  assert.equal((await cust({ k: 'comp', gid: 'KTEST1', data: { name: '' } })).status, 500);
  assert.equal((await cust({ k: 'comp', gid: 'KTEST1', data: { name: 'บริษัท ขอนแก่นวิศวกรรม จำกัด', tax: '0405561000124', phone: '043123456' } })).body.ok, true);
  assert.equal((await cust({ k: 'comp', gid: 'KTEST2', data: { name: 'อีกบริษัท', tax: '0405561000124' } })).status, 500);
  await cust({ k: 'company', gid: 'G04', company: 'KTEST1' });
  const M = (await call('/api/app?part=mods&since=x')).body.mods;
  assert.ok(M.cust.includes('"id":"KTEST1","name":"บริษัท ขอนแก่นวิศวกรรม จำกัด"') && M.cust.includes('"company":"KTEST1"'));
  ok('เพิ่มบริษัทใหม่ (ตรวจเลขผู้เสียภาษี/กันซ้ำ) และผูกลูกค้าได้');
}

// 11g) อ่านข้อมูลจากภาพบัตร (จำลอง AI)
{
  process.env.PP_FAKE_OCR = JSON.stringify({ doc_type: 'id', doc_no: '1-1017-00230-70-8', title: 'นาย', first_name: 'สมชาย', last_name: 'ใจดี', birth_date: '1990-01-02', address: 'x', province: 'ขอนแก่น' });
  const r = (await call('/api/app?part=idocr', { method: 'POST', body: JSON.stringify({ img: 'data:image/jpeg;base64,AAAA' }) })).body;
  assert.equal(r.doc_no, '1101700230708'); assert.equal(r.gender, 'ชาย'); assert.equal(r.id_ok, true);
  assert.ok((await call('/api/app?part=idocr', { method: 'POST', body: JSON.stringify({ img: 'nope' }) })).body.error);
  delete process.env.PP_FAKE_OCR;
  ok('อ่านข้อมูลจากภาพบัตร: แยกเลขบัตร/เพศจากคำนำหน้า/ตรวจเลข');
}

// 11h) ไม่มีแชทบอท: ลูกค้าทักมา → เก็บไว้ให้พนักงานตอบ · รับสติกเกอร์/รูป · พนักงานส่งรูป/สติกเกอร์/ไฟล์
{
  delete process.env.AI_AUTOREPLY;
  const before = replies().length;
  const u = 'U_media_test';
  assert.equal(await webhook([lineEvent(u, 'สอบถามห้องว่างค่ะ')]), 200);
  await webhook([{ type: 'message', webhookEventId: 'evs1', replyToken: 'rts1', source: { type: 'user', userId: u }, message: { type: 'sticker', id: 'ms1', packageId: '446', stickerId: '1988' } }]);
  await webhook([{ type: 'message', webhookEventId: 'evi1', replyToken: 'rti1', source: { type: 'user', userId: u }, message: { type: 'image', id: 'mi1' } }]);
  assert.equal(replies().length, before, 'AI ต้องไม่ตอบอัตโนมัติ');
  const tid = psql('-c', `select id from chat_threads where line_user_id='${u}'`);
  assert.equal(psql('-c', `select needs_staff from chat_threads where id=${tid}`), 't');
  assert.equal(psql('-c', `select meta->>'sid' from chat_messages where thread_id=${tid} and meta->>'type'='sticker'`), '1988');
  assert.ok(psql('-c', `select meta->>'url' from chat_messages where thread_id=${tid} and meta->>'type'='image'`).startsWith('data:image/jpeg'));
  const chat = d => call('/api/app?part=chat', { method: 'POST', body: JSON.stringify(d) });
  const img = 'data:image/jpeg;base64,' + Buffer.from('jpeg-bytes').toString('base64');
  assert.equal((await chat({ k: 'send', key: 'db:' + tid, body: '[สติกเกอร์]', media: { type: 'sticker', pkg: '446', sid: '1989' } })).body.line, 'sent');
  assert.equal((await chat({ k: 'send', key: 'db:' + tid, body: '[รูปภาพ]', media: { type: 'image', data: img } })).body.line, 'sent');
  assert.equal((await chat({ k: 'send', key: 'db:' + tid, body: '[ไฟล์] ใบเสนอราคา.pdf', media: { type: 'file', name: 'ใบเสนอราคา.pdf', data: 'data:application/pdf;base64,' + Buffer.from('%PDF').toString('base64') } })).body.line, 'sent');
  assert.equal((await chat({ k: 'send', key: 'db:' + tid, body: 'x', media: { type: 'sticker', pkg: 'a', sid: 'b' } })).status, 400);
  assert.equal(psql('-c', `select count(*) from chat_messages where thread_id=${tid} and sender='พนักงาน' and meta ? 'type'`), '3');
  const L = (await call('/api/app?part=mods&since=x')).body.mods.linechat;
  assert.ok(L.includes('sticker/1988/') && L.includes('"t":"img"') && L.includes('ใบเสนอราคา.pdf') && L.includes('stkPanel'));
  process.env.AI_AUTOREPLY = '1';
  ok('ไม่มีแชทบอท + รับ/ส่ง สติกเกอร์ รูป ไฟล์ ในแชท LINE');
}

// 11i) แม่บ้าน: โซน/ห้อง → เช็คเอาท์แล้วมอบหมายอัตโนมัติ · งานบันทึกจริง · ลบรายชื่อโอนงาน
{
  const hk = d => call('/api/app?part=hk', { method: 'POST', body: JSON.stringify(d) });
  await hk({ k: 'staff_save', id: 'H1', name: 'ป้าใจ', on: true, zones: [], sort: 1 });
  await hk({ k: 'staff_save', id: 'H2', name: 'ดวน', on: true, zones: ['ตึกใหม่'], sort: 2 });
  await hk({ k: 'staff_save', id: 'H3', name: 'ใบ', on: true, zones: ['บ้านหลัง'], rooms: ['C01', 'C02'], sort: 3 });
  await hk({ k: 'staff_save', id: 'H4', name: 'แก้ว', on: true, zones: ['บ้านหลัง'], sort: 4 });
  let r = (await hk({ k: 'task_new', room: 'A03', kind: 'out' })).body; assert.equal(r.who, 'ดวน'); assert.equal(r.auto, true);
  r = (await hk({ k: 'task_new', room: 'C01', kind: 'out' })).body; assert.equal(r.who, 'ใบ');          // ห้องเฉพาะ
  r = (await hk({ k: 'task_new', room: 'C09', kind: 'out' })).body; assert.equal(r.who, 'แก้ว');        // ใบรับแค่ C01-C02
  await hk({ k: 'staff_save', id: 'H2', name: 'ดวน', on: false, zones: ['ตึกใหม่'], sort: 2 });
  r = (await hk({ k: 'task_new', room: 'A06', kind: 'out' })).body; assert.equal(r.who, '');            // ดวนหยุด ไม่มีใครในโซน
  assert.equal((await hk({ k: 'task_new', room: 'A03', kind: 'out' })).body.existed, true);            // กันซ้ำ
  const a03 = psql('-c', "select id from hk_task where room='A03' and not deleted");
  await hk({ k: 'task_upd', id: a03, st: 2 }); assert.equal(psql('-c', `select t2 is not null from hk_task where id=${a03}`), 't');
  await hk({ k: 'staff_del', id: 'H3', to: 'แก้ว' });
  assert.equal(psql('-c', "select who from hk_task where room='C01' and not deleted"), 'แก้ว');
  const M = (await call('/api/app?part=mods&since=x')).body.mods.hk;
  assert.ok(M.includes('"n":"แก้ว"') && !M.includes('"n":"ใบ"') && M.includes('dbid:') && M.includes('pickWho'));
  ok('แม่บ้าน: มอบหมายตามโซน/ห้อง/คนหยุด · งานทำความสะอาดบันทึกจริง · ลบรายชื่อโอนงาน');
  // วันทำงานประจำสัปดาห์ + สวิตช์วันนี้
  const dow = +psql('-c', 'select extract(dow from pp_today())::int');
  const notToday = [0, 1, 2, 3, 4, 5, 6].filter(d => d !== dow);
  await hk({ k: 'staff_save', id: 'H4', name: 'แก้ว', zones: ['บ้านหลัง'], sort: 4, days: notToday, ovr: null });
  r = (await hk({ k: 'task_new', room: 'C10', kind: 'out' })).body; assert.equal(r.who, '');            // วันนี้ไม่ใช่วันทำงาน
  await hk({ k: 'staff_save', id: 'H4', name: 'แก้ว', zones: ['บ้านหลัง'], sort: 4, days: notToday, ovr: true });
  r = (await hk({ k: 'task_new', room: 'C11', kind: 'out' })).body; assert.equal(r.who, 'แก้ว');        // กดมาทำงานวันนี้
  assert.equal(psql('-c', "select ovr_day = pp_today() from hk_staff where id='H4'"), 't');
  await hk({ k: 'staff_save', id: 'H4', name: 'แก้ว', zones: ['บ้านหลัง'], sort: 4, days: null, ovr: true }); // ตรงตาราง → ล้างค่าวันนี้
  assert.equal(psql('-c', "select ovr_on is null from hk_staff where id='H4'"), 't');
  assert.equal((await hk({ k: 'staff_save', id: 'H4', name: 'แก้ว', days: [9] })).status, 500);
  const M2 = (await call('/api/app?part=mods&since=x')).body.mods.hk;
  assert.ok(M2.includes('HK_DOW=') && M2.includes('data-hkd') && M2.includes('"days":null'));
  ok('แม่บ้าน: วันทำงานประจำสัปดาห์ + สวิตช์ทำงาน/หยุดเฉพาะวันนี้');
}

// 11j) บันทึกการจองย้อนหลัง (เจ้าของ) → เข้าพัก+เช็คเอาท์+จ่ายครบในครั้งเดียว · ไม่ถูกยกเลิกอัตโนมัติ · พนักงานจองย้อนหลังไม่ได้
{
  const act = d => call('/api/app?part=act', { method: 'POST', body: JSON.stringify(d) });
  const ci = plus(-40), co = plus(-38);
  const room = psql('-c', `select id from rooms r where not exists (select 1 from bookings b where b.room_id = r.id and b.status <> 'ยกเลิก' and daterange(b.check_in, b.check_out) && daterange('${ci}'::date, '${co}'::date)) order by id limit 1`);
  let a = (await act({ k: 'book', guest: 'คุณลูกค้าเก่า ทดสอบ', phone: '0899999999', check_in: ci, check_out: co, rooms: [{ room }], channel: 'โทรศัพท์', pay: 'later', m: 'transfer' })).body;
  assert.ok(String(a.error || '').includes('ผ่านมาแล้ว'));                                     // ไม่ติ๊กย้อนหลัง → ไม่ให้จอง
  a = (await act({ k: 'book', backdate: true, guest: 'คุณลูกค้าเก่า ทดสอบ', phone: '0899999999', check_in: ci, check_out: plus(1), rooms: [{ room }], pay: 'now', m: 'transfer' })).body;
  assert.ok(String(a.error || '').includes('ไม่เกินวันนี้'));
  a = (await act({ k: 'book', backdate: true, guest: 'คุณลูกค้าเก่า ทดสอบ', phone: '0899999999', check_in: ci, check_out: co, rooms: [{ room }], channel: 'โทรศัพท์', pay: 'now', m: 'transfer' })).body;
  assert.equal(a.ok, true); const no = a.nos[0];
  assert.equal(psql('-c', `select string_agg(kind, ',' order by id) from ops where booking_no='${no}'`), 'checkin,pay,checkout,book');
  rpc('pp_noshow()');
  assert.equal(psql('-c', `select status from bookings where booking_no='${no}'`), 'ยืนยันแล้ว');
  const M = (await call('/api/app?part=mods&since=x')).body.mods;
  const i = M.fin.indexOf('let BILLS='); const fb = JSON.parse(M.fin.slice(i + 10, M.fin.indexOf(';\n', i))).find(x => x.no === no);
  assert.ok(fb && fb.paid > 0 && fb.paid === fb.total);
  assert.ok(M.book.includes('"no":"' + no + '"') && M.book.includes('fBack'));
  ok('บันทึกการจองย้อนหลัง: เข้าพัก/เช็คเอาท์/จ่ายครบในครั้งเดียว · ไม่ถูกยกเลิกอัตโนมัติ · ต้องติ๊กย้อนหลังเท่านั้น');
}

// 11k) เมนูการเงิน: บันทึกสถานะ (บริการ/รายการรับ-จ่าย/กะ) แล้วโหลดกลับมาได้
{
  const st = { v: 1, bills: {}, sv: [], txns: [{ id: 't1_x', time: Date.now(), item: 'ทดสอบรายการ', bk: '', cat: 'อื่นๆ', method: 'เงินสด', type: 'in', amount: 50, who: 'ดวน', auto: false }], shifts: {}, shiftLog: [], vars: [], closed: [], hf: {}, banks: [] };
  assert.equal((await call('/api/app?part=fin', { method: 'POST', body: JSON.stringify(st) })).body.ok, true);
  const F = (await call('/api/app?part=mods&since=x')).body.mods.fin;
  assert.ok(F.includes('const FIN_STATE=') && F.includes('ทดสอบรายการ') && F.includes('ppFinSave'));
  ok('เมนูการเงิน: บันทึกสถานะแล้วโหลดกลับมาได้');
}

// 11l) เมนูอื่นๆ: แม่บ้าน (ของที่พบ) บันทึกแล้วโหลดกลับมาได้ · เมนูที่ไม่รู้จักถูกปฏิเสธ
{
  const mod = d => call('/api/app?part=mod', { method: 'POST', body: JSON.stringify(d) });
  assert.equal((await mod({ k: 'hk', data: { found: [{ id: 7, room: 'A01', name: 'ร่มทดสอบระบบ', st: 1 }], lost: [], repairs: [] } })).body.ok, true);
  assert.equal((await mod({ k: 'xx', data: {} })).status, 500);
  const H = (await call('/api/app?part=mods&since=x')).body.mods.hk;
  assert.ok(H.includes('PPM_STATE=') && H.includes('ร่มทดสอบระบบ'));
  ok('เมนูอื่นๆ: บันทึกสถานะแล้วโหลดกลับมาได้');
}

// 11m) ศูนย์ไอเดีย: Agent Insight ใช้ตัวเลขจริง · เก็บไว้ใช้ทั้งวัน · ข่าวรับเฉพาะลิงก์ที่มาจากผลค้นเว็บจริง
{
  const it = (k, x = {}) => ({ cat: 'ห้องว่าง', tn: 'hi', n: '95%', u: 'ว่าง', t: 'ข้อ ' + k, found: 'พบ', nums: [{ l: 'อาทิตย์', v: '5%' }], why: 'เพราะ', act: 'ทำ', src: 'booking', ...x });
  script.push(p => { const d = JSON.parse(p.messages[0].content); assert.ok(d.rooms_total > 0 && d.bookings.active > 0 && d.occupancy_by_weekday_last60_next14.length === 7);
    assert.equal(p.tools[0].name, 'save_insights');
    return { stop_reason: 'tool_use', content: [{ type: 'tool_use', id: 'tu1', name: 'save_insights',
      input: { items: [it(1, { t: 'ห้องว่าง <script>x</script>' }), it(2), it(3), it(4), it(5), it(6), { cat: 'ไม่มีหัวข้อ' }] } }] }; });
  let r = await call('/api/insight');
  assert.equal(r.body.items.length, 6); assert.ok(!r.body.items[0].t.includes('<script>')); assert.ok(r.body.basis.bookings > 0);
  r = await call('/api/insight'); assert.equal(r.body.items.length, 6);                     // ใช้ของเดิม ไม่เรียก AI ซ้ำ
  script.push(p => { assert.equal(p.tools[0].name, 'web_search');
    return { stop_reason: 'end_turn', content: [
      { type: 'web_search_tool_result', content: [{ type: 'web_search_result', url: 'https://news.example.th/a', title: 'ข่าวจริง' }] },
      { type: 'tool_use', id: 'sn', name: 'save_news', input: { news: [{ cat: 'โรงงาน · น้ำพอง', tn: 'hi', t: 'ข่าวจริง', sum: 's', why: 'w', url: 'https://news.example.th/a/', src: 'news.example.th', end: '2099-12-31' },
                                                    { t: 'งานจบแล้ว', url: 'https://news.example.th/a', end: '2020-01-01' },
                                                    { t: 'ข่าวแต่ง', url: 'https://fake.example/b' }], trends: [] } }] }; });
  r = await call('/api/news');
  assert.equal(r.body.news.length, 1); assert.equal(r.body.news[0].url, 'https://news.example.th/a/'); assert.equal(r.body.raw.news, 3); assert.equal(r.body.raw.old, 1);
  const M = (await call('/')).body;
  assert.ok(M.includes("loadAI('insight')") && M.includes('data-ai=\\"insight\\"'));
  ok('ศูนย์ไอเดีย: Agent Insight จากข้อมูลจริง (เก็บใช้ทั้งวัน) · ข่าวรับเฉพาะลิงก์จากผลค้นเว็บ');
}

// 11n) แผนการตลาดจาก AI: ใช้ได้เฉพาะกลุ่ม/โปร/ช่องทางที่มีในระบบ · เก็บไว้ใช้ซ้ำเมื่อเลือกชุดเดิม
{
  const body = { mode: 'new', items: [{ t: 'คืนวันอาทิตย์ห้องว่าง 95%', detail: 'd', nums: 'n' }], price: 597,
    segments: [{ id: 's1', n: 'บริษัท', c: 8, u: 'บริษัท', line: 5, email: 8, nights: 3.4 }], promos: [{ id: 'p0', n: 'ไม่มีโปรโมชัน', f: 1 }, { id: 'p3', n: 'ลด 30%', f: 0.7 }] };
  script.push(p => { assert.equal(p.tools[0].name, 'save_plans'); assert.ok(JSON.parse(p.messages[0].content).segments.length === 1);
    return { stop_reason: 'tool_use', content: [{ type: 'tool_use', id: 'tp', name: 'save_plans', input: { plans: [
      { name: 'เช็คอินคืนอาทิตย์', why: 'w', goal: 'g', seg: ['s1', 'sX'], ch: ['line', 'tiktok'], promo: 'p3', acc: [40, 20], tools: ['msg', 'hack'], level: 'ง่าย', from: [1, 9] },
      { name: 'โปรใหม่', why: 'w', goal: 'g', seg: ['s1'], ch: ['email'], promo: 'new', new_promo: { n: 'แถมอาหารเช้า', s: 's', f: 0.2 }, acc: [5, 10], tools: [], level: 'ยาก', from: [1] },
      { name: 'ไม่มีกลุ่ม', why: 'w', goal: 'g', seg: ['zz'], ch: ['line'], promo: 'p0', acc: [1, 2], tools: [], level: 'ง่าย', from: [] }] } }] }; });
  let r = await call('/api/plan', { method: 'POST', body: JSON.stringify(body) });
  assert.equal(r.body.plans.length, 2); const [a, b] = r.body.plans;
  assert.deepEqual([a.seg, a.ch, a.tools, a.acc, a.from, a.rec], [['s1'], ['line'], ['msg'], [20, 40], [1], true]);
  assert.equal(b.newPromo.f, 0.5);
  r = await call('/api/plan', { method: 'POST', body: JSON.stringify(body) }); assert.equal(r.body.cached, true);   // ชุดเดิมไม่เรียก AI ซ้ำ
  ok('แผนการตลาดจาก AI: กรองเฉพาะกลุ่ม/ช่องทางที่มีจริง · ใช้ซ้ำเมื่อเลือกชุดเดิม');
}

// 11o) ลูกค้าจองเองผ่านหน้าจอ LINE (LIFF): จองหลายประเภท · อาหารเช้ารายห้อง · การ์ด + QR พร้อมเพย์ · ส่งรูปในแชท = สลิป
{
  process.env.LIFF_ID = '2000000000-testliff';
  const ci = plus(40), co = plus(42);
  const cfg = (await call(`/api/liff?ci=${ci}&co=${co}`)).body;
  assert.ok(cfg.types.length > 1 && cfg.bf === 170);
  const free = cfg.types.filter(t => t.free > 0).slice(0, 2);
  globalThis.__ppLineOutbox.length = 0;
  let r = await call('/api/liff', { method: 'POST', body: JSON.stringify({ idToken: 'dev:Uliff1', ci, co, adults: 2, kids: 0,
    items: [{ zone: free[0].zone, type: free[0].type, count: 1, bf: true }, { zone: free[1].zone, type: free[1].type, count: 1, bf: false }],
    name: 'ลูกค้า หน้าจอ', phone: '0899990000', idno: '1234567890123', consent: true, purpose: 'ทำงาน' }) });
  assert.equal(r.status, 200, JSON.stringify(r.body)); assert.equal(r.body.nos.length, 2);
  assert.equal(r.body.total, (free[0].rate + free[1].rate) * 2 + 170 * 1 * 2);
  const card = globalThis.__ppLineOutbox.find(x => x.path === '/message/push');
  assert.ok(card && card.body.messages[0].type === 'flex' && !card.body.messages[0].contents.hero, 'การ์ดไม่มี QR');
  assert.ok(JSON.stringify(card.body.messages[0].contents.footer).includes('liff.line.me/2000000000-testliff?no=' + r.body.nos[0]), 'ปุ่มเปิดรายละเอียดการจอง');
  const nosA = r.body.nos;
  // หน้ารายละเอียดการจอง: เจ้าของการจองดูได้ · LINE อื่นดูไม่ได้ · ยังไม่จ่าย → มี QR
  const dt = await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'detail', idToken: 'dev:Uliff1', no: r.body.nos[0] }) });
  assert.equal(dt.status, 200, JSON.stringify(dt.body)); assert.equal(dt.body.nos.length, 2); assert.equal(dt.body.paid, false);
  assert.equal(dt.body.due, r.body.total); assert.ok(dt.body.qr.includes('/api/qr?no=' + r.body.nos[0]));
  assert.ok(!/1234567890123|0899990000/.test(JSON.stringify(dt.body)), 'ไม่ส่งเลขบัตร/เบอร์');
  assert.equal((await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'detail', idToken: 'dev:Uother', no: r.body.nos[0] }) })).status, 400);
  assert.equal((await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'detail', idToken: 'dev:Uliff1', no: "x'; drop" }) })).status, 400);
  const png = await fetch(base + '/api/qr?no=' + r.body.nos[0]); assert.equal(png.headers.get('content-type'), 'image/png');
  assert.deepEqual([...new Uint8Array(await png.arrayBuffer()).slice(1, 4)], [80, 78, 71]);
  // ไม่ยินยอม / เกิน 4 ห้อง → ไม่จอง
  r = await call('/api/liff', { method: 'POST', body: JSON.stringify({ idToken: 'dev:Uliff1', ci, co, adults: 1, items: [{ zone: free[0].zone, type: free[0].type, count: 1 }],
    name: 'x', phone: '0899990000', idno: '1234567890123', consent: false }) });
  assert.equal(r.status, 400);
  // ส่งรูปในแชท → บันทึกชำระ + ป้ายสลิปยังไม่ตรวจ
  await webhook([{ type: 'message', webhookEventId: 'ev-slip', replyToken: 'rt-slip', source: { type: 'user', userId: 'Uliff1' }, message: { type: 'image', id: 'mslip' } }]);
  const paid = rpc(`(select count(*) from ops where kind = 'pay' and data->>'unchecked' = 'true')`);
  assert.equal(paid, 2);
  const dt2 = (await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'detail', idToken: 'dev:Uliff1', no: nosA[0] }) })).body;
  assert.equal(dt2.paid, true); assert.equal(dt2.slip_unchecked, true); assert.equal(dt2.qr, null);
  // เลือก "ชำระวันเข้าพัก" → การ์ดไม่มี QR · รูปในแชทไม่นับเป็นสลิป
  globalThis.__ppLineOutbox.length = 0;
  r = await call('/api/liff', { method: 'POST', body: JSON.stringify({ idToken: 'dev:Uliff2', ci, co, adults: 1, kids: 0, pay: 'arrival',
    items: [{ zone: free[0].zone, type: free[0].type, count: 1, bf: false }], name: 'จ่ายหน้างาน', phone: '0899990001', idno: '1234567890123', consent: true }) });
  assert.equal(r.status, 200, JSON.stringify(r.body)); assert.equal(r.body.pay, 'arrival');
  const card2 = globalThis.__ppLineOutbox.find(x => x.path === '/message/push').body.messages[0];
  assert.ok(!card2.contents.hero && !card2.quickReply && card2.contents.footer);
  assert.equal(rpc(`(select details->>'liff_pay' from bookings where booking_no = '${r.body.nos[0]}')`), 'arrival');
  await webhook([{ type: 'message', webhookEventId: 'ev-slip2', replyToken: 'rt-slip2', source: { type: 'user', userId: 'Uliff2' }, message: { type: 'image', id: 'mslip2' } }]);
  assert.equal(rpc(`(select count(*) from ops where kind = 'pay' and booking_no = '${r.body.nos[0]}')`), 0);
  // ลูกค้าเดิม: ใช้ข้อมูลเดิม (เลขบัตรปิดบางหลัก) · จ่ายเงินประกันพร้อมค่าห้อง · แนบสลิปในหน้าจอจอง
  const pv = (await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'prev', idToken: 'dev:Uliff1' }) })).body.prev;
  assert.equal(pv.name, 'ลูกค้า หน้าจอ'); assert.equal(pv.doc, 'x-xxxx-xxxxx-12-3'); assert.ok(!/0899990000/.test(JSON.stringify(pv)));
  assert.equal((await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'prev', idToken: 'dev:Unobody' }) })).body.prev, null);
  globalThis.__ppLineOutbox.length = 0;
  r = await call('/api/liff', { method: 'POST', body: JSON.stringify({ idToken: 'dev:Uliff1', ci: plus(50), co: plus(51), adults: 2, kids: 0, pay: 'now', dep: true, usePrev: true,
    items: [{ zone: free[0].zone, type: free[0].type, count: 2, bf: false }], name: pv.name, phone: pv.phone, idno: '', consent: true }) });
  assert.equal(r.status, 200, JSON.stringify(r.body)); assert.equal(r.body.dep, 400); assert.equal(r.body.total, free[0].rate * 2 + 400);
  assert.equal(rpc(`(select phone from guests where line_user_id = 'Uliff1')`), '0899990000');
  assert.equal(rpc(`(select count(*) from guest_docs where line_user_id = 'Uliff1' and doc_no = '1234567890123')`), 2);
  const png2 = await fetch(base + r.body.qr); assert.equal(png2.status, 200);
  const nos3 = r.body.nos;
  let sl = await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'slip', idToken: 'dev:Uliff1', img: 'data:image/jpeg;base64,' + Buffer.from('fake-slip').toString('base64') }) });
  assert.equal(sl.status, 200, JSON.stringify(sl.body)); assert.equal(sl.body.total, free[0].rate * 2 + 400);
  assert.equal(rpc(`(select sum((data->>'dep')::int) from ops where kind = 'pay' and booking_no in (${nos3.map(n => `'${n}'`).join(',')}))`), 400);
  assert.ok(globalThis.__ppLineOutbox.some(x => x.path === '/message/push' && /ได้รับสลิปแล้ว/.test(x.body.messages[0].altText)));
  sl = await call('/api/liff', { method: 'POST', body: JSON.stringify({ action: 'slip', idToken: 'dev:Uliff1', img: 'data:image/jpeg;base64,eA==' }) });
  assert.equal(sl.status, 400);
  ok('จองผ่านหน้าจอ LINE: หลายประเภท · อาหารเช้ารายห้อง · การ์ด QR พร้อมเพย์ · ส่งสลิปในแชท = ชำระ (รอตรวจ) · เลือกชำระวันเข้าพักได้ · ใช้ข้อมูลเดิม · เงินประกัน + แนบสลิปในหน้าจอ');
}

// 11p) ข้อความอัตโนมัติ: สวิตช์หลัก · ข้อมูลโรงแรมว่าง = ข้าม · ต้อนรับตอนมอบคีย์การ์ด · เช็คเอาท์ + ให้คะแนน 1-5 · เช้าวันเข้าพัก (ห้องพร้อม/ไม่พร้อม) · เตือนเช็คเอาท์ · กันส่งซ้ำ
{
  const today = plus(0);
  const act = d => call('/api/app?part=act', { method: 'POST', body: JSON.stringify(d) });
  const save = d => call('/api/app?part=amsave', { method: 'POST', body: JSON.stringify(d) });
  const logOf = (kind, no) => { const o = psql('-c', `select to_jsonb(l) from auto_msg_log l where kind = '${kind}' and booking_no = '${no}'`); return o ? JSON.parse(o) : null; };
  const cnt = () => Number(psql('-c', 'select count(*) from auto_msg_log'));
  const free = (await call(`/api/liff?ci=${today}&co=${plus(2)}`)).body.types.filter(t => t.free > 0);
  const book = async (uid, name, ci = today, co = plus(2)) => {
    const t = free[0];
    const r = await call('/api/liff', { method: 'POST', body: JSON.stringify({ idToken: 'dev:' + uid, ci, co, adults: 1, kids: 0, pay: 'arrival',
      items: [{ zone: t.zone, type: t.type, count: 1, bf: false }], name, phone: '0899991111', idno: '1234567890123', consent: true }) });
    assert.equal(r.status, 200, JSON.stringify(r.body)); return r.body.nos[0];
  };
  const hotel = { wifi_name: 'PobrakWiFi', wifi_pass: 'pw12345', breakfast: '06:00–10:00', phone: '081-234-5678', map: 'https://maps.app.goo.gl/test', review_url: 'https://g.page/r/test' };

  // เฉพาะเจ้าของตั้งค่าได้ · ลิงก์ต้องเป็น https
  assert.equal((await fetch(base + '/api/app?part=amsave', { method: 'POST', body: '{"on":true}' })).status, 403);
  assert.equal((await save({ map: 'ไม่ใช่ลิงก์' })).status, 500);
  let ov = (await call('/api/app?part=amcfg')).body;
  assert.equal(ov.on, false);   // ค่าเริ่มต้นปิดอยู่
  assert.equal(ov.kinds.welcome.state, 'skip');

  // 1) สวิตช์หลักปิด → ไม่ส่งอะไรเลย
  const A = await book('Uam1', 'คุณธนกฤต วงศ์ศรีแก้ว');
  await act({ k: 'checkin', no: A });
  assert.equal(cnt(), 0); ok('ข้อความอัตโนมัติ: สวิตช์หลักปิดอยู่ = ไม่ส่งหาลูกค้าเลย');

  // 2) เปิดสวิตช์ + ข้อมูลโรงแรมยังไม่ครบ (ไม่มีไวไฟ) → ข้ามและบอกสาเหตุ
  await save({ on: true, breakfast: hotel.breakfast, phone: hotel.phone, map: hotel.map, review_url: hotel.review_url });
  const B = await book('Uam2', 'คุณสมหญิง ใจดี');
  await act({ k: 'checkin', no: B });
  let l = logOf('welcome', B);
  assert.equal(l.status, 'skipped'); assert.ok(l.reason.includes('ชื่อไวไฟ') && l.reason.includes('รหัสไวไฟ'));
  ok('ข้อมูลโรงแรมที่ต้องใช้ว่างอยู่ → ข้ามข้อความต้อนรับ พร้อมบอกสาเหตุ');

  // 3) ไวไฟครบ → มอบคีย์การ์ดแล้วส่งการ์ดต้อนรับทันที (ครั้งเดียว)
  await save({ wifi_name: hotel.wifi_name, wifi_pass: hotel.wifi_pass });
  await act({ k: 'checkin', no: A });   // กดซ้ำ/ย้อนกลับแล้วกดใหม่ก็ส่งซ้ำไม่ได้
  l = logOf('welcome', A);
  assert.equal(l.status, 'sent');
  const w = JSON.stringify(l.payload.messages);
  assert.ok(w.includes('PobrakWiFi') && w.includes('pw12345') && w.includes('06:00–10:00') && w.includes('12:00') && w.includes('ธนกฤต') && w.includes('tel:0812345678'));
  await act({ k: 'checkin', no: A });
  assert.equal(Number(psql('-c', `select count(*) from auto_msg_log where kind = 'welcome' and booking_no = '${A}'`)), 1);
  assert.ok(!/pw12345/.test(psql('-c', `select string_agg(body, ' ') from chat_messages where body like '%ส่งอัตโนมัติ%'`)), 'ไม่เอารหัสไวไฟลงแชท');
  ok('มอบคีย์การ์ดแล้ว → ส่งการ์ดต้อนรับ (ไวไฟ/อาหารเช้า/เช็คเอาท์/โทร) ครั้งเดียว');

  // 4) เมนู CRM ปิดข้อความนี้ (สวิตช์ "ใช้งาน") → ไม่ส่ง
  await call('/api/app?part=mod', { method: 'POST', body: JSON.stringify({ k: 'crmtool', data: { ms: [{ id: 'thanks', st: 'off' }, { id: 'stay', st: 'on' }, { id: 'pre', st: 'on' }] } }) });
  const C = await book('Uam3', 'คุณมานะ ตั้งใจ');
  await act({ k: 'checkin', no: C }); await act({ k: 'checkout', no: C });
  assert.equal(logOf('rate', C), null);
  await call('/api/app?part=mod', { method: 'POST', body: JSON.stringify({ k: 'crmtool', data: { ms: [{ id: 'thanks', st: 'on' }, { id: 'stay', st: 'on' }, { id: 'pre', st: 'on' }] } }) });
  ok('ปิดข้อความในเมนู CRM → ระบบไม่ส่งข้อความนั้น');

  // 5) เช็คเอาท์ → การ์ดดาว (ขั้น 1) → การ์ดรายเรื่อง (ขั้น 2) → ข้อความขอบคุณ/ขอโทษ (ขั้น 3)
  await act({ k: 'checkout', no: A });
  l = logOf('rate', A); assert.equal(l.status, 'sent');
  const rm = JSON.stringify(l.payload.messages);
  assert.ok(rm.includes('pp_rate|' + A + '|1') && rm.includes('pp_rate|' + A + '|5') && rm.includes('ธนกฤต') && rm.includes('ขั้น 1 / 3'));
  assert.ok(!rm.includes('จองอีกครั้ง') && !rm.includes('จองห้องพัก'), 'ไม่มีปุ่มจองอีกครั้ง');
  const postback = (uid, data, id) => ({ type: 'postback', webhookEventId: id, replyToken: 'rt-' + id, source: { type: 'user', userId: uid }, postback: { data } });
  const lastReply = () => JSON.stringify(replies().at(-1).body.messages);
  globalThis.__ppLineOutbox.length = 0;
  await webhook([postback('Uam1', `pp_rate|${A}|5`, 'pb1')]);
  let rp = lastReply();   // ขั้น 2: การ์ดปัด · A ไม่ได้สั่งอาหารเช้า → ไม่มีใบ "อาหาร"
  assert.ok(rp.includes('carousel') && rp.includes(`pp_topic|${A}|room|5`) && rp.includes(`pp_topic|${A}|value|1`) && !rp.includes('|food|') && rp.includes(`pp_done|${A}`));
  assert.equal(rpc(`(select score from auto_msg_rating where key = '${A}')`), 5);
  await webhook([postback('Uam1', `pp_rate|${A}|1`, 'pb2')]);   // กดดาวซ้ำ ไม่เปลี่ยนคะแนน
  assert.equal(rpc(`(select score from auto_msg_rating where key = '${A}')`), 5);
  assert.ok(lastReply().includes('บันทึกคะแนนของคุณไว้แล้ว'));
  await webhook([postback('Uother', `pp_rate|${A}|2`, 'pb3')]);   // คนอื่นให้คะแนนการจองของเราไม่ได้
  assert.equal(rpc(`(select count(*) from auto_msg_rating where key = '${A}')`), 1);
  const r0 = replies().length;
  for (const [t, v, i] of [['room', 5, 'a1'], ['facility', 3, 'a2'], ['service', 5, 'a3']]) await webhook([postback('Uam1', `pp_topic|${A}|${t}|${v}`, i)]);
  assert.equal(replies().length, r0, 'ยังตอบไม่ครบ ไม่ส่งอะไรเพิ่ม');
  await webhook([postback('Uam1', `pp_topic|${A}|value|5`, 'a4')]);   // ตอบครบ 4 เรื่อง → ขั้น 3 เอง
  rp = lastReply();
  assert.ok(rp.includes('ขอบคุณมากค่ะ') && rp.includes('https://g.page/r/test') && !rp.includes('★'), rp);
  assert.deepEqual(JSON.parse(psql('-c', `select topics::text from auto_msg_rating where key = '${A}'`)), { room: 5, facility: 3, service: 5, value: 5 });
  const r1 = replies().length; await webhook([postback("Uam1", `pp_done|${A}`, "a5")]); assert.equal(replies().length, r1, 'ขั้น 3 ส่งครั้งเดียว');
  // ไม่พอใจ: ภาพรวม 4 แต่เลือก "ปรับปรุง" เรื่องอาหาร (B สั่งอาหารเช้า) → ขอโทษ + แจ้งผู้จัดการ · ตอบไม่ครบแล้วกด "ข้าม"
  psql('-c', `update bookings set details = details || '{"bf":170}'::jsonb where booking_no = '${B}'`);
  await act({ k: 'checkin', no: B }); await act({ k: 'checkout', no: B });
  await webhook([postback('Uam2', `pp_rate|${B}|4`, 'pb4')]);
  assert.ok(lastReply().includes(`pp_topic|${B}|food|3`), 'B สั่งอาหารเช้า → มีใบอาหาร');
  await webhook([postback('Uam2', `pp_topic|${B}|food|1`, 'b1')]);
  await webhook([postback('Uam2', `pp_done|${B}`, 'b2')]);
  rp = lastReply();
  assert.ok(rp.includes('ขอโทษด้วยนะคะ') && rp.includes('อาหาร') && !rp.includes('Google'), rp);
  assert.equal(psql('-c', `select needs_staff from chat_threads where line_user_id = 'Uam2'`), 't');
  assert.ok(psql('-c', `select handoff_reason from chat_threads where line_user_id = 'Uam2'`).includes('อาหาร'));
  // ตัวอย่างจากหน้าตั้งค่า (key TEST) ไม่แตะฐานข้อมูล
  await webhook([postback('Uam1', 'pp_rate|TEST|3', 'pt1')]); assert.ok(lastReply().includes('carousel'));
  await webhook([postback('Uam1', 'pp_done|TEST', 'pt2')]); assert.ok(lastReply().includes('ขอบคุณมากค่ะ'));
  assert.equal(rpc(`(select count(*) from auto_msg_rating where key = 'TEST')`), 0);
  ok('เช็คเอาท์ → ดาวภาพรวม → การ์ดรายเรื่อง (ข้ามอาหารถ้าไม่สั่งอาหารเช้า) → ขอบคุณ+ลิงก์รีวิว / ขอโทษ+แจ้งผู้จัดการ · ส่งขั้น 3 ครั้งเดียว · กดซ้ำ/คนอื่นกดไม่ได้');

  // 6) เช้าวันเข้าพัก 10:00: ห้องพร้อม / ห้องยังไม่พร้อม (มีงานทำความสะอาดค้าง) · นอกช่วงเวลาไม่ส่ง · ไม่ส่งซ้ำ
  const D1 = await book('Uam4', 'คุณพร้อม ใจดี'), D2 = await book('Uam5', 'คุณรอ ก่อนนะ');
  const room2 = psql('-c', `select room_id from bookings where booking_no = '${D2}'`);
  psql('-c', `update hk_task set st = 5 where st < 5`);                                   // ห้องอื่นสะอาดหมดแล้ว
  psql('-c', `insert into hk_task (room, kind, st) values ('${room2}', 'out', 2)`);       // ห้องของ D2 แม่บ้านยังทำไม่เสร็จ
  const tick = async t => { process.env.PP_NOW = t; try { return (await call('/api/app?part=tick')).body; } finally { delete process.env.PP_NOW; } };
  let tk = await tick(today + 'T09:00');
  assert.equal(logOf('arrive', D1), null);
  tk = await tick(today + 'T10:05');
  const a1 = logOf('arrive', D1), a2 = logOf('arrive', D2);
  assert.equal(a1.status, 'sent'); assert.equal(a2.status, 'sent');
  assert.ok(JSON.stringify(a1.payload.messages).includes('ห้องพร้อมแล้ว') && JSON.stringify(a1.payload.messages).includes('https://maps.app.goo.gl/test'));
  assert.ok(JSON.stringify(a2.payload.messages).includes('เช็คอินได้ตั้งแต่ 14:00') && !JSON.stringify(a2.payload.messages).includes('ห้องพร้อมแล้ว'));
  const before = cnt(); await tick(today + 'T10:40'); assert.equal(cnt(), before);
  ok('เช้าวันเข้าพัก 10:00: ห้องพร้อม → "เช็คอินได้เลย" · ห้องยังไม่พร้อม → "เช็คอินได้ตั้งแต่ 14:00" · ไม่ส่งซ้ำ · นอกเวลาไม่ส่ง');

  await act({ k: 'checkin', no: D1 });

  // 8) ส่งทดสอบ: เลือกบัญชีได้ · ไม่เข้าประวัติกันซ้ำ · ข้อมูลไม่ครบ = บอกสาเหตุ
  ov = (await call('/api/app?part=amcfg')).body;
  assert.ok(ov.people.some(p => p.id === 'Uam1') && ov.stats['welcome:sent'] >= 1);
  const n0 = cnt();
  const t1 = await call('/api/app?part=amtest', { method: 'POST', body: JSON.stringify({ kind: 'arrive', variant: 'wait', to: 'Uam1' }) });
  assert.equal(t1.status, 200, JSON.stringify(t1.body)); assert.equal(cnt(), n0);
  await save({ wifi_name: '' });
  const t2 = await call('/api/app?part=amtest', { method: 'POST', body: JSON.stringify({ kind: 'welcome', to: 'Uam1' }) });
  assert.equal(t2.status, 400); assert.ok(t2.body.error.includes('ชื่อไวไฟ'));
  await save({ on: false });
  assert.equal((await call('/api/app?part=tick')).body.on, false);
  ok('ส่งทดสอบหาบัญชีที่เลือก (ไม่นับเป็นการส่งจริง) · ปิดสวิตช์หลัก = ตัวตั้งเวลาไม่ทำงาน');
}

// 12) กันเดา PIN
for (let i = 0; i < 8; i++) await call('/api/app?part=pin', { method: 'POST', body: JSON.stringify({ role: 'owner', pin: '000000' }) });
assert.equal((await call('/api/app?part=pin', { method: 'POST', body: JSON.stringify({ role: 'owner', pin: '246810' }) })).status, 429);
ok('ใส่ PIN ผิด 8 ครั้ง → ล็อก 15 นาที');

// 13) health
const h = await (await fetch(base + '/api/health')).json();
assert.equal(h.database, 'ok'); ok('หน้าตรวจการตั้งค่าทำงาน');

assert.equal(script.length, 0, 'สคริปต์ AI ใช้ไม่หมด');
srv.close();
console.log(`\nผ่านทั้งหมด ${pass} ข้อ`);
