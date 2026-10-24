import { requireUser } from '../lib/auth.js';
import { ownerSummary } from '../lib/ai.js';
import { json, errorJson } from '../lib/http.js';

export async function POST(request) {
  const a = await requireUser(request);
  if (a.response) return a.response;
  try {
    return json(await ownerSummary(), 200, a.cookies);
  } catch (e) { return errorJson(e); }
}
