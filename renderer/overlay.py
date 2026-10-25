# -*- coding: utf-8 -*-
"""รวมข้อมูลจริงจากฐานข้อมูลเข้ากับชุดข้อมูลต้นแบบ ให้อยู่ในรูปแบบเดียวกับที่หน้าจอ v196 ใช้

- การจองตัวอย่าง (seed) ใช้รายละเอียดเดิมจากชุดข้อมูลต้นแบบ
- การจองใหม่ (AI / พนักงาน) สร้างระเบียนในรูปแบบเดียวกัน
- สถานะทุกการจองคำนวณใหม่จาก "วันนี้" จริง (รอเช็คอิน / กำลังพัก / เช็คเอาท์แล้ว)
- แชท LINE จริงต่อท้ายแชทตัวอย่าง
"""
import copy, datetime, re
from roomcodes import OLD2NEW

TZ = '+07:00'


def _d(s):
    return datetime.date.fromisoformat(s[:10])


def _iso(day, hhmm):
    return f'{day}T{hhmm}:00{TZ}'


def _bkk(ts):
    """timestamp จากฐานข้อมูล (UTC หรือมีเขตเวลา) -> 'YYYY-MM-DDTHH:MM:SS+07:00'"""
    if not ts:
        return None
    t = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    t = t.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
    return t.strftime('%Y-%m-%dT%H:%M:%S') + TZ


