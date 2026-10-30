# -*- coding: utf-8 -*-
"""แปลง POBRAK_MOCK -> โครงสร้างที่แต่ละโมดูลใช้ (วัน = จำนวนวันจาก epoch, เวลา = ms แบบ UTC-as-local)"""
import json, datetime, calendar, re, os
HERE = os.path.dirname(os.path.abspath(__file__))
import ctx
m = ctx.MOCK if ctx.MOCK is not None else json.load(open(os.path.join(HERE, 'base_mock.json'), encoding='utf-8'))
EPOCH = datetime.date(1970, 1, 1)
REF = ctx.NOW[:10]                      # วันนี้ (เวลาไทย)
REF_H, REF_M = int(ctx.NOW[11:13]), int(ctx.NOW[14:16])

def dno(s):
    y, mo, d = map(int, s[:10].split('-'))
    return (datetime.date(y, mo, d) - EPOCH).days

def msl(s):
    """ISO 'YYYY-MM-DDTHH:MM:SS(+07:00)' -> ms โดยใช้ตัวเลขนาฬิกาตามที่เขียน"""
    d = s[:10]
    t = s[11:19] if len(s) >= 19 else '00:00:00'
    y, mo, dd = map(int, d.split('-'))
    hh, mi, ss = map(int, t.split(':'))
    return calendar.timegm((y, mo, dd, hh, mi, ss)) * 1000

def hm(s):
    return s[11:16]

D0 = dno(REF)
REFMS = calendar.timegm((*map(int, REF.split('-')), REF_H, REF_M, 0)) * 1000

def clean_addr(a):
    return re.sub(r'\s*\((ตรวจสอบ|ที่อยู่โรงงาน)[^)]*\)', '', a or '').strip()

# ---------------- ห้อง ----------------
ROOMS = []
for r in m['rooms']:
    ROOMS.append({'code': r['room_id'], 'zone': 'B' if r['zone'] == 'บ้านหลัง' else 'A',   # A = โซนตึกใหม่, B = โซนบ้านหลัง (คีย์ภายในของต้นแบบ)
                   'type': r['room_type'], 'rate': r['rack_rate'],
                  'max': r['max_guests'], 'open': not r.get('closed'), 'ota': not r.get('closed'), 'bed': r['bed'], 'floor': r['floor']})
ROOMBY = {r['code']: r for r in ROOMS}

# ---------------- พนักงาน ----------------
STAFF = {s['staff_id']: s for s in m['staff']}
SN = {'S01': 'เจ้าของ', 'S02': 'ป้าใจ', 'S03': 'ดวน', 'S04': 'ใบ'}

# ---------------- ลูกค้า / บริษัท ----------------
G = {g['guest_id']: g for g in m['guests']}
# ห้องแชทกลุ่ม LINE ไม่ใช่ลูกค้า: ให้หน้าแชทหาเจอ (G) แต่ไม่นับในรายชื่อ/สถิติลูกค้า
m['guests'] = [g for g in m['guests'] if not g.get('is_group_chat')]
CO = {c['company_id']: c for c in m['companies']}
def disp(g):
    return 'คุณ' + g['first_name'] + ' ' + g['last_name']
def gname(gid):
    return disp(G[gid])
MEM = {x['guest_id']: x for x in m['members']}
CONT = {}
for c in m['company_contacts']:
    CONT.setdefault(c['company_id'], []).append(c)

def co_contact(cid):
    for c in CONT.get(cid, []):
        if c['guest_id']:
            return G[c['guest_id']]
    return None

# ---------------- การจอง ----------------
PAY = {}
for p in m['payments']:
    PAY.setdefault(p['booking_id'], []).append(p)
INV = {}
for t in m['tax_invoices']:
    for b in t['booking_ids']:
        INV.setdefault(b, []).append(t)

def mth(p):
    x = p['method']
    return 'cash' if x.startswith('เงินสด') else 'transfer'

