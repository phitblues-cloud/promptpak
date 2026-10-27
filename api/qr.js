// รูป QR พร้อมเพย์ของการจอง (การ์ดใน LINE ดึงรูปจากลิงก์นี้) · ?no=เลขจอง
import { rpc } from '../lib/db.js';
import { qrPng, promptpay } from '../lib/qr.js';
import { PROMPTPAY } from '../lib/liff.js';

export async function GET(request) {
  const no = new URL(request.url).searchParams.get('no') || '';
  if (!/^BK[0-9A-Z-]{4,20}$/.test(no)) return new Response('bad', { status: 400 });
  try {
    const d = await rpc('pp_liff_due', { p_no: no });
    if (!d || !d.total) return new Response('not found', { status: 404 });
    return new Response(qrPng(promptpay(PROMPTPAY(), d.total), 10, 4), { headers: { 'Content-Type': 'image/png', 'Cache-Control': 'public, max-age=3600' } });
  } catch (e) { return new Response('error', { status: 500 }); }
}
