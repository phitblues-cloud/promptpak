import { requireUser } from '../lib/auth.js';
import { rpc } from '../lib/db.js';
import { json, errorJson } from '../lib/http.js';

export async function GET(request) {
  const a = await requireUser(request);
  if (a.response) return a.response;
  try {
    return json({ ...(await rpc('pp_dashboard', {})), user: a.user?.email }, 200, a.cookies);
  } catch (e) { return errorJson(e); }
}