def _blank_like(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return 0
    if isinstance(v, str):
        return ''
    if isinstance(v, list):
        return []
    if isinstance(v, dict):
        return {k: _blank_like(x) for k, x in v.items()}
    return None


def _split_name(full):
    full = re.sub(r'^(คุณ|นาย|นางสาว|นาง|น\.ส\.)\s*', '', (full or '').strip())
    parts = full.split()
    if not parts:
        return 'ลูกค้า', 'LINE'
    return parts[0], ' '.join(parts[1:])


def _match_company(name, companies):
    if not name:
        return None
    n = name.strip().lower()
    for c in companies:
        if n and (n in c['name_th'].lower() or c['name_short'].lower() in n):
            return c['company_id']
    return None


def _pay_id(m):
    return 'PX%04d' % (len(m['payments']) + 1)


GOLIVE = datetime.date(2026, 10, 25)   # วันเริ่มใช้งานจริง: ข้อมูลตัวอย่างที่เข้าพักตั้งแต่วันนี้ต้องให้พนักงานกดเหมือนของจริง


def _normalize(b, today, m, credit_ids, by_no, cut=None):
    """ปรับสถานะการจองให้ตรงกับวันนี้ (ข้อมูลต้นแบบอ้างอิง 24 ต.ค. 10:00)"""
    if b['booking_status'] in ('ยกเลิก', 'ไม่มาตามนัด'):
        return
    ci, co = _d(b['checkin_date']), _d(b['checkout_date'])
    cut = cut or today
    inhouse_at_golive = not b.get('_real') and ci < GOLIVE <= co
    if b.get('_real') or ci >= GOLIVE or inhouse_at_golive:
        # การจองจริง: สถานะเปลี่ยนเฉพาะเมื่อพนักงานกด (ไม่เช็คอิน/เช็คเอาท์/รับเงินให้เอง)
        if b['booking_status'] == 'เช็คเอาท์แล้ว':
            return
        if inhouse_at_golive and not b.get('checkin_actual'):
            b['checkin_actual'] = _iso(b['checkin_date'], '14:30')   # เข้าพักก่อนวันเริ่มใช้งานจริง
        if b.get('checkin_actual'):
            b['booking_status'] = 'กำลังพัก'
            b['due_out_today'] = co <= today          # เลยวันเช็คเอาท์แล้วยังไม่กด -> ค้างในกล่องเช็คเอาท์
        elif ci < cut:
            b['booking_status'] = 'ยกเลิก'            # เลยวันเข้าพัก (ถึง 06:00 วันถัดไป) ไม่มาเช็คอิน -> ยกเลิก
            b['cancel_reason'] = 'ไม่มาตามนัด (ระบบยกเลิกอัตโนมัติเมื่อเลยวันเข้าพัก)'
            b['cancelled_at'] = b.get('cancelled_at') or _iso(b['checkin_date'], '23:59')
        elif ci <= today:                                 # วันนี้ หรือมาดึกหลังเที่ยงคืน (ก่อน 06:00)
            b['booking_status'] = 'รอเช็คอิน'
            paid = b['payment_status'] in ('ชำระแล้ว', 'รอชำระ') or b['payment_status'].startswith('เครดิต')
            b['checkin_split'] = 'รอเช็คอิน-ชำระแล้ว (ส่งคีย์การ์ดได้ทันที)' if paid else 'รอเช็คอิน-ยังไม่ชำระ (ชำระก่อนแล้วส่งคีย์การ์ด)'
            b['due_out_today'] = False
        else:
            b['booking_status'] = 'จองแล้ว'
            b['due_out_today'] = False
        return
    child = by_no.get(b.get('continued_by') or '')
    if child and child['booking_status'] not in ('ยกเลิก', 'ไม่มาตามนัด') and co < today <= _d(child['checkout_date']):
        b['booking_status'] = 'กำลังพัก'   # พักต่อในการจองถัดไป มัดจำยังถือไว้
        b['due_out_today'] = False
        return
    credit = b['billing_type'].startswith('เครดิต')
    is_credit = credit or b.get('company_id') in credit_ids and not b['billing_type'].startswith('จ่ายเอง')

    def ensure_checked_in():
        if not b.get('checkin_actual'):
            b['checkin_actual'] = _iso(b['checkin_date'], '14:30')
            b['keycard_given'] = True
        if b['deposit_status'].startswith('ยังไม่เก็บ'):
            b['deposit_status'] = 'ถือไว้'
            m['payments'].append({'payment_id': _pay_id(m), 'booking_id': b['booking_id'], 'guest_id': b['guest_id'],
                                  'paid_at': b['checkin_actual'], 'type': 'มัดจำห้อง (รับ)', 'amount': b['deposit'],
                                  'method': 'เงินสด', 'received_by': 'S03', 'note': 'บันทึกอัตโนมัติ'})
        if b['payment_status'] == 'ค้างชำระ' and not is_credit:
            b['payment_status'] = 'ชำระแล้ว'
            m['payments'].append({'payment_id': _pay_id(m), 'booking_id': b['booking_id'], 'guest_id': b['guest_id'],
                                  'paid_at': b['checkin_actual'], 'type': 'ค่าห้อง', 'amount': b['room_total'],
                                  'method': 'โอน PromptPay', 'received_by': 'S03', 'note': 'บันทึกอัตโนมัติ'})
        if b['payment_status'] == 'เครดิต-ยังไม่ถึงวันพัก':
            b['payment_status'] = 'รอชำระ'
        b['checkin_split'] = None

    if co < today:
        if b['booking_status'] != 'เช็คเอาท์แล้ว':
            ensure_checked_in()
            b['booking_status'] = 'เช็คเอาท์แล้ว'
            b['checkout_actual'] = b.get('checkout_actual') or _iso(b['checkout_date'], '10:30')
            if b['deposit_status'] == 'ถือไว้':
                b['deposit_status'] = 'คืนแล้ว'
                m['payments'].append({'payment_id': _pay_id(m), 'booking_id': b['booking_id'], 'guest_id': b['guest_id'],
                                      'paid_at': b['checkout_actual'], 'type': 'มัดจำห้อง (คืน)', 'amount': b['deposit'],
                                      'method': 'เงินสด', 'received_by': 'S03', 'note': 'บันทึกอัตโนมัติ'})
        b['due_out_today'] = False
    elif ci < today:
        if b['booking_status'] != 'กำลังพัก':
            ensure_checked_in()
            b['booking_status'] = 'กำลังพัก'
        b['due_out_today'] = (co == today)
    elif ci == today:
        if b['booking_status'] not in ('กำลังพัก', 'รอเช็คอิน'):
            b['booking_status'] = 'รอเช็คอิน'
            paid = b['payment_status'] == 'ชำระแล้ว' or is_credit
            b['checkin_split'] = 'รอเช็คอิน-ชำระแล้ว (ส่งคีย์การ์ดได้ทันที)' if paid else 'รอเช็คอิน-ยังไม่ชำระ (ชำระก่อนแล้วส่งคีย์การ์ด)'
        b['due_out_today'] = False
    else:
        if b['booking_status'] not in ('จองแล้ว',):
            b['booking_status'] = 'จองแล้ว'
        b['due_out_today'] = False


STAFF_ID = {'owner': 'S01', 'staff': 'S03'}
METHOD = {'cash': 'เงินสด', 'transfer': 'โอน PromptPay'}


def _new_gid(m):
    """รหัสลูกค้าใหม่ที่ไม่ซ้ำกับของเดิม"""
    have = {g['guest_id'] for g in m['guests']}
    n = 1
    while 'N%03d' % n in have:
        n += 1
    return 'N%03d' % n


def _apply_details(b, g, row, m):
    """รายละเอียดที่พนักงานกรอกตอนจอง (คน อาหารเช้า ส่วนลด บริษัท ใบกำกับภาษี เครดิต)"""
    d = row.get('details') or {}
    b['_staff'] = row.get('created_by') == 'staff'
    if b['_staff'] and not g.get('line_user_id'):
        g['line_display_name'] = ''
    if not d:
        return
    b['adults'] = int(d.get('adults') or d.get('pax') or 1)
    b['kids'] = int(d.get('kids') or 0)
    if d.get('purpose'):
        b['purpose'] = d['purpose']
    if d.get('email') and not g.get('email'):
        g['email'] = d['email']
    b['bf'], b['disc'], b['promo_code'] = int(d.get('bf') or 0), int(d.get('disc') or 0), d.get('code') or ''
    b['room_total'] = b['rate'] * b['nights'] + b['bf'] - b['disc']
    co = d.get('co')
    if co and co.get('name'):
        cid = _match_company(co['name'], m['companies'])
        if not cid:
            c = _blank_like(m['companies'][0])
            cid = 'CX%02d' % (len([x for x in m['companies'] if x['company_id'].startswith('CX')]) + 1)
            c.update({'company_id': cid, 'name_th': co['name'], 'name_short': co['name'], 'tax_id': co.get('tax') or '',
                      'billing_address': co.get('addr') or '', 'billing_branch': co.get('hq') or 'สำนักงานใหญ่',
                      'credit_days': int(d.get('cred_days') or 30)})
            m['companies'].append(c)
        b['company_id'] = g['company_id'] = cid
        pay = d.get('pay') or 'later'
        b['billing_type'] = ('เครดิตบริษัท' if pay == 'credit' else 'บริษัทโอนล่วงหน้า' if pay in ('now', 'dep')
                             else 'จ่ายเอง')
    if d.get('tax') or co:
        b['tax_invoice_requested'] = True


def apply_ops(m, ops, by_no, status_only=False):
    """การทำงานหน้าเคาน์เตอร์ที่บันทึกจริง (ตาราง ops) -> ข้อมูลการจอง/การเงินของหน้าจอ"""
    for o in ops:
        b = by_no.get(o.get('no') or '')
        if not b:
            continue
        k, d, at = o['kind'], o.get('data') or {}, _bkk(o['at'])
        if k == 'checkin':
            b['booking_status'] = 'กำลังพัก'
            b['checkin_actual'] = b.get('checkin_actual') or at
            b['keycard_given'] = True
            b['checkin_split'] = None
            b['due_out_today'] = False
        elif k == 'checkout':
            b['booking_status'] = 'เช็คเอาท์แล้ว'
            b['checkout_actual'] = at
            b['due_out_today'] = False
        elif k == 'cancel':
            b['booking_status'] = 'ยกเลิก'
            b['cancelled_at'] = at
            b['cancel_reason'] = d.get('why') or 'ยกเลิกที่เคาน์เตอร์'
        if status_only:
            continue

        def pay(typ, amt, method=None):
            m['payments'].append({'payment_id': 'PO%05d-%d' % (o['id'], len(m['payments'])), 'booking_id': b['booking_id'],
                                  'guest_id': b['guest_id'], 'paid_at': at, 'type': typ, 'amount': int(amt),
                                  'method': METHOD.get(method or d.get('m'), 'เงินสด'),
                                  'received_by': STAFF_ID.get(o.get('role'), 'S03'), 'note': 'บันทึกที่เคาน์เตอร์'})
        if k == 'pay':
            if d.get('room_amt'):
                pay('ค่าห้อง (มัดจำ 30%)' if d.get('partial') else 'ค่าห้อง', d['room_amt'])
                if not d.get('partial'):
                    b['payment_status'] = 'ชำระแล้ว'
                if b['booking_status'] == 'รอเช็คอิน':
                    b['checkin_split'] = 'รอเช็คอิน-ชำระแล้ว (ส่งคีย์การ์ดได้ทันที)'
            if d.get('ext_amt'):
                pay('ค่าห้อง (พักต่อ)', d['ext_amt'])
            if d.get('dep'):
                pay('มัดจำห้อง (รับ)', d['dep'])
                b['deposit_status'] = 'ถือไว้'
        elif k == 'dep_in':
            pay('มัดจำห้อง (รับ)', d.get('amt') or b['deposit'])
            b['deposit_status'] = 'ถือไว้'
        elif k == 'dep_out':
            back = int(d.get('amt', b['deposit']))
            pay('มัดจำห้อง (คืน)', -back)
            b['deposit_status'] = 'คืนแล้ว' + (f" (หัก {int(d['ded'])} บาท)" if d.get('ded') else '')
        elif k == 'checkout' and d.get('refund'):
            pay('ค่าห้อง (คืนเงิน เช็คเอาท์ก่อนกำหนด)', -int(d['refund']), 'cash')
        elif k == 'credit':
            b['billing_type'] = 'เครดิตบริษัท (ตั้งที่เคาน์เตอร์)'
            b['payment_status'] = 'รอชำระ'
            if b['booking_status'] == 'รอเช็คอิน':
                b['checkin_split'] = 'รอเช็คอิน-ชำระแล้ว (ส่งคีย์การ์ดได้ทันที)'
        elif k == 'cancel' and d.get('refund'):
            pay('คืนเงินยกเลิกการจอง', -int(d['refund']), 'transfer')
            b['payment_status'] = 'คืนเงินแล้ว'


def build(base, export, now):
    """base = ชุดข้อมูลต้นแบบ, export = ผลจาก pp_export(), now = 'YYYY-MM-DDTHH:MM' (เวลาไทย)"""
    m = copy.deepcopy(base)
    today = _d(now)
    cut = (datetime.datetime.fromisoformat(now) - datetime.timedelta(hours=6)).date()   # ไม่มาตามนัด: ตัดที่ 06:00 วันถัดไป
    m['meta'] = dict(m['meta'], reference_datetime=now + ':00' + TZ)
    m['hotel'] = dict(m['hotel'], reference_datetime=now + ':00' + TZ)
    if export.get('rooms'):   # ห้องจากฐานข้อมูล (ราคา/ประเภท/ห้องที่เพิ่มใหม่ ตามที่เจ้าของตั้ง)
        amen = {r['zone']: r.get('amenities', []) for r in m['rooms']}
        m['rooms'] = [{'room_id': x['id'], 'zone': x['zone'], 'building': x['zone'], 'floor': x.get('floor') or 1,
                       'room_type': x['room_type'], 'bed': x.get('bed') or '', 'rack_rate': x['rate'],
                       'max_guests': x['max_guests'], 'amenities': amen.get(x['zone'], [])}
                      for x in sorted(export['rooms'], key=lambda x: (x['zone'] != 'ตึกใหม่', x['id']))]
        m['hotel'] = dict(m['hotel'], rooms_total=len(m['rooms']))
    rooms = {r['room_id']: r for r in m['rooms']}
    rooms.update({old: rooms[new] for old, new in OLD2NEW.items() if new in rooms})   # ฐานข้อมูลยังไม่อัปเดตรหัสห้อง
    by_no = {b['booking_id']: b for b in m['bookings']}
    credit_ids = {c['company_id'] for c in m['companies'] if (c.get('credit_days') or 0) > 0}
    tmpl_g = m['guests'][0]
    tmpl_b = m['bookings'][0]
    guest_ids = {}       # uuid ในฐานข้อมูล -> guest_id ในชุดข้อมูล
    line_to_gid = {g['line_user_id']: g['guest_id'] for g in m['guests'] if g.get('line_user_id')}

    def guest_for(row):
        key = row.get('guest_id') or ('phone:%s|%s' % (row.get('phone') or '', row['guest_name']))
        if key in guest_ids:
            return guest_ids[key]
        gr = next((g for g in export.get('guests', []) if g['id'] == row.get('guest_id')), None)
        if gr and gr.get('line_user_id') in line_to_gid:
            guest_ids[key] = line_to_gid[gr['line_user_id']]
            return guest_ids[key]
        gid = _new_gid(m)
        first, last = _split_name(row['guest_name'])
        g = _blank_like(tmpl_g)
        g.update({'guest_id': gid, 'prefix': '', 'first_name': first, 'last_name': last,
                  'full_name': (first + ' ' + last).strip(), 'nickname': first, 'birth_date': '1990-01-01',
                  'birth_date_th': '', 'age': 0, 'id_card_no': '', 'id_card_is_mock': False,
                  'phone': row.get('phone') or '', 'email': '',
                  'line_display_name': (gr or {}).get('line_display_name') or first,
                  'line_user_id': (gr or {}).get('line_user_id') or '',
                  'company_id': _match_company(row.get('company'), m['companies']),
                  'segment': 'ลูกค้าใหม่', 'purpose_group': 'ทำงาน' if row.get('company') else 'แวะพัก',
                  'vehicle': None, 'is_member': False, 'bookings_total': 1, 'stays_completed_or_inhouse': 0,
                  'nights_stayed_to_ref': 0, 'upcoming_bookings': 1,
                  'first_stay': row['check_in'], 'last_stay': row['check_in'],
                  'customer_type_at_ref': 'ลูกค้าใหม่', 'tags': ['จองผ่าน AI'] if row.get('created_by') == 'ai' else [],
                  'preferences_note': ''})
        m['guests'].append(g)
        guest_ids[key] = gid
        if g['line_user_id']:
            line_to_gid[g['line_user_id']] = gid
        return gid

    seen = set()
    for row in export.get('bookings', []):
        no = row['booking_no']
        seen.add(no)
        if row['created_by'] == 'seed' and no in by_no:
            b = by_no[no]
            if row['status'] == 'ยกเลิก' and b['booking_status'] not in ('ยกเลิก', 'ไม่มาตามนัด'):
                b['booking_status'] = 'ยกเลิก'
                b['cancelled_at'] = _bkk(row.get('created_at'))
                b['cancel_reason'] = 'ยกเลิกในระบบ'
            if row['check_out'] != b['checkout_date']:   # พักต่อ / เช็คเอาท์ก่อนกำหนด
                b['checkout_date'] = row['check_out']
                b['nights'] = (_d(row['check_out']) - _d(b['checkin_date'])).days
                b['room_total'] = b['rate'] * b['nights']
            continue
        gid = guest_for(row)
        g = next(x for x in m['guests'] if x['guest_id'] == gid)
        r = rooms[row['room_id']]
        ci, co = _d(row['check_in']), _d(row['check_out'])
        booked = _bkk(row.get('created_at')) or (now + ':00' + TZ)
        b = _blank_like(tmpl_b)
        b.update({'booking_id': no, 'group_id': row.get('group_no'), 'parent_booking_id': None, 'extension_type': None,
                  'guest_id': gid, 'guest_name': g['full_name'], 'company_id': g['company_id'],
                  'room_id': r['room_id'], 'zone': r['zone'], 'room_type': r['room_type'],
                  'checkin_date': row['check_in'], 'checkout_date': row['check_out'], 'nights': (co - ci).days,
                  'weekday_nights': sum(1 for i in range((co - ci).days) if (ci + datetime.timedelta(days=i)).weekday() < 5),
                  'booked_at': booked, 'lead_days': max(0, (ci - _d(booked)).days),
                  'channel': row.get('channel') or 'LINE OA', 'purpose': 'ทำงาน' if g['company_id'] else 'แวะพัก',
                  'work_site': '', 'adults': 1, 'rack_rate': r['rack_rate'], 'rate': row['rate'],
                  'room_total': row['room_total'], 'deposit': row.get('deposit') or 300,
                  'billing_type': 'จ่ายเอง', 'tax_invoice_requested': False,
                  'note': ('จองผ่าน AI ทาง LINE' if row['created_by'] == 'ai' else '') + ((' · ' + row['note']) if row.get('note') else ''),
                  'special': None, 'continued_by': None, 'checkin_actual': None, 'checkout_actual': None,
                  'line_checkin_at': None, 'keycard_given': False,
                  'booking_status': 'ยกเลิก' if row['status'] == 'ยกเลิก' else 'จองแล้ว',
                  'payment_status': 'ชำระแล้ว' if row.get('payment_status') == 'ชำระแล้ว' else 'ค้างชำระ',
                  'deposit_status': 'ยังไม่เก็บ (เก็บตอนเช็คอิน)', 'due_out_today': False, 'checkin_split': None,
                  'cancel_reason': 'ยกเลิกในระบบ' if row['status'] == 'ยกเลิก' else None,
                  'cancelled_at': booked if row['status'] == 'ยกเลิก' else None})
        b['_real'] = True   # การจองจริง (LINE / พนักงาน) ไม่ใช้กฎอัตโนมัติของข้อมูลตัวอย่าง
        _apply_details(b, g, row, m)
        m['bookings'].append(b)
        by_no[no] = b

    # การจองตัวอย่างที่ถูกลบออกจากฐานข้อมูล -> ไม่แสดง
    if export.get('bookings'):
        m['bookings'] = [b for b in m['bookings'] if b['booking_id'] in seen]

    ops = export.get('ops', [])
    apply_ops(m, ops, by_no)
    for b in m['bookings']:
        _normalize(b, today, m, credit_ids, by_no, cut)
    apply_ops(m, ops, by_no, status_only=True)   # สถานะที่พนักงานกดจริง ชนะสถานะที่คำนวณจากวันที่
    closed = set(export.get('closed_rooms', []))
    for r in m['rooms']:
        r['closed'] = r['room_id'] in closed

    # สถานะห้องสำหรับแม่บ้าน ณ วันนี้
    hk = []
    for r in m['rooms']:
        mine = [b for b in m['bookings'] if b['room_id'] == r['room_id'] and b['booking_status'] not in ('ยกเลิก', 'ไม่มาตามนัด')]
        dep = next((b for b in mine if _d(b['checkin_date']) < today == _d(b['checkout_date'])), None)
        stay = next((b for b in mine if _d(b['checkin_date']) < today < _d(b['checkout_date'])), None)
        arr = next((b for b in mine if _d(b['checkin_date']) == today), None)
        st, b = (('มีแขก – เช็คเอาท์วันนี้', dep) if dep else ('มีแขกพัก', stay) if stay else
                 ('เตรียมรับแขกวันนี้', arr) if arr else ('ว่าง สะอาด พร้อมขาย', None))
        hk.append({'room_id': r['room_id'], 'zone': r['zone'], 'status_at_ref': st,
                   'guest_id': b['guest_id'] if b else None, 'assigned_to': 'S03' if r['zone'] == 'ตึกใหม่' else 'S04'})
    m['housekeeping_at_ref'] = hk

    # อัตราเข้าพักรายวัน (ใช้ในรายงาน) คำนวณใหม่จากการจองจริง
    act = [b for b in m['bookings'] if b['booking_status'] not in ('ยกเลิก', 'ไม่มาตามนัด')]
    for d in m['daily_occupancy']:
        day = _d(d['date'])
        on = [b for b in act if _d(b['checkin_date']) <= day < _d(b['checkout_date'])]
        d['rooms_sold'] = len(on)
        d['occupancy_pct'] = round(len(on) / len(m['rooms']) * 100, 1)
        d['room_revenue'] = sum(b['rate'] for b in on)
        bc = {k: 0 for k in d.get('by_company', {})}
        gen = 0
        for b in on:
            if b.get('company_id') in bc:
                bc[b['company_id']] += 1
            else:
                gen += 1
        d['by_company'] = bc
        d['general'] = gen

    # แชท LINE จริง
    n = len(m['line_chats'])
    for t in export.get('threads', []):
        if t.get('is_seed') or not t.get('messages'):
            continue
        n += 1
        gid = line_to_gid.get(t['line_user_id'])
        if not gid:
            first = (t.get('display_name') or 'ลูกค้า LINE')
            g = _blank_like(tmpl_g)
            gid = _new_gid(m)
            g.update({'guest_id': gid, 'first_name': first, 'last_name': '', 'full_name': first, 'nickname': first,
                      'birth_date': '1990-01-01', 'line_display_name': first, 'line_user_id': t['line_user_id'],
                      'company_id': None, 'vehicle': None, 'is_member': False, 'tags': [], 'segment': 'ลูกค้าใหม่',
                      'customer_type_at_ref': 'ลูกค้าใหม่', 'first_stay': None, 'last_stay': None})
            m['guests'].append(g)
            line_to_gid[t['line_user_id']] = gid
        linked = None
        mine = [b for b in m['bookings'] if b['guest_id'] == gid and b['booking_status'] not in ('ยกเลิก', 'ไม่มาตามนัด')]
        if mine:
            linked = sorted(mine, key=lambda b: b['checkin_date'])[-1]['booking_id']
        msgs = []
        for i, x in enumerate(t['messages'], 1):
            who = {'ลูกค้า': 'ลูกค้า', 'พนักงาน': 'พนักงาน', 'AI': 'ระบบอัตโนมัติ', 'ระบบ': 'ระบบอัตโนมัติ'}[x['sender']]
            body = x['body']
            if x['sender'] == 'AI':
                body = '✨ ' + body
            msgs.append({'seq': i, 'from': who, 'at': _bkk(x['at']), 'text': body, 'type': 'text'})
        m['line_chats'].append({'thread_id': 'T9%03d' % n, 'db_key': 'db:%s' % t['id'], 'guest_id': gid, 'line_display_name': t.get('display_name') or '',
                                'line_user_id': t['line_user_id'],
                                'topic_tags': ['ส่งต่อพนักงาน'] if t.get('needs_staff') else ['AI ตอบ'],
                                'status': 'รอพนักงาน' if t.get('needs_staff') else 'ปิดแล้ว',
                                'unread_count': 1 if t.get('needs_staff') else 0,
                                'linked_booking_id': linked, 'last_message_at': msgs[-1]['at'], 'messages': msgs})
    # สถานะแชทที่พนักงานตั้ง (ชื่อแชท/หมายเหตุ/ปิดเคส/อ่านแล้ว/ข้อความในแชทตัวอย่าง) เวลาแปลงเป็นเวลาไทย
    cs = {}
    for k, v in (export.get('chat_state') or {}).items():
        cs[k] = dict(v, closed_at=_bkk(v.get('closed_at')), read_at=_bkk(v.get('read_at')),
                     sent=[dict(x, at=_bkk(x['at'])) for x in (v.get('sent') or [])])
    m['chat_state'] = cs
    m['cust_state'] = export.get('cust_state') or {}
    # สมัครสมาชิกจากโมดูลลูกค้า → ทุกโมดูลเห็นว่าเป็นสมาชิก (ป้ายในการ์ดหน้าแรก/ป๊อปอัปการจอง/แชท)
    gby = {g['guest_id']: g for g in m['guests']}
    mem_ids = {x['guest_id'] for x in m['members']}
    done_st = ('เช็คเอาท์แล้ว', 'ยกเลิก', 'ไม่มาตามนัด')
    for gid, d in m['cust_state'].items():
        g = gby.get(gid)
        # แก้ชื่อ/เบอร์/LINE ในโมดูลลูกค้า: การจองที่จบแล้วเก็บข้อมูลเดิมไว้เป็นประวัติ · การจองที่ยังดำเนินอยู่ใช้ข้อมูลปัจจุบัน
        if g and any(d.get(k) for k in ('name', 'phone', 'line')):
            old = {'name': 'คุณ' + g['first_name'] + (' ' + g['last_name'] if g['last_name'] else ''), 'phone': g['phone']}
            for b in m['bookings']:
                if b['guest_id'] == gid and '_snap' not in b and (b['booking_status'] in done_st or b['checkout_date'] < today.isoformat()):
                    b['_snap'] = old
            if d.get('name'):
                nm = re.sub(r'^คุณ\s*', '', d['name']).strip()
                first, _, last = nm.partition(' ')
                g['first_name'], g['last_name'] = first, last.strip()
                g['full_name'] = nm
            if d.get('phone'):
                g['phone'] = d['phone']
            if d.get('line'):
                g['line_display_name'] = d['line']
        if g and d.get('memberNo'):
            g['is_member'] = True
            if gid not in mem_ids:
                m['members'].append({'member_id': d['memberNo'], 'guest_id': gid, 'line_user_id': g.get('line_user_id'),
                                     'line_display_name': g.get('line_display_name'), 'joined_at': (d.get('memberSince') or now[:10]) + 'T12:00:00' + TZ,
                                     'join_channel': 'สมัครที่เคาน์เตอร์', 'member_level': 'สมาชิก', 'consent_marketing': False,
                                     'birthday_greeting': False, 'rich_menu': 'เมนูสมาชิก'})
                mem_ids.add(gid)
    # บริษัทที่พนักงานเพิ่มใหม่/แก้ไข (แท็บบริษัท)
    if export.get('comp_state') and m['companies']:
        tmpl = m['companies'][0]
        byc = {c['company_id']: c for c in m['companies']}
        for cid, d in sorted(export['comp_state'].items()):
            c = byc.get(cid)
            if not c:
                if not d.get('name'):
                    continue
                c = {k: _blank_like(v) for k, v in tmpl.items()}
                c.update({'company_id': cid, 'account_stage': 'ลูกค้าใหม่', 'credit_days': 0, 'billing_branch': 'สำนักงานใหญ่'})
                m['companies'].append(c)
                byc[cid] = c
            if d.get('name'):
                c['name_th'] = d['name']
                short = re.sub(r'^(บริษัท|บจก\.|หจก\.|บมจ\.)\s*', '', d['name'])
                c['name_short'] = re.sub(r'\s*(จำกัด|\(มหาชน\))\s*', ' ', short).strip() or d['name']
            for k, f in (('short', 'name_short'), ('type', 'company_type'), ('site', 'work_site'), ('tax', 'tax_id'),
                         ('branch', 'billing_branch'), ('addr', 'billing_address'), ('pay', 'pay_mode'),
                         ('cname', 'contact_name'), ('crole', 'contact_role'), ('cphone', 'contact_phone'),
                         ('cemail', 'contact_email'), ('cline', 'contact_line'), ('cdecide', 'contact_decide')):
                if d.get(k) not in (None, ''):
                    c[f] = d[k]
            if d.get('pay'):
                c['credit_days'] = int(d.get('credit') or 0) if d['pay'] == 'credit' else 0
                c['billing_mode'] = {'self': 'ผู้เข้าพักจ่ายเอง', 'prepay': 'บริษัทโอนค่าห้องล่วงหน้า',
                                     'credit': 'วางบิลเครดิต %d วัน' % c['credit_days']}[d['pay']]
    m['cust_ids'] = export.get('cust_ids') or {}
    return m
