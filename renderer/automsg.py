# -*- coding: utf-8 -*-
"""ข้อความอัตโนมัติหาลูกค้าทาง LINE (การ์ดตามภาพร่าง docs/mockups/liff/auto_msg_v2.png · ต้องรัน 22_automsg.sql)
  arrive  เช้าวันเข้าพัก 10:00  (ห้องพร้อม → "เช็คอินได้เลย" · ยังไม่พร้อม → "เช็คอินได้ตั้งแต่ 14:00")
  welcome ทันทีหลังพนักงานกดเช็คอิน (มอบคีย์การ์ด): ไวไฟ อาหารเช้า เวลาเช็คเอาท์
  remind  คืนสุดท้าย 19:00 (เฉพาะพักหลายคืน)
  rate    ทันทีหลังพนักงานกดเช็คเอาท์: ขอบคุณ + ปุ่มให้คะแนน 1-5 (ตอบรับคะแนนอยู่ที่ api/line-webhook.js)
กติกา: สวิตช์หลักปิดอยู่เป็นค่าเริ่มต้น · ช่องข้อมูลโรงแรมที่ว่าง = ข้ามข้อความที่ต้องใช้ · 1 เหตุการณ์ต่อ 1 การจองส่งครั้งเดียว
ทุกฟังก์ชันที่ถูกเรียกจากปุ่มของพนักงานห้ามทำให้ปุ่มพัง (ครอบ try ไว้ที่ on_act)"""
import json, os, re, time
from db import rpc, DbError

MENU_ID = {'arrive': 'pre', 'welcome': 'stay', 'remind': 'stay', 'rate': 'thanks'}   # ข้อความในเมนู CRM ที่เป็นสวิตช์ "ใช้งาน"
MENU_DEFAULT = {'pre': 'on', 'stay': 'on', 'thanks': 'on'}                              # ยังไม่เคยบันทึกเมนูนี้ = เปิด
LABEL = {'arrive': 'เช้าวันเข้าพัก', 'welcome': 'ต้อนรับหลังมอบคีย์การ์ด', 'remind': 'เตือนเช็คเอาท์คืนสุดท้าย', 'rate': 'ขอบคุณ + ให้คะแนน'}

ORCHID = ('#4B2477', '#C04C9C')
GREEN = ('#1F7A50', '#2E9C6A')
BLUE = ('#1C3F7A', '#3A6FB5')
INK, SOFT, LINK = '#2B1B3A', '#7D7090', '#7B3A9E'


def _env(k):
    return (os.environ.get(k) or '').strip()


def settings():
    c = rpc('pp_am_cfg') or {}
    return {
        'on': bool(c.get('on')),
        'wifi_name': (c.get('wifi_name') or '').strip(), 'wifi_pass': (c.get('wifi_pass') or '').strip(),
        'breakfast': (c.get('breakfast') or '').strip() or _env('HOTEL_BREAKFAST'),
        'checkin_time': (c.get('checkin_time') or '').strip() or '14:00',
        'checkout_time': (c.get('checkout_time') or '').strip() or '12:00',
        'phone': (c.get('phone') or '').strip() or _env('HOTEL_PHONE'),
        'map': (c.get('map') or '').strip() or _env('HOTEL_MAP_URL'),
        'review_url': (c.get('review_url') or '').strip(),
        'test_to': (c.get('test_to') or '').strip(),
    }


def menu_state(kind, mod_state=None):
    """สถานะของข้อความนี้ในเมนู CRM (on/off/draft/wait) · ยังไม่เคยบันทึกเมนู = ค่าเริ่มต้น"""
    mid = MENU_ID[kind]
    try:
        st = mod_state if mod_state is not None else (rpc('pp_mod_state') or {})
    except DbError:
        st = {}
    ms = (st.get('crmtool') or {}).get('ms')
    if isinstance(ms, list):
        m = next((x for x in ms if isinstance(x, dict) and x.get('id') == mid), None)
        if m is not None:
            return m.get('st') or 'off'
    return MENU_DEFAULT[mid]


def _first(name):
    n = re.sub(r'^(นางสาว|นาย|นาง|น\.ส\.|ด\.ช\.|ด\.ญ\.|คุณ)\s*', '', (name or '').strip())
    return (n.split() or [''])[0] or 'ลูกค้า'


def _digits(s):
    return re.sub(r'[^0-9+]', '', s or '')


