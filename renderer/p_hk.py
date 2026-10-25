# -*- coding: utf-8 -*-
from patch_all import R, J
from nb import *
import datetime

HKAT = {h['room_id']: h for h in m['housekeeping_at_ref']}

def guests_by_room():
    g = {}
    for b in sorted(BK, key=lambda x: (x['start'], x['no'])):
        if b['start'] <= D0 and b['stage'] in ('stay', 'out', 'outdone'):
            g[b['room']] = {'name': b['guest'], 'no': b['no'], 'phone': b['phone'], 'line': b['line'], 'ci': b['start'] - D0}
    return g

def patch(h):
    hs = m.get('hk_state') or {}
    if hs.get('has_staff'):
        staff = [{'id': x['id'], 'n': x['name'], 'on': x['on'], 'zones': x['zones'] or [], 'rooms': x['rooms'], 'line': x.get('line_key') or '', 'sort': x.get('sort') or 0, 'days': x.get('days'), 'ovr': x.get('ovr')} for x in hs.get('staff') or []]
    else:   # ยังไม่เคยตั้งค่า: ใช้รายชื่อเริ่มต้น (บันทึกทั้งหมดเมื่อแก้ไขครั้งแรก)
        staff = [{'id': 'H1', 'n': 'ป้าใจ', 'on': True, 'zones': [], 'rooms': None, 'line': '', 'sort': 1, 'days': None, 'ovr': None},
                 {'id': 'H2', 'n': 'ดวน', 'on': True, 'zones': ['ตึกใหม่'], 'rooms': None, 'line': '', 'sort': 2, 'days': None, 'ovr': None},
                 {'id': 'H3', 'n': 'ใบ', 'on': True, 'zones': ['บ้านหลัง'], 'rooms': None, 'line': '', 'sort': 3, 'days': None, 'ovr': None}]
    rooms = [{'c': r['code'], 'z': 'ตึกใหม่' if r['zone'] == 'A' else 'บ้านหลัง'} for r in ROOMS]
    chats = [{'k': t['db_key'], 'n': (t.get('line_display_name') or '') } for t in m['line_chats'] if t.get('db_key')]
    i = h.index("const HKS=["); j = h.index("\n", i)
    h = h[:i] + ("const HKS=" + J(staff) + ";\nconst HK_DB=" + ('true' if hs else 'false') + ",HAS_STAFF=" + ('true' if hs.get('has_staff') else 'false')
                 + ";\nlet HK_GROUP=" + J(hs.get('group') or '') + ";\nconst HK_DOW=" + str((datetime.date.fromisoformat(REF).weekday() + 1) % 7) + ";\nconst RMZ=" + J(rooms) + ";\nconst LCH=" + J(chats) + ";") + h[j:]
    # แขกล่าสุดของห้อง
    i = h.index("const GUESTS={"); j = h.index("};", i) + 2
    h = h[:i] + "const GUESTS=" + J(guests_by_room()) + ";" + h[j:]
    # งานทำความสะอาดวันนี้: ห้องเตรียมรับแขก
    tasks = []
    for rid, r in sorted(HKAT.items()):
        if r['status_at_ref'] == 'เตรียมรับแขกวันนี้':
            b = next(x for x in BK if x['room'] == rid and x['start'] == D0)
            note = 'ลูกค้าขอเช็คอินก่อนเวลา' if rid in ('C11', 'C12') else 'ลูกค้าเช็คอินวันนี้'
            tasks.append((rid, SN[r['assigned_to']], note))
    js = "let TASKS=[\n" + ",\n".join("  mkT(%s,'arrive',%s,1,null,null,%s)" % (J(a), J(b), J(c)) for a, b, c in tasks) + "\n];"
    if hs:   # งานจากฐานข้อมูล + งานเตรียมรับแขกตัวอย่างที่ยังไม่มีในฐานข้อมูล
        def ms(ts):
            return 'null' if not ts else "Date.parse(%s)" % J(ts)
        have = {(t['room'], t['kind']) for t in hs.get('tasks') or []}
        rows = ["  {id:++tid,dbid:%d,room:%s,kind:%s,who:%s,st:%d,t2:%s,t3:%s,note:%s,auto:%s}" % (
            t['id'], J(t['room']), J(t['kind']), J(t['who']), t['st'], ms(t.get('t2')), ms(t.get('t3')), J(t.get('note') or ''), 'true' if t.get('auto') else 'false')
            for t in hs.get('tasks') or []]
        rows += ["  mkT(%s,'arrive',%s,1,null,null,%s)" % (J(a), J(b), J(c)) for a, b, c in tasks if (a, 'arrive') not in have]
        js = "let TASKS=[\n" + ",\n".join(rows) + "\n];"
    i = h.index("let TASKS=["); j = h.index("];", i) + 2
    h = h[:i] + js + h[j:]
    outs = [rid for rid, r in sorted(HKAT.items()) if r['status_at_ref'] == 'มีแขก – เช็คเอาท์วันนี้']
    i = h.index("const CHECKOUTS_TODAY="); j = h.index("\n", i)
    h = h[:i] + "const CHECKOUTS_TODAY=" + J(outs) + "; // ห้องที่แขกเช็คเอาท์วันนี้ (จากข้อมูลหน้าแรก)" + h[j:]
    # ของที่พบ/ของหาย/แจ้งซ่อม: ชุดข้อมูลใหม่ไม่มี จึงเริ่มว่าง
    i = h.index("const FOUND=["); j = h.index("];", i) + 2
    h = h[:i] + "const FOUND=[];" + h[j:]
    i = h.index("const LOST=["); j = h.index("];", i) + 2
    h = h[:i] + "const LOST=[];" + h[j:]
    i = h.index("let REPAIRS=["); j = h.index("];", i) + 2
    h = h[:i] + "let REPAIRS=[];" + h[j:]
    i = h.index("const ROOMS=[];"); j = h.index("\n", i)
    h = h[:i] + "const ROOMS=" + J([r['code'] for r in ROOMS]) + ";" + h[j:]
    return h
