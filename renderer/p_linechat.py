# -*- coding: utf-8 -*-
import collections
from patch_all import R, J
from nb import *

MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
def short_date(s):
    y, mo, d = map(int, s[:10].split('-')); return f'{d} {MON[mo-1]}'
def day_short(dn):
    d = EPOCH + datetime.timedelta(days=dn); return f'{d.day} {MON[d.month-1]}'

def tlabel(iso):
    d = dno(iso); k = D0 - d; hhmm = iso[11:16]
    if k <= 0: return hhmm
    if k == 1: return 'เมื่อวาน ' + hhmm
    if k <= 6: return f'{k} วันก่อน ' + hhmm
    return short_date(iso) + ' ' + hhmm

def bd_of(b):
    t = b['nights']
    if b.get('cancelled'): return {'k': 'cancel', 't': t}
    if b.get('noshow'): return {'k': 'cancel', 't': t}
    st = b['stage']
    if st == 'outdone': return {'k': 'done', 't': t}
    if st == 'out': return {'k': 'co', 't': t}
    if st == 'stay': return {'k': 'stay', 'n': D0 - b['start'] + 1, 't': t}
    if b['start'] <= D0: return {'k': 'wait', 't': t, 'date': short_date(REF), 'unpaid': 0 if b['paid'] or b['kind'] == 'credit' else 1}
    return {'k': 'soon', 't': t, 'date': day_short(b['start'])}

def stay_txt(b):
    if b.get('cancelled'): return 'ยกเลิกการจอง'
    if b.get('noshow'): return 'ไม่มาตามนัด'
    st = b['stage']
    if st == 'outdone': return 'เช็คเอาท์แล้ว'
    if st == 'out': return 'เช็คเอาท์วันนี้'
    if st == 'stay': return f"เข้าพักอยู่ · เหลือ {b['end'] - D0} คืน"
    if b['start'] <= D0: return 'จองไว้ · เข้าพักวันนี้'
    return 'จองไว้ · เข้าพัก ' + day_short(b['start'])

def seg_of(n):
    return 'none' if n == 0 else ('often' if n >= 3 else ('rep' if n == 2 else 'new'))

