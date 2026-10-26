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
