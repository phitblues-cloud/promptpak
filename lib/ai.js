// AI (Claude API) — เรียกจากหลังบ้านเท่านั้น คีย์ไม่เคยอยู่ในหน้าเว็บ
import { rpc } from './db.js';
import { bangkokDate } from './http.js';

const MODEL = () => process.env.ANTHROPIC_MODEL || 'claude-sonnet-5-5';

export async function claude(payload) {
  if (globalThis.__ppFakeClaude) return globalThis.__ppFakeClaude(payload); // โหมดทดสอบ
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY');
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: MODEL(), max_tokens: 1200, ...payload }),
  });
  if (!res.ok) throw new Error(`Claude API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res.json();
}

const textOf = r => (r.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n').trim();

// ---------- ปฏิทิน 21 วันข้างหน้า ช่วย AI ตีความ "พรุ่งนี้" "ศุกร์หน้า" "27 ต.ค." ให้ถูก ----------
const TH_DAY = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์'];
const TH_MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
export function thDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  const wd = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return `${TH_DAY[wd]} ${d} ${TH_MON[m - 1]} ${y + 543}`;
}
function calendar(today, n = 21) {
  const [y, m, d] = today.split('-').map(Number);
  const out = [];
  for (let i = 0; i < n; i++) {
    const iso = new Date(Date.UTC(y, m - 1, d + i)).toISOString().slice(0, 10);
    out.push(`${iso} = ${thDate(iso)}${i === 0 ? ' (วันนี้)' : i === 1 ? ' (พรุ่งนี้)' : ''}`);
  }
  return out.join('\n');
}

// ---------- AI รับจองผ่าน LINE ----------
const BOOKING_TOOLS = [
  {
    name: 'check_availability',
    description: 'ดูจำนวนห้องว่างจริงแยกตามประเภทห้อง และราคาต่อคืน สำหรับช่วงวันที่ระบุ ต้องเรียกทุกครั้งก่อนบอกลูกค้าว่าห้องว่างหรือบอกราคา',
    input_schema: {
      type: 'object',
      properties: {
        check_in: { type: 'string', description: 'วันเข้าพัก YYYY-MM-DD (ค.ศ.)' },
        check_out: { type: 'string', description: 'วันเช็คเอาท์ YYYY-MM-DD (ค.ศ.) ต้องหลัง check_in' },
      },
      required: ['check_in', 'check_out'],
    },
  },
  {
    name: 'create_booking',
    description: 'สร้างการจองจริงและยืนยันทันที เรียกได้เมื่อ (1) ลูกค้าให้ชื่อ เบอร์โทร วันเข้า-ออก ประเภทห้องและจำนวนห้องครบ (2) สรุปรายการให้ลูกค้าดูแล้ว และ (3) ลูกค้าตอบตกลง/ยืนยันแล้วเท่านั้น จองได้ไม่เกิน 4 ห้องต่อครั้ง',
    input_schema: {
      type: 'object',
      properties: {
        guest_name: { type: 'string', description: 'ชื่อ-นามสกุลผู้จอง' },
        phone: { type: 'string', description: 'เบอร์โทรศัพท์' },
        company: { type: 'string', description: 'ชื่อบริษัท/หน่วยงาน (ถ้ามี)' },
        check_in: { type: 'string', description: 'YYYY-MM-DD' },
        check_out: { type: 'string', description: 'YYYY-MM-DD' },
        items: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              room_type: { type: 'string', enum: ['สแตนดาร์ด (เตียงคู่)', 'ดีลักซ์ (เตียงใหญ่)', 'บ้านพัก', 'บ้านพัก (ใหญ่)'] },
              count: { type: 'integer', minimum: 1 },
            },
            required: ['room_type', 'count'],
          },
        },
        note: { type: 'string', description: 'คำขอพิเศษ เช่น ขอใบกำกับภาษี ขอห้องติดกัน' },
      },
      required: ['guest_name', 'phone', 'check_in', 'check_out', 'items'],
    },
  },
  {
    name: 'handoff_to_staff',
    description: 'ส่งเรื่องให้พนักงานดูแลต่อ ใช้เมื่อ: จอง 5 ห้องขึ้นไป, ขอเครดิต/วางบิลบริษัท, ขอส่วนลด/ต่อราคา, ยกเลิกหรือแก้ไขการจองเดิม, ห้องประชุม, ร้องเรียน, หรือคำถามที่ตอบจากข้อมูลที่มีไม่ได้',
    input_schema: {
      type: 'object',
      properties: { reason: { type: 'string', description: 'สรุปสั้นๆ ว่าลูกค้าต้องการอะไร' } },
      required: ['reason'],
    },
  },
];

function bookingSystemPrompt(today, ctx) {
  const g = ctx.guest;
  const upcoming = (ctx.upcoming || []).map(b => `- ${b.booking_no} ห้อง ${b.room_id} ${b.check_in} ถึง ${b.check_out} (${b.room_total} บาท)`).join('\n');
  return `คุณคือ "น้องพบรัก" ผู้ช่วยรับจองห้องของ พบรักรีสอร์ท ทาง LINE พูดสุภาพ เป็นกันเอง ลงท้าย "ค่ะ" ตอบสั้น กระชับ เหมาะกับแชทมือถือ
ห้ามใช้ markdown (ห้ามใช้ ** หรือ # หรือตาราง) ใช้ข้อความธรรมดา ขึ้นบรรทัดใหม่ได้ ใช้อีโมจิได้เล็กน้อย

ข้อมูลโรงแรม (ใช้เท่านี้ ห้ามแต่งเพิ่ม)
- ที่อยู่: บ้านนิคม ต.โคกสูง อ.อุบลรัตน์ จ.ขอนแก่น 40250
- ห้องพัก 31 ห้อง 2 โซน: โซนตึก = สแตนดาร์ด (เตียงเดี่ยว 2 เตียง) 700 บาท/คืน และ ดีลักซ์ (เตียงคิงไซซ์) 800 บาท/คืน, โซนบ้าน = บ้านพัก (เตียงใหญ่ 1 เตียง) 400 บาท/คืน และ บ้านพัก (ใหญ่) (เตียงคู่ 2 เตียง พักได้ 3 คน) 500 บาท/คืน ราคารวม VAT แล้ว ไม่มีห้องรายเดือน
- เช็คอิน 14:00 เช็คเอาท์ 12:00 (ออกหลัง 14:00 คิดเพิ่ม 1 คืน)
- บริการ: อาหารเช้า, สระว่ายน้ำ, ที่จอดรถคันใหญ่ได้, WiFi
- มัดจำห้อง 300 บาท/ห้อง ชำระตอนเช็คอิน ได้คืนตอนเช็คเอาท์เมื่อห้องปกติ
- ไม่ต้องโอนมัดจำล่วงหน้า ชำระค่าห้องตอนเช็คอิน หรือโอนก่อนวันเข้าพักก็ได้
- ยกเลิกการจองได้ คืนเงินเต็มจำนวน / เช็คเอาท์ก่อนกำหนด จ่ายเฉพาะคืนที่พักจริง
- ออกใบกำกับภาษีได้ (แจ้งชื่อบริษัท/เลขผู้เสียภาษีตอนเช็คอิน)

ขั้นตอนรับจอง
1. ถามให้ได้: วันเข้าพัก วันออก จำนวนห้อง และโซน/ประเภทห้อง (ถ้าลูกค้าไม่ระบุประเภท ให้เสนอตัวเลือกพร้อมราคา)
2. เรียก check_availability ทุกครั้งก่อนบอกว่าห้องว่างหรือบอกราคา ห้ามเดา
3. ขอชื่อ-นามสกุล และเบอร์โทร (บริษัทถ้ามี) ห้ามขอเลขบัตรประชาชน
4. สรุปให้ลูกค้าดู: วันเข้า-ออก จำนวนคืน ประเภทและจำนวนห้อง ค่าห้องรวม (ราคา x คืน x ห้อง) มัดจำ 300 บาท/ห้องชำระตอนเช็คอิน แล้วถามว่า "ยืนยันการจองไหมคะ"
5. เมื่อลูกค้ายืนยันแล้วเท่านั้น จึงเรียก create_booking
6. แจ้งผล: เลขที่การจอง ห้องที่ได้ ค่าห้องรวม วิธีชำระ เวลาเช็คอิน 14:00

กติกาสำคัญ
- คิดเลขจากผลของเครื่องมือเท่านั้น ถ้า create_booking สำเร็จ ให้ใช้ตัวเลข room_total ที่ระบบคืนมา
- ถ้าห้องว่างไม่พอ เสนอประเภทอื่นหรือวันอื่นที่ว่าง
- จอง 5 ห้องขึ้นไป, ขอเครดิต/วางบิลบริษัท, ขอส่วนลด, ยกเลิก/แก้ไขการจองเดิม, ห้องประชุม, ร้องเรียน หรือเรื่องที่ไม่รู้ → เรียก handoff_to_staff แล้วบอกลูกค้าว่าพนักงานจะติดต่อกลับโดยเร็ว
- ถ้าเครื่องมือแจ้งข้อผิดพลาด ห้ามบอกว่าจองสำเร็จ

วันที่ (ใช้ตีความวันที่ลูกค้าพิมพ์ ปีลูกค้ามักพิมพ์เป็น พ.ศ.)
${calendar(today)}

ข้อมูลลูกค้าคนนี้ที่ระบบรู้
- ชื่อ LINE: ${ctx.thread?.display_name || '-'}
- ชื่อที่เคยให้: ${g?.full_name || '-'} / เบอร์: ${g?.phone || '-'} / บริษัท: ${g?.company || '-'} (ถ้ามี ให้ถามยืนยันว่าใช้ข้อมูลเดิมได้ไหม แทนการถามใหม่)
- การจองที่กำลังจะมาถึง:
${upcoming || '- ไม่มี'}`;
}

function toClaudeMessages(history) {
  const msgs = [];
  for (const m of history) {
    const role = m.sender === 'ลูกค้า' ? 'user' : 'assistant';
    const text = m.sender === 'พนักงาน' ? `[พนักงานตอบ] ${m.body}` : m.body;
    if (!text) continue;
    const last = msgs[msgs.length - 1];
    if (last && last.role === role) last.content += '\n' + text;
    else msgs.push({ role, content: text });
  }
  while (msgs.length && msgs[0].role !== 'user') msgs.shift();
  return msgs;
}

async function runTool(name, input, lineUserId, displayName) {
  try {
    if (name === 'check_availability') return await rpc('pp_availability', { p_check_in: input.check_in, p_check_out: input.check_out });
    if (name === 'create_booking') {
      return await rpc('pp_book', { p: { ...input, line_user_id: lineUserId, line_display_name: displayName, created_by: 'ai', channel: 'LINE OA' } });
    }
    if (name === 'handoff_to_staff') {
      await rpc('pp_handoff', { p_line_user_id: lineUserId, p_reason: input.reason });
      return { ok: true, message: 'ส่งเรื่องให้พนักงานแล้ว' };
    }
    return { error: 'ไม่รู้จักเครื่องมือนี้' };
  } catch (e) {
    return { error: e.message };
  }
}

// คืน { text, actions } — actions = รายการเครื่องมือที่ AI ใช้ (เก็บไว้ตรวจย้อนหลัง)
export async function bookingAgent(lineUserId, displayName) {
  const today = bangkokDate();
  const ctx = await rpc('pp_chat_context', { p_line_user_id: lineUserId, p_limit: 20 });
  const system = bookingSystemPrompt(today, ctx);
  const messages = toClaudeMessages(ctx.messages || []);
  const actions = [];
  for (let i = 0; i < 6; i++) {
    const r = await claude({ system, messages, tools: BOOKING_TOOLS });
    const uses = (r.content || []).filter(b => b.type === 'tool_use');
    if (r.stop_reason !== 'tool_use' || !uses.length) return { text: textOf(r) || 'ขออภัยค่ะ ระบบขัดข้อง พนักงานจะติดต่อกลับค่ะ', actions };
    messages.push({ role: 'assistant', content: r.content });
    const results = [];
    for (const u of uses) {
      const out = await runTool(u.name, u.input || {}, lineUserId, displayName);
      actions.push({ tool: u.name, input: u.input, ok: !out?.error, error: out?.error });
      results.push({ type: 'tool_result', tool_use_id: u.id, content: JSON.stringify(out), ...(out?.error ? { is_error: true } : {}) });
    }
    messages.push({ role: 'user', content: results });
  }
  return { text: 'ขออภัยค่ะ เรื่องนี้ขอให้พนักงานช่วยดูแลต่อนะคะ', actions };
}

// ---------- AI สรุปให้เจ้าของ ----------
export async function ownerSummary() {
  const data = await rpc('pp_summary_data', {});
  const system = `คุณคือผู้ช่วยเจ้าของโรงแรมพบรักรีสอร์ท (31 ห้อง) สรุปสถานการณ์จากข้อมูล JSON ที่ให้ เป็นภาษาไทยง่ายๆ
- ไม่เกิน 5 ข้อ แต่ละข้อขึ้นต้นด้วย "• " ยาวไม่เกิน 2 บรรทัด ห้ามใช้ markdown
- เรียงจากเรื่องที่ต้องทำก่อน: แชทที่ต้องให้พนักงานตอบ, แขกเข้าวันนี้ที่ยังไม่ชำระ, การจองใหม่, อัตราเข้าพัก 7 วันข้างหน้า (วันไหนว่างมาก = โอกาสขาย), สิ่งที่ลูกค้าถามบ่อยในแชท
- ตัวเลขต้องคัดลอกจากข้อมูลเท่านั้น ห้ามคำนวณใหม่หรือประมาณ ถ้าต้องการเปอร์เซ็นต์ให้บอกเป็น "x จาก 31 ห้อง" แทน
- ข้อมูลไหนไม่มี ไม่ต้องพูดถึง`;
  const r = await claude({ system, messages: [{ role: 'user', content: JSON.stringify(data) }] });
  return { text: textOf(r), data };
}