def media_att(meta):
    """รูป/สติกเกอร์/ไฟล์ ที่แนบมากับข้อความ → รูปแบบไฟล์แนบของหน้าแชท"""
    if not isinstance(meta, dict) or not meta.get('type'):
        return None
    t = meta['type']
    if t == 'sticker' and meta.get('sid'):
        return [{'t': 'stk', 'src': 'https://stickershop.line-scdn.net/stickershop/v1/sticker/%s/android/sticker.png' % meta['sid'], 'name': 'สติกเกอร์'}]
    if t == 'image':
        return [{'t': 'img', 'src': meta['url'], 'name': 'รูปภาพ'}] if meta.get('url') else [{'t': 'file', 'name': 'รูปภาพ (โหลดไม่ได้)', 'size': ''}]
    if t in ('file', 'video', 'audio'):
        nm = meta.get('name') or {'video': 'วิดีโอ', 'audio': 'ข้อความเสียง', 'file': 'ไฟล์'}[t]
        sz = meta.get('size')
        return [{'t': 'file', 'name': nm, 'size': ('%.1f MB' % (sz / 1048576) if sz and sz > 1048576 else ('%d KB' % (sz // 1024) if sz else '')), 'u': meta.get('url') or ''}]
    return None


def build():
    CV, BKN, BD, PF, LCX = [], {}, {}, {}, {}
    for i, t in enumerate(sorted(m['line_chats'], key=lambda x: x['thread_id']), 1):
        g = G[t['guest_id']]
        b = BKBY.get(t['linked_booking_id'])
        last = t['last_message_at']
        ago = max(0, (REFMS - msl(last)) // 60000)
        msgs = []
        for x in t['messages']:
            who = {'ลูกค้า': 'c', 'ระบบอัตโนมัติ': 'b', 'พนักงาน': 's'}[x['from']]
            tx = x['text']
            if x['type'] == 'image': tx = '🖼 ' + tx
            elif x['type'] == 'file': tx = '📎 ' + tx
            elif x['type'] == 'flex': tx = '🧾 ' + tx
            att = media_att(x.get('meta'))
            if att:
                tx = ''
            msgs.append([who, tx, tlabel(x['at'])] + ([att] if att else []))
        key = t.get('db_key') or t['thread_id']
        cs = (m.get('chat_state') or {}).get(key) or {}
        for x in cs.get('sent') or []:   # ข้อความที่พนักงานพิมพ์ในแชทตัวอย่าง
            att = media_att(x.get('meta'))
            msgs.append(['s', '' if att else x['body'], tlabel(x['at'])] + ([att] if att else []))
            last = max(last, x['at'])
        ago = max(0, (REFMS - msl(last)) // 60000)
        cust_at = max([x['at'] for x in t['messages'] if x['from'] == 'ลูกค้า'] or [''])
        staff_at = max([x['at'] for x in t['messages'] if x['from'] == 'พนักงาน'] + [x['at'] for x in cs.get('sent') or []] or [''])
        n_st = len([s for s in BK if s['gid'] == g['guest_id'] and s['start'] <= D0])
        co = CO[g['company_id']]['name_th'] if g['company_id'] in CO else ''
        st = 'new' if (t['unread_count'] > 0 or t['status'] == 'รอพนักงาน') else 'done'
        if staff_at and staff_at >= cust_at and msgs and msgs[-1][0] == 's':
            st = 'wait'   # พนักงานตอบล่าสุด รอลูกค้าตอบกลับ
        if cs.get('closed_at') and cs['closed_at'] >= max(cust_at, staff_at):
            st = 'done'
        c = {'id': i, 'name': (t['line_display_name'] if g.get('is_group_chat') else 'คุณ' + g['nickname']), 'line': t['line_display_name'], 'ago': ago, 'st': st,
             'room': b['room'] if b else '', 'stay': stay_txt(b) if b else '', 'co': co, 'stays': n_st, 'sum': '', 'm': msgs,
             'key': key, 'sn': list(cs.get('notes') or []), 'read': bool(cs.get('read_at') and cs['read_at'] >= cust_at)}
        if cs.get('alias'):
            c['name'] = cs['alias']
        CV.append(c)
        if b:
            BKN[str(i)] = b['no']; BD[str(i)] = bd_of(b)
        else:
            BD[str(i)] = {'k': 'none'}
        PF[str(i)] = {'real': g['first_name'] + ' ' + g['last_name'], 'mem': 1 if g['is_member'] else 0, 'seg': seg_of(n_st),
                    'cs': (CSAT_G.get(g['guest_id']) or [0, 0])[0], 'nocs': bool(g.get('is_group_chat'))}
        LCX[str(i)] = {'line': t['line_display_name'], 'co': co, 'stays': n_st}
    purp = {str(i): (BKBY[t['linked_booking_id']]['purpose'] if t['linked_booking_id'] in BKBY else '') for i, t in enumerate(sorted(m['line_chats'], key=lambda x: x['thread_id']), 1)}
    return CV, BKN, BD, PF, LCX, purp

def patch(h):
    CV, BKN, BD, PF, LCX, purp = build()
    i = h.index('const CV=['); j = h.index("const stageOf=")
    from p_cust import FACE_JS
    h = h[:i] + FACE_JS + 'const CV=' + J(CV) + ';\nconst BKN=' + J(BKN) + ';\n' + h[j:]
    # ลบ CV.push(id 10) ... ถึงก่อน BS
    i = h.index("CV.push({id:10,"); j = h.index("const BS={")
    h = h[:i] + 'const BD=' + J(BD) + ';\nconst PF=' + J(PF) + ';\nconst LCX=' + J(LCX) + ';\nconst PURP=' + J(purp) + ';\n' + \
        "CV.forEach(c=>{if(LCX[c.id])Object.assign(c,LCX[c.id])});\nCV.forEach(c=>{c.purp=PURP[c.id]||'';c.bd=BD[c.id];Object.assign(c,PF[c.id]);c.sn=c.sn||[]});\n" + h[j:]
    h = R(h, "<option ${c.own==='พลอย'?'selected':''}>พลอย</option><option ${c.own==='เมท'?'selected':''}>เมท</option>",
          "<option ${c.own==='ป้าใจ'?'selected':''}>ป้าใจ</option><option ${c.own==='ดวน'?'selected':''}>ดวน</option><option ${c.own==='ใบ'?'selected':''}>ใบ</option><option ${c.own==='เจ้าของ'?'selected':''}>เจ้าของ</option>", 1, 'lc-own')
    return h
