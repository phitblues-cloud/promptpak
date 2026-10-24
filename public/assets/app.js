// ตัวช่วยร่วมทุกหน้า
const ICONS = {
  home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-5h4v5"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  chat: '<path d="M4 5h16v11H9l-5 4z"/>',
  out: '<path d="M15 12H4M8 8l-4 4 4 4"/><path d="M13 4h6v16h-6"/>',
  spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
  bed: '<path d="M3 18V8M3 14h18v4M21 14v-2a3 3 0 00-3-3h-7v5"/><circle cx="7" cy="11" r="1.6"/>',
  in: '<path d="M10 12h10M16 8l4 4-4 4"/><path d="M11 4H5v16h6"/>',
  moon: '<path d="M20 14A8 8 0 1110 4a6 6 0 0010 10z"/>',
  bag: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5h8v2"/>',
  gauge: '<path d="M4 18a8 8 0 1116 0"/><path d="M12 14l4-4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/>',
  left: '<path d="M15 5l-7 7 7 7"/>', right: '<path d="M9 5l7 7-7 7"/>',
  logo: '<path d="M4 6h16v11H10l-5 4z"/><path d="M7 14v-4M7 12h10v2M14 12v-1.5a1.5 1.5 0 013 0V12"/>',
};
export const icon = (n, cls = 'ic') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ''}</svg>`;

export function rail(active) {
  const items = [['/', 'home', 'หน้าแรก'], ['/bookings', 'cal', 'การจอง'], ['/chats', 'chat', 'แชท LINE']];
  const el = document.createElement('nav');
  el.className = 'rail';
  el.innerHTML = `<div class="mark" title="PROMPT PAK">${icon('logo')}</div>` +
    items.map(([h, i, t]) => `<a href="${h}" ${active === h ? 'aria-current="page"' : ''}>${icon(i)}<span>${t}</span>${h === '/chats' ? '<b class="bd hide" id="chatBadge"></b>' : ''}</a>`).join('') +
    `<div class="sp"></div><button id="logout">${icon('out')}<span>ออกจากระบบ</span></button>`;
  document.querySelector('.app').prepend(el);
  el.querySelector('#logout').onclick = async () => { await fetch('/api/logout', { method: 'POST' }); location.href = '/login'; };
}

export async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) } });
  if (res.status === 401) { location.href = '/login'; throw new Error('ต้องล็อกอิน'); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `ผิดพลาด (${res.status})`);
  return data;
}

export function setBadge(n) {
  const b = document.getElementById('chatBadge');
  if (!b) return;
  b.textContent = n; b.classList.toggle('hide', !n);
}

const DAY = ['อา.', 'จ.', 'อ.', 'พ.', 'พฤ.', 'ศ.', 'ส.'];
const DAYF = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์'];
const MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
const MONF = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'];
export const parse = iso => { const [y, m, d] = iso.slice(0, 10).split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); };
export const iso = dt => dt.toISOString().slice(0, 10);
export const addDays = (s, n) => { const d = parse(s); d.setUTCDate(d.getUTCDate() + n); return iso(d); };
export const dayDiff = (a, b) => Math.round((parse(b) - parse(a)) / 864e5);
export const th = s => { const d = parse(s); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}`; };
export const thLong = s => { const d = parse(s); return `${DAYF[d.getUTCDay()]} ${d.getUTCDate()} ${MONF[d.getUTCMonth()]} ${d.getUTCFullYear() + 543}`; };
export const parts = s => { const d = parse(s); return { dow: DAY[d.getUTCDay()], day: d.getUTCDate(), mon: MON[d.getUTCMonth()], monF: MONF[d.getUTCMonth()], wd: d.getUTCDay(), year: d.getUTCFullYear() + 543, dowF: DAYF[d.getUTCDay()] }; };
export const time = ts => new Date(ts).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
export const baht = n => (Number(n) || 0).toLocaleString('th-TH');
export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function payChip(p) {
  const cls = p === 'ชำระแล้ว' ? 'pay' : p === 'เครดิตบริษัท' ? 'cr' : p === 'คืนเงินแล้ว' ? '' : 'due';
  return `<span class="chip ${cls}">${esc(p)}</span>`;
}
export const aiChip = b => b.created_by === 'ai' ? `<span class="chip ai">${icon('spark')} AI จองให้</span>` : '';

export function toast(msg, ms = 4000) {
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg;
  document.body.append(t);
  setTimeout(() => { t.style.opacity = 0; setTimeout(() => t.remove(), 400); }, ms);
}

// เปิดแผงรายละเอียดการจอง
export function bookingDrawer(b) {
  const d = document.createElement('div');
  d.className = 'drawer';
  d.innerHTML = `<div class="pn" role="dialog" aria-label="รายละเอียดการจอง">
    <button class="btn sec" style="float:right" data-x>ปิด</button>
    <div class="muted">${esc(b.booking_no)}</div><h3>${esc(b.guest_name)}</h3>
    <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem">${aiChip(b)}${payChip(b.payment_status)}${b.status === 'ยกเลิก' ? '<span class="chip cx">ยกเลิก</span>' : ''}</div>
    <dl class="kv">
      <dt>ห้อง</dt><dd>${esc(b.room_id)}</dd>
      <dt>เข้าพัก</dt><dd>${thLong(b.check_in)}</dd>
      <dt>เช็คเอาท์</dt><dd>${thLong(b.check_out)}</dd>
      <dt>จำนวนคืน</dt><dd>${b.nights} คืน</dd>
      <dt>ราคา/คืน</dt><dd>${baht(b.rate)} บาท</dd>
      <dt>ค่าห้องรวม</dt><dd>${baht(b.room_total)} บาท</dd>
      <dt>มัดจำ</dt><dd>${baht(b.deposit)} บาท (ชำระตอนเช็คอิน)</dd>
      <dt>เบอร์โทร</dt><dd>${esc(b.phone || '-')}</dd>
      <dt>บริษัท</dt><dd>${esc(b.company || '-')}</dd>
      <dt>ช่องทาง</dt><dd>${esc(b.channel)}</dd>
      <dt>จองเมื่อ</dt><dd>${b.created_at ? time(b.created_at) : '-'}</dd>
      <dt>หมายเหตุ</dt><dd>${esc(b.note || '-')}</dd>
    </dl></div>`;
  d.addEventListener('click', e => { if (e.target === d || e.target.closest('[data-x]')) d.remove(); });
  document.body.append(d);
}
