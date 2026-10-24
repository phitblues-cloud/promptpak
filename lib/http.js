// ตัวช่วยตอบกลับ JSON + คุกกี้
export function json(data, status = 200, cookies = []) {
  const h = new Headers({ 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  for (const c of cookies) h.append('Set-Cookie', c);
  return new Response(JSON.stringify(data), { status, headers: h });
}

export function getCookie(request, name) {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const i = part.indexOf('=');
    if (i > 0 && part.slice(0, i).trim() === name) return decodeURIComponent(part.slice(i + 1).trim());
  }
  return null;
}

export function cookie(name, value, maxAge) {
  const secure = process.env.LOCAL_DEV ? '' : '; Secure';
  return `${name}=${encodeURIComponent(value)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

export function errorJson(e, status = 500) {
  console.error(e);
  return json({ error: e?.message || String(e) }, status);
}

// วันที่ไทย (เขตเวลา Asia/Bangkok) รูปแบบ YYYY-MM-DD
export function bangkokDate(d = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok' }).format(d);
}