# ---------- การ์ด Flex ----------
def _header(title, grad, sub='พบรักรีสอร์ท'):
    return {'type': 'box', 'layout': 'vertical', 'paddingAll': '16px',
            'background': {'type': 'linearGradient', 'angle': '125deg', 'startColor': grad[0], 'endColor': grad[1]},
            'contents': [{'type': 'text', 'text': sub, 'color': '#FFFFFFCC', 'size': 'xs'},
                         {'type': 'text', 'text': title, 'color': '#FFFFFF', 'weight': 'bold', 'size': 'lg', 'wrap': True}]}


def _text(t, **kw):
    return dict({'type': 'text', 'text': t, 'wrap': True, 'size': 'sm', 'color': INK}, **kw)


def _row(k, v):
    return {'type': 'box', 'layout': 'horizontal', 'margin': 'sm', 'contents': [
        {'type': 'text', 'text': k, 'size': 'sm', 'color': SOFT, 'flex': 3},
        {'type': 'text', 'text': v, 'size': 'sm', 'color': INK, 'align': 'end', 'flex': 5, 'wrap': True}]}


def _btn(label, action):
    return {'type': 'button', 'style': 'link', 'height': 'sm', 'color': LINK, 'action': dict(action, label=label[:20])}


def _bubble(title, grad, body, buttons, alt, sub='พบรักรีสอร์ท'):
    b = {'type': 'bubble', 'header': _header(title, grad, sub),
         'body': {'type': 'box', 'layout': 'vertical', 'spacing': 'sm', 'contents': body}}
    if buttons:
        b['footer'] = {'type': 'box', 'layout': 'vertical', 'spacing': 'none', 'paddingAll': '4px', 'contents': buttons}
    return {'type': 'flex', 'altText': alt[:400], 'contents': b}


def _links(cfg, no=None):
    out = []
    if cfg['map']:
        out.append(_btn('📍 ดูแผนที่', {'type': 'uri', 'uri': cfg['map']}))
    d = _digits(cfg['phone'])
    if d:
        out.append(_btn('โทร ' + cfg['phone'], {'type': 'uri', 'uri': 'tel:' + d}))
    liff = _env('LIFF_ID')
    if no and liff:
        out.append(_btn('ดูรายละเอียดการจอง', {'type': 'uri', 'uri': 'https://liff.line.me/%s?no=%s' % (liff, no)}))
    return out


def build(kind, t, cfg, *, ready=False, test=False):
    """สร้างข้อความ LINE (รายการ) จากข้อมูลผู้รับ t (ผลของ pp_am_target) และการตั้งค่า"""
    who = 'คุณ' + _first(t.get('name'))
    rooms = ', '.join(t.get('rooms') or []) or '-'
    sub = 'พบรักรีสอร์ท' + (' · ทดสอบ' if test else '')
    no = t.get('no')
    if kind == 'arrive':
        n = int(t.get('nights') or 1)
        head = _text('%s ห้อง %s · %s คืน' % (who, rooms, n), weight='bold')
        if ready:
            return [_bubble('วันนี้พบกันนะคะ · ห้องพร้อมแล้ว ✓', GREEN,
                            [head, _text('ห้องทำความสะอาดเรียบร้อยแล้ว มาถึงเมื่อไหร่ เช็คอินได้เลยค่ะ ไม่ต้องรอ %s น.' % cfg['checkin_time'])],
                            _links(cfg, no), 'วันนี้พบกันนะคะ ห้องพร้อมแล้ว เช็คอินได้เลย', sub)]
        return [_bubble('วันนี้พบกันนะคะ 🌿', BLUE,
                        [head, _text('เช็คอินได้ตั้งแต่ %s น. ค่ะ' % cfg['checkin_time'])],
                        _links(cfg, no), 'วันนี้พบกันนะคะ เช็คอินได้ตั้งแต่ %s น.' % cfg['checkin_time'], sub)]
    if kind == 'welcome':
        body = [_row('📶 Wi‑Fi', '%s / %s' % (cfg['wifi_name'], cfg['wifi_pass'])),
                _row('🍳 อาหารเช้า', cfg['breakfast'] + ('' if 'น' in cfg['breakfast'] else ' น.')),
                _row('🕛 เช็คเอาท์', 'ไม่เกิน %s น.' % cfg['checkout_time']),
                _text('มีอะไรให้ช่วย พิมพ์ในแชทนี้ได้เลยค่ะ', size='xs', color=SOFT, margin='md')]
        btns = [_btn('ขอของใช้', {'type': 'message', 'text': 'ขอของใช้'}),
                _btn('แจ้งปัญหาในห้อง', {'type': 'message', 'text': 'แจ้งปัญหาในห้อง'})]
        d = _digits(cfg['phone'])
        if d:
            btns.append(_btn('โทรหาโรงแรม', {'type': 'uri', 'uri': 'tel:' + d}))
        return [_bubble('ยินดีต้อนรับค่ะ %s' % who, ORCHID, body, btns, 'ยินดีต้อนรับค่ะ ห้อง %s · ไวไฟ อาหารเช้า เวลาเช็คเอาท์' % rooms,
                        'พบรักรีสอร์ท · ห้อง %s%s' % (rooms, ' · ทดสอบ' if test else ''))]
    if kind == 'remind':
        return [_bubble('พรุ่งนี้เช็คเอาท์นะคะ', BLUE,
                        [_text('เช็คเอาท์ภายใน %s น. ค่ะ ถ้าต้องการพักต่อหรือเช็คเอาท์ช้า พิมพ์บอกในแชทนี้ได้เลย' % cfg['checkout_time'])],
                        [_btn('ขอเช็คเอาท์ช้า', {'type': 'message', 'text': 'ขอเช็คเอาท์ช้า / พักต่อ'})],
                        'พรุ่งนี้เช็คเอาท์ภายใน %s น.' % cfg['checkout_time'], sub)]
    if kind == 'rate':
        key = 'TEST' if test else t.get('key')
        stars = {'type': 'box', 'layout': 'horizontal', 'spacing': 'sm', 'margin': 'lg', 'contents': [
            {'type': 'button', 'style': 'secondary', 'height': 'sm', 'flex': 1,
             'action': {'type': 'postback', 'label': str(i), 'data': 'pp_rate|%s|%d' % (key, i), 'displayText': 'ให้คะแนน %d' % i}}
            for i in range(1, 6)]}
        return [_bubble('เช็คเอาท์เรียบร้อยค่ะ', ORCHID,
                        [_text('ขอบคุณที่พักกับพบรักรีสอร์ทนะคะ %s เดินทางปลอดภัยค่ะ 🙏\nช่วยให้คะแนนการพักครั้งนี้หน่อยนะคะ' % who), stars],
                        [_btn('จองอีกครั้ง', {'type': 'message', 'text': 'จองห้องพัก'})],
                        'ขอบคุณที่พักกับพบรักรีสอร์ท ช่วยให้คะแนน 1-5 หน่อยนะคะ', sub)]
    raise ValueError(kind)


