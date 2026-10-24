import { requireUser } from '../lib/auth.js';
import { rpc } from '../lib/db.js';
import { json, errorJson } from '../lib/http.js';

export async function GET(request) {
  const a = await requireUser(request);
  if (a.response) return a.response;
  const id = Number(new URL(request.url).searchParams.get('id'));
  try {
    const data = id ? await rpc('pp_chat_messages', { p_thread_id: id }) : await rpc('pp_chat_threads', {});
    return json(data, 200, a.cookies);
  } catch (e) { return errorJson(e); }
}

// พนักงานกด "จบเรื่อง" → AI กลับมาตอบแชทนี้ได้อีก
export async function POST(request) {
  const a = await requireUser(request);
  if (a.response) return a.response;
  const { id, action } = await request.json().catch(() => ({}));
  if (!id || action !== 'resolve') return json({ error: 'คำขอไม่ถูกต้อง' }, 400);
  try {
    await rpc('pp_chat_resolve', { p_thread_id: Number(id) });
    return json({ ok: true }, 200, a.cookies);
  } catch (e) { return errorJson(e); }
}
