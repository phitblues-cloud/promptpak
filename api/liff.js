// หน้าจอเด้งจองห้องใน LINE (LIFF) · GET ?ci&co = ตั้งค่า + ห้องว่าง · POST = จองจริง (ตรวจตัวตนด้วย ID token ของ LINE)
import { liffConfig, availability, liffBook, liffPrev, liffSlip } from '../lib/liff.js';
import { json } from '../lib/http.js';

const thai = e => ({ error: String(e?.message || e).replace(/^.*?ERROR:\s*/, '').slice(0, 300) });

export async function GET(request) {
  const u = new URL(request.url), ci = u.searchParams.get('ci'), co = u.searchParams.get('co');
  try { return json({ ...liffConfig(), ...(ci && co ? await availability(ci, co) : {}) }); }
  catch (e) { return json(thai(e), 400); }
}

export async function POST(request) {
  let body;
  try { body = await request.json(); } catch { return json({ error: 'ข้อมูลไม่ถูกต้อง' }, 400); }
  try { return json(body.action === 'prev' ? await liffPrev(body) : body.action === 'slip' ? await liffSlip(body) : await liffBook(body, new URL(request.url).origin)); }
  catch (e) { console.error('liff book', e); return json(thai(e), 400); }
}