def stage_of(b):
    st = b['booking_status']
    ci, co = dno(b['checkin_date']), dno(b['checkout_date'])
    if st in ('ยกเลิก', 'ไม่มาตามนัด'):
        return None
    if st == 'กำลังพัก' and co <= D0:
        return 'out'          # ถึง/เลยวันเช็คเอาท์ แต่ยังไม่กดเช็คเอาท์ -> ค้างในกล่องเช็คเอาท์
    if co < D0 or st == 'เช็คเอาท์แล้ว':
        return 'outdone'
    if st == 'กำลังพัก':
        return 'out' if (b.get('due_out_today') or co == D0) else 'stay'
    if st == 'รอเช็คอิน':
        return 'key' if 'ส่งคีย์การ์ดได้ทันที' in (b.get('checkin_split') or '') else 'arrive'
    return 'arrive'

def dep_of(b):
    s = b['deposit_status']
    if b['booking_status'] in ('ยกเลิก', 'ไม่มาตามนัด'):
        return 'none'
    if s.startswith('ไม่ได้เก็บ'):
        return 'none'
    if s.startswith('คืน'):
        return 'refunded'
    if s.startswith('ถือ') or s.startswith('ใช้มัดจำ'):
        return 'held'
    return 'unpaid'

def billing_kind(b):
    t = b['billing_type']
    if t.startswith('จ่ายเอง'):
        return 'self'
    if t.startswith('บริษัทโอนล่วงหน้า'):
        return 'now'
    return 'credit'

def credit_days(b):
    cid = b['company_id']
    return CO[cid]['credit_days'] if cid in CO else 30

BK = []   # การจองที่ใช้งาน (ไม่ยกเลิก)
BC = []   # ยกเลิก / ไม่มาตามนัด
for i, b in enumerate(sorted(m['bookings'], key=lambda x: x['booking_id'])):
    g = G[b['guest_id']]
    cid = b['company_id']
    kind = billing_kind(b)
    ci, co = dno(b['checkin_date']), dno(b['checkout_date'])
    st = stage_of(b)
    roomp = [p for p in PAY.get(b['booking_id'], []) if p['type'].startswith('ค่าห้อง')]
    paid = b['payment_status'] == 'ชำระแล้ว'
    o = {
        'id': 'b' + b['booking_id'][4:],
        'no': b['booking_id'], 'group': b['group_id'], 'room': b['room_id'],
        'start': ci, 'nights': b['nights'], 'end': co,
        'gid': b['guest_id'], 'guest': (b.get('_snap') or {}).get('name') or disp(g), 'phone': (b.get('_snap') or {}).get('phone') or g['phone'], 'email': g['email'],
        'line': g['line_display_name'], 'lineOn': not b.get('_staff'),
        'bf': b.get('bf', 0), 'disc': b.get('disc', 0), 'promo': b.get('promo_code', ''),
        'mem': bool(g['is_member']), 'visits': g['stays_completed_or_inhouse'] or g['bookings_total'] or 1,
        'cid': cid, 'cname': CO[cid]['name_th'] if cid in CO else '', 'cshort': CO[cid]['name_short'] if cid in CO else '',
        'grp': 'ลูกค้าบริษัท' if cid in CO else 'ลูกค้าทั่วไป',
        'rate': b['rate'], 'total': b['room_total'], 'dep': dep_of(b), 'deposit': b['deposit'],
        'paid': paid, 'payM': (mth(roomp[0]) if (paid and roomp) else None),
        'ch': b['channel'], 'adults': b['adults'], 'kids': b.get('kids', 0), 'pax': b['adults'] + b.get('kids', 0),
        'madeAt': msl(b['booked_at']), 'lead': b['lead_days'], 'hm': hm(b['booked_at']),
        'note': b.get('note') or '', 'purpose': b['purpose'], 'worksite': b.get('work_site') or '',
        'bill': b['billing_type'], 'kind': kind, 'taxReq': bool(b['tax_invoice_requested']),
        'status': b['booking_status'], 'pstatus': b['payment_status'],
        'stage': st, 'viaLine': bool(b.get('line_checkin_at')), 'ci': bool(b.get('checkin_actual')),
        'ciAt': msl(b['checkin_actual']) if b.get('checkin_actual') else None,
        'coAt': msl(b['checkout_actual']) if b.get('checkout_actual') else None,
        'parent': b.get('parent_booking_id'), 'ext': b.get('extension_type'), 'cont': b.get('continued_by'),
        'dueToday': bool(b.get('due_out_today')),
        'special': b.get('special'), 'cancelAt': msl(b['cancelled_at']) if b.get('cancelled_at') else None,
        'cancelWhy': b.get('cancel_reason') or '', 'split': b.get('checkin_split') or '',
    }
    # ที่อยู่/ภาษี
    if b['tax_invoice_requested']:
        invs = INV.get(b['booking_id'], [])
        if cid in CO:
            c = CO[cid]
            o['tax'] = {'type': 'บริษัท / นิติบุคคล', 'name': c['name_th'], 'id': c['tax_id'], 'addr': clean_addr(c['billing_address']),
                        'hq': c['billing_branch'], 'branch': ''}
        else:
            ti = next((t for t in invs), None)
            o['tax'] = {'type': 'บุคคลธรรมดา', 'name': disp(g), 'id': (ti or {}).get('tax_id', ''), 'addr': clean_addr((ti or {}).get('address', g['address'])), 'hq': '', 'branch': ''}
    else:
        o['tax'] = None
    if st is None:
        o['cancelled'] = (b['booking_status'] == 'ยกเลิก')
        o['noshow'] = (b['booking_status'] == 'ไม่มาตามนัด')
        BC.append(o)
    else:
        BK.append(o)