def _missing(kind, cfg):
    """ข้อความนี้ต้องใช้ข้อมูลโรงแรมอะไรที่ยังว่างอยู่"""
    if kind == 'welcome':
        return [n for k, n in (('wifi_name', 'ชื่อไวไฟ'), ('wifi_pass', 'รหัสไวไฟ'), ('breakfast', 'เวลาอาหารเช้า')) if not cfg[k]]
    return []


def _push(to, msgs):
    import web
    return web.line_push(to, msgs)


def _chat_note(t, text):
    try:   # ให้พนักงานเห็นในแชทลูกค้า (ไม่ใส่รหัสไวไฟ)
        rpc('pp_chat_log', {'p_line_user_id': t['line_user_id'], 'p_display_name': t.get('name'), 'p_sender': 'ระบบ', 'p_body': text})
    except Exception:
        pass


def deliver(kind, t, cfg, *, ready=False):
    """ส่ง 1 ข้อความให้ 1 กลุ่มการจอง (กันซ้ำด้วย auto_msg_log) คืน 'sent' / 'skipped' / 'failed' / None(ไม่ได้ส่ง ไม่ได้บันทึก)"""
    if not t or t.get('cancelled') or not t.get('line_user_id'):
        return None
    key = t['key']
    if not rpc('pp_am_claim', {'p_kind': kind, 'p_key': key, 'p_line': t['line_user_id'], 'p_no': t.get('no')}):
        return None
    miss = _missing(kind, cfg)
    if miss:
        rpc('pp_am_done', {'p_kind': kind, 'p_key': key, 'p_status': 'skipped', 'p_reason': 'ขาดข้อมูล: ' + ', '.join(miss), 'p_payload': None})
        return 'skipped'
    msgs = build(kind, t, cfg, ready=ready)
    err = _push(t['line_user_id'], msgs)
    payload = {'alt': msgs[0].get('altText')}
    if os.environ.get('LOCAL_DEV'):
        payload['messages'] = msgs   # เครื่องทดสอบเท่านั้น (ให้เทสต์ตรวจเนื้อหา) · ของจริงไม่เก็บรหัสไวไฟลงประวัติ
    if err:
        rpc('pp_am_done', {'p_kind': kind, 'p_key': key, 'p_status': 'failed', 'p_reason': err[:200], 'p_payload': payload})
        return 'failed'
    rpc('pp_am_done', {'p_kind': kind, 'p_key': key, 'p_status': 'sent', 'p_reason': None, 'p_payload': payload})
    _chat_note(t, '[ส่งอัตโนมัติ · %s] %s' % (LABEL[kind], msgs[0].get('altText')))
    return 'sent'


