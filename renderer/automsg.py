# -*- coding: utf-8 -*-
"""ข้อความอัตโนมัติหาลูกค้าทาง LINE (การ์ดตามภาพร่าง docs/mockups/liff/auto_msg_v2.png · ต้องรัน 22_automsg.sql)
  arrive  เช้าวันเข้าพัก 10:00  (ห้องพร้อม → "เช็คอินได้เลย" · ยังไม่พร้อม → "เช็คอินได้ตั้งแต่ 14:00")
  welcome ทันทีหลังพนักงานกดเช็คอิน (มอบคีย์การ์ด): ไวไฟ อาหารเช้า เวลาเช็คเอาท์
  rate    ทันทีหลังพนักงานกดเช็คเอาท์: ขอบคุณ + ปุ่มให้คะแนน 1-5 (ตอบรับคะแนนอยู่ที่ api/line-webhook.js)
กติกา: สวิตช์หลักปิดอยู่เป็นค่าเริ่มต้น · ช่องข้อมูลโรงแรมที่ว่าง = ข้ามข้อความที่ต้องใช้ · 1 เหตุการณ์ต่อ 1 การจองส่งครั้งเดียว
ทุกฟังก์ชันที่ถูกเรียกจากปุ่มของพนักงานห้ามทำให้ปุ่มพัง (ครอบ try ไว้ที่ on_act)"""
import json, os, re, time
from db import rpc, DbError

MENU_ID = {'arrive': 'pre', 'welcome': 'stay', 'rate': 'thanks'}   # ข้อความในเมนู CRM ที่เป็นสวิตช์ "ใช้งาน"
MENU_DEFAULT = {'pre': 'on', 'stay': 'on', 'thanks': 'on'}                              # ยังไม่เคยบันทึกเมนูนี้ = เปิด
LABEL = {'arrive': 'เช้าวันเข้าพัก', 'welcome': 'ต้อนรับหลังมอบคีย์การ์ด', 'rate': 'ขอบคุณ + ให้คะแนน'}

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


RATE_LABEL = {1: 'ไม่ประทับใจ', 2: 'ควรปรับปรุง', 3: 'พอใช้', 4: 'ดี', 5: 'ดีเยี่ยม'}
DARK, GOLD, IVORY, STAR_OFF = '#2E1450', '#B8923A', '#FBF8F3', '#D8CFBC'


def _base():
    return _env('PUBLIC_URL') or 'https://promptpak-eight.vercel.app'


def _survey_card(key, who, rooms, test=False):
    """แบบสอบถามขั้น 1: ภาพรวมการพัก · ดาว 5 ดวง (สีเทา) แตะดวงไหน = ให้คะแนนเท่านั้น (ข้อความที่ลูกค้าส่งขึ้นเป็น ⭐ ทอง)"""
    stars = {'type': 'box', 'layout': 'horizontal', 'margin': 'lg', 'contents': [
        {'type': 'box', 'layout': 'vertical', 'flex': 1, 'paddingAll': '2px',
         'action': {'type': 'postback', 'label': 'ให้ %d ดาว' % i, 'data': 'pp_rate|%s|%d' % (key, i), 'displayText': '⭐' * i + ' ' + RATE_LABEL[i]},
         'contents': [{'type': 'text', 'text': '★', 'size': '3xl', 'align': 'center', 'color': STAR_OFF}]} for i in range(1, 6)]}
    ends = {'type': 'box', 'layout': 'horizontal', 'contents': [
        {'type': 'text', 'text': 'ไม่ประทับใจ', 'size': 'xxs', 'color': '#8C7FA0'},
        {'type': 'text', 'text': 'ดีเยี่ยม', 'size': 'xxs', 'color': '#8C7FA0', 'align': 'end'}]}
    head = {'type': 'box', 'layout': 'vertical', 'paddingAll': '16px',
            'background': {'type': 'linearGradient', 'angle': '135deg', 'startColor': DARK, 'endColor': '#4B2477'},
            'contents': [
                {'type': 'box', 'layout': 'horizontal', 'alignItems': 'center', 'contents': [
                    {'type': 'image', 'url': _base() + '/brand/mark_w.png', 'size': '24px', 'aspectMode': 'fit', 'flex': 0},
                    {'type': 'text', 'text': 'พบรักรีสอร์ท' + (' · ทดสอบ' if test else ''), 'size': 'xs', 'color': '#F4E9C8', 'margin': 'sm', 'gravity': 'center'},
                    {'type': 'text', 'text': 'ขั้น 1 / 3', 'size': 'xxs', 'color': '#D9C48A', 'align': 'end', 'gravity': 'center'}]},
                {'type': 'text', 'text': 'ขอบคุณที่มาพักกับเรานะคะ', 'size': 'lg', 'weight': 'bold', 'color': '#FFFFFF', 'margin': 'md', 'wrap': True},
                {'type': 'text', 'text': '%s · ห้อง %s' % (who, rooms), 'size': 'xs', 'color': '#D9C48A', 'margin': 'xs'}]}
    bub = {'type': 'bubble', 'size': 'mega', 'header': head,
           'body': {'type': 'box', 'layout': 'vertical', 'backgroundColor': IVORY, 'paddingAll': '16px', 'contents': [
               {'type': 'text', 'text': 'โดยรวมแล้ว การพักครั้งนี้เป็นอย่างไรบ้างคะ', 'size': 'md', 'weight': 'bold', 'color': DARK, 'wrap': True, 'margin': 'lg'},
               stars, ends]}}
    return {'type': 'flex', 'altText': 'ขอบคุณที่มาพักกับพบรักรีสอร์ท ช่วยให้คะแนนการพักครั้งนี้หน่อยนะคะ', 'contents': bub}


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
    if kind == 'rate':
        key = 'TEST' if test else t.get('key')
        return [_survey_card(key, who, rooms, test)]
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
    """ตัวตั้งเวลา (เรียกจากการเปิดหน้าจอ/โพลล์ และ cron ของ Vercel): เช้าวันเข้าพัก 10:00-17:59 · ส่งซ้ำไม่ได้"""
    if not force and time.time() - _last_tick[0] < 50:
        return {'skipped': 'recent'}
    _last_tick[0] = time.time()
    cfg = settings()
    if not cfg['on']:
        return {'on': False}
    today, hh = now[:10], int(now[11:13])
    res = {'on': True, 'arrive': 0}
    ms = None
    try:
        ms = rpc('pp_mod_state') or {}
    except DbError:
        ms = {}
    if 10 <= hh < 18 and menu_state('arrive', ms) == 'on':
        for t in rpc('pp_am_arrivals', {'p_today': today}) or []:
            if deliver('arrive', t, cfg, ready=bool(t.get('ready'))) == 'sent':
                res['arrive'] += 1
    return res


# ---------- หน้าตั้งค่า ----------
def overview():
    o = rpc('pp_am_overview') or {}
    cfg = settings()
    o['hotel'] = {k: cfg[k] for k in ('wifi_name', 'wifi_pass', 'breakfast', 'checkin_time', 'checkout_time', 'phone', 'map', 'review_url', 'test_to')}
    o['on'] = cfg['on']
    ms = (rpc('pp_mod_state') or {})
    o['kinds'] = {}
    for kind in ('arrive', 'welcome', 'rate'):
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