BKBY = {b['no']: b for b in BK + BC}

def company_obj(b):
    """โครง co ของโมดูลจอง สำหรับการจองที่บริษัทเป็นผู้จ่าย (โอนล่วงหน้า / เครดิต)"""
    if b['kind'] == 'self' or b['cid'] not in CO:
        return None
    c = CO[b['cid']]
    ct = co_contact(b['cid'])
    return {'name': c['name_th'], 'tax': c['tax_id'], 'addr': clean_addr(c['billing_address']), 'hq': c['billing_branch'],
            'contact': {'name': disp(ct) if ct else '', 'phone': ct['phone'] if ct else '', 'email': ct['email'] if ct else ''},
            'payer': 'room', 'terms': 'now' if b['kind'] == 'now' else 'credit',
            'credDays': c['credit_days'] or 30, 'po': ''}

def fmt_date_th(s):
    d = datetime.date(*map(int, s[:10].split('-')))
    mo = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'][d.month - 1]
    return f'{d.day} {mo} {d.year + 543}'

if __name__ == '__main__':
    import collections
    print(len(BK), len(BC), D0)
    print(collections.Counter(b['stage'] for b in BK))
    print([b['no'] + ':' + b['room'] for b in BK if b['start'] <= D0 and b['stage'] != 'outdone'])

# ---------------- รีวิว (ข้อมูล Google ในไฟล์ต้นฉบับมีช่องวันที่/ชื่อผู้รีวิวสลับกัน จึงแก้ไขที่นี่) ----------------
REVIEWS = []
_gi = 0
for r in m['reviews']:
    ca = r['created_at']
    if re.match(r'^\d{4}-\d\d-\d\d', ca or ''):
        d = ca[:10]; nm = r['reviewer_name']
    else:
        # รูปแบบ "<ชื่อ>T12:00:00+07:00" ไม่มีวันที่ -> ไล่วันย้อนหลังจากวันอ้างอิง (17-23 ต.ค.)
        nm = ca.split('T12:00')[0] if 'T12:00' in ca else ''
        d = (datetime.date(2026, 10, 17) + datetime.timedelta(days=_gi % 7)).isoformat(); _gi += 1
    REVIEWS.append(dict(r, created_at=d + 'T12:00:00+07:00', reviewer_name=nm if isinstance(nm, str) else ''))
