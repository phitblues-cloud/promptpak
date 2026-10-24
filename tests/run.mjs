// ทดสอบทั้งเส้นทางในเครื่อง: LINE → AI (จำลอง) → ฐานข้อมูล → หน้าจอ v196
// ใช้: LOCAL_PG=postgresql://... node tests/run.mjs
import { createHmac } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

Object.assign(process.env, { LOCAL_DEV: '1', LINE_CHANNEL_SECRET: 'test-secret', APP_SECRET: 'test-app', OWNER_PIN: '246810', STAFF_PIN: '135790' });
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
assert.deepEqual(Object.keys(mods.mods).sort(), ['book', 'cust', 'fin', 'hk', 'home', 'linechat']);
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
