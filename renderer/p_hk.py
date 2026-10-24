# -*- coding: utf-8 -*-
from patch_all import R, J
from nb import *

HKAT = {h['room_id']: h for h in m['housekeeping_at_ref']}

def guests_by_room():
    g = {}
    for b in sorted(BK, key=lambda x: (x['start'], x['no'])):
        if b['start'] <= D0 and b['stage'] in ('stay', 'out', 'outdone'):
            g[b['room']] = {'name': b['guest'], 'no': b['no'], 'phone': b['phone'], 'line': b['line'], 'ci': b['start'] - D0}
    return g

def patch(h):
    i = h.index("const HKS=["); j = h.index("\n", i)
    h = h[:i] + "const HKS=[{n:'ป้าใจ',on:true},{n:'ดวน',on:true},{n:'ใบ',on:true}];" + h[j:]
    # แขกล่าสุดของห้อง
    i = h.index("const GUESTS={"); j = h.index("};", i) + 2
    h = h[:i] + "const GUESTS=" + J(guests_by_room()) + ";" + h[j:]
    # งานทำความสะอาดวันนี้: ห้องเตรียมรับแขก
    tasks = []
    for rid, r in sorted(HKAT.items()):
        if r['status_at_ref'] == 'เตรียมรับแขกวันนี้':
            b = next(x for x in BK if x['room'] == rid and x['start'] == D0)
            note = 'ลูกค้าขอเช็คอินก่อนเวลา' if rid in ('B011', 'B012') else 'ลูกค้าเช็คอินวันนี้'
            tasks.append((rid, SN[r['assigned_to']], note))
    js = "let TASKS=[\n" + ",\n".join("  mkT(%s,'arrive',%s,1,null,null,%s)" % (J(a), J(b), J(c)) for a, b, c in tasks) + "\n];"
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
    return h
