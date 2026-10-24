import { logoutCookies } from '../lib/auth.js';
import { json } from '../lib/http.js';

export function POST() {
  return json({ ok: true }, 200, logoutCookies());
}