# ---------- ตัวกระตุ้น ----------
def on_act(k, data, out):
    """เรียกหลังพนักงานกดปุ่มในหน้าจอ: เช็คอิน (มอบคีย์การ์ด) → welcome · เช็คเอาท์ → rate"""
    if k not in ('checkin', 'checkout') or data.get('move') or not data.get('no'):
        return None
    kind = 'welcome' if k == 'checkin' else 'rate'
    cfg = settings()
    if not cfg['on'] or menu_state(kind) != 'on':
        return None
    t = rpc('pp_am_target', {'p_no': data['no']})
    if kind == 'rate' and not (t or {}).get('all_out'):
        return None   # เช็คเอาท์ครบทุกห้องในการจองแล้วค่อยส่ง
    return deliver(kind, t, cfg)


_last_tick = [0.0]


def tick(now, force=False):
    """ตัวตั้งเวลา (เรียกจากการเปิดหน้าจอ/โพลล์ และ cron ของ Vercel): เช้าวันเข้าพัก 10:00-17:59 · เตือนเช็คเอาท์ 19:00-21:59 · ส่งซ้ำไม่ได้"""
    if not force and time.time() - _last_tick[0] < 50:
        return {'skipped': 'recent'}
    _last_tick[0] = time.time()
    cfg = settings()
    if not cfg['on']:
        return {'on': False}
    today, hh = now[:10], int(now[11:13])
    res = {'on': True, 'arrive': 0, 'remind': 0}
    ms = None
    try:
        ms = rpc('pp_mod_state') or {}
    except DbError:
        ms = {}
    if 10 <= hh < 18 and menu_state('arrive', ms) == 'on':
        for t in rpc('pp_am_arrivals', {'p_today': today}) or []:
            if deliver('arrive', t, cfg, ready=bool(t.get('ready'))) == 'sent':
                res['arrive'] += 1
    if 19 <= hh < 22 and menu_state('remind', ms) == 'on':
        for t in rpc('pp_am_reminders', {'p_today': today}) or []:
            if deliver('remind', t, cfg) == 'sent':
                res['remind'] += 1
    return res


# ---------- หน้าตั้งค่า ----------
def overview():
    o = rpc('pp_am_overview') or {}
    cfg = settings()
    o['hotel'] = {k: cfg[k] for k in ('wifi_name', 'wifi_pass', 'breakfast', 'checkin_time', 'checkout_time', 'phone', 'map', 'review_url', 'test_to')}
    o['on'] = cfg['on']
    ms = (rpc('pp_mod_state') or {})
    o['kinds'] = {}
    for kind in ('arrive', 'welcome', 'remind', 'rate'):
        st = menu_state(kind, ms)
        miss = _missing(kind, cfg)
        o['kinds'][kind] = {'label': LABEL[kind], 'menu': st, 'missing': miss,
                            'state': 'off' if st != 'on' else ('skip' if miss else 'ready')}
    return o


def save(p, role):
    allowed = {k: v for k, v in (p or {}).items() if k in ('on', 'wifi_name', 'wifi_pass', 'breakfast', 'checkin_time', 'checkout_time', 'phone', 'map', 'review_url', 'test_to')}
    rpc('pp_am_save', {'p': allowed, 'p_role': role})
    return overview()


def send_test(kind, variant, to_id):
    """ส่งตัวอย่างข้อความหาบัญชี LINE ที่เลือก (ไม่ผ่านสวิตช์หลัก ไม่นับเป็นการส่งจริง ไม่เข้าประวัติกันซ้ำ)"""
    if kind not in MENU_ID:
        raise ValueError('ไม่รู้จักข้อความนี้')
    if not to_id:
        raise ValueError('ยังไม่ได้เลือกบัญชี LINE ที่จะส่งทดสอบ')
    cfg = settings()
    miss = _missing(kind, cfg)
    if miss:
        raise ValueError('ยังไม่ได้กรอก: ' + ', '.join(miss))
    t = {'name': 'ธนกฤต วงศ์ศรีแก้ว', 'rooms': ['B06'], 'nights': 2, 'no': 'BK0000000', 'key': 'TEST'}
    msgs = build(kind, t, cfg, ready=(variant != 'wait'), test=True)
    err = _push(to_id, msgs)
    if err:
        raise ValueError('ส่งเข้า LINE ไม่สำเร็จ: ' + err)
    return {'ok': True}
