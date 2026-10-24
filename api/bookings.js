import { requireUser } from '../lib/auth.js';
import { rpc } from '../lib/db.js';
import { json, errorJson } from '../lib/http.js';

const ISO = /^\d{4}-\d{2}-\d{2}$/;

export async function GET(request) {
  const a = await requireUser(request);
  if (a.response) return a.response;
  const u = new URL(request.url);
  const from = u.searchParams.get('from'), to = u.searchParams.get('to');
  if (!ISO.test(from || '') || !ISO.test(to || '')) return json({ error: 'ต้องระบุ from/to (YYYY-MM-DD)' }, 400);
  try {
    return json(await rpc('pp_bookings', { p_from: from, p_to: to }), 200, a.cookies);
  } catch (e) { return errorJson(e); }
}
