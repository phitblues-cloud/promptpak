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
    return parts[0], ' '.join(parts[1:]) or '-'


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


def _normalize(b, today, m, credit_ids, by_no):
    """ปรับสถานะการจองให้ตรงกับวันนี้ (ข้อมูลต้นแบบอ้างอิง 24 ต.ค. 10:00)"""
    if b['booking_status'] in ('ยกเลิก', 'ไม่มาตามนัด'):
        return
    ci, co = _d(b['checkin_date']), _d(b['checkout_date'])
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


def build(base, export, now):
    """base = ชุดข้อมูลต้นแบบ, export = ผลจาก pp_export(), now = 'YYYY-MM-DDTHH:MM' (เวลาไทย)"""
    m = copy.deepcopy(base)
    today = _d(now)
    m['meta'] = dict(m['meta'], reference_datetime=now + ':00' + TZ)
    m['hotel'] = dict(m['hotel'], reference_datetime=now + ':00' + TZ)
    rooms = {r['room_id']: r for r in m['rooms']}
    rooms.update({old: rooms[new] for old, new in OLD2NEW.items() if new in rooms})   # ฐานข้อมูลยังไม่อัปเดตรหัสห้อง
    by_no = {b['booking_id']: b for b in m['bookings']}
    credit_ids = {c['company_id'] for c in m['companies'] if (c.get('credit_days') or 0) > 0}
    tmpl_g = m['guests'][0]
    tmpl_b = m['bookings'][0]
    guest_ids = {}       # uuid ในฐานข้อมูล -> guest_id ในชุดข้อมูล
    line_to_gid = {g['line_user_id']: g['guest_id'] for g in m['guests'] if g.get('line_user_id')}

    def guest_for(row):
        key = row.get('guest_id') or ('phone:' + (row.get('phone') or row['guest_name']))
        if key in guest_ids:
            return guest_ids[key]
        gr = next((g for g in export.get('guests', []) if g['id'] == row.get('guest_id')), None)
        if gr and gr.get('line_user_id') in line_to_gid:
            guest_ids[key] = line_to_gid[gr['line_user_id']]
            return guest_ids[key]
        gid = 'L%03d' % (len([g for g in m['guests'] if g['guest_id'].startswith('L')]) + 1)
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
                  'customer_type_at_ref': 'ลูกค้าใหม่', 'tags': ['จองผ่าน AI'], 'preferences_note': ''})
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
        m['bookings'].append(b)
        by_no[no] = b

    # การจองตัวอย่างที่ถูกลบออกจากฐานข้อมูล -> ไม่แสดง
    if export.get('bookings'):
        m['bookings'] = [b for b in m['bookings'] if b['booking_id'] in seen]

    for b in m['bookings']:
        _normalize(b, today, m, credit_ids, by_no)

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
            gid = 'L%03d' % (len([x for x in m['guests'] if x['guest_id'].startswith('L')]) + 1)
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
        m['line_chats'].append({'thread_id': 'T9%03d' % n, 'guest_id': gid, 'line_display_name': t.get('display_name') or '',
                                'line_user_id': t['line_user_id'],
                                'topic_tags': ['ส่งต่อพนักงาน'] if t.get('needs_staff') else ['AI ตอบ'],
                                'status': 'รอพนักงาน' if t.get('needs_staff') else 'ปิดแล้ว',
                                'unread_count': 1 if t.get('needs_staff') else 0,
                                'linked_booking_id': linked, 'last_message_at': msgs[-1]['at'], 'messages': msgs})
    return m
