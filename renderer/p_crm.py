# -*- coding: utf-8 -*-
import json, re, collections
from patch_all import R, J
from nb import *
import p_cust

BASE = dno('2026-01-01')
PUL = ['ทำงาน', 'แวะพัก', 'งานบุญ', 'ราชการ/อบรม']
RTL = []
for r in ROOMS:
    t = ('ตึกใหม่ ' if r['zone'] == 'A' else 'บ้านหลัง ') + r['type']
    if t not in RTL: RTL.append(t)
RTL_IDX = {}
for r in ROOMS:
    RTL_IDX[r['code']] = RTL.index(('ตึกใหม่ ' if r['zone'] == 'A' else 'บ้านหลัง ') + r['type'])
N_TOWER_TYPES = sum(1 for t in RTL if t.startswith('ตึก'))
CHI = {'LINE OA': 0, 'โทรศัพท์': 1, 'Walk-in': 2}
GIDX = {g['guest_id']: i for i, g in enumerate(m['guests'])}

def persona(g):
    ks = set(b['kind'] for b in BK + BC if b['gid'] == g['guest_id'])
    if g['company_id'] in CO:
        return 'W1' if (ks & {'now', 'credit'}) else 'W3'
    return 'L1' if g['home_province'] == 'ขอนแก่น' else ('L3' if g['segment'] == 'ทั่วไป-แวะพัก' else 'L2')

def build_raw():
    grpn = collections.Counter(b['group'] for b in BK)
    gl = []
    for g in m['guests']:
        gl.append([g['first_name'] + ' ' + g['last_name'], g['home_province'] or '', CO[g['company_id']]['name_th'] if g['company_id'] in CO else '',
                   g['position'] if g['company_id'] in CO else '', 1 if g['is_member'] else 0, persona(g), g['age'] or 0])
    sl = []
    for b in sorted(BK, key=lambda x: (x['start'], x['no'])):
        pu = PUL.index(b['purpose']) if b['purpose'] in PUL else 0
        sl.append([GIDX[b['gid']], b['start'] - BASE, b['nights'], RTL_IDX[b['room']], grpn[b['group']], CHI.get(b['ch'], 0), b['lead'],
                   int(b['hm'][:2]), pu, 1 if b['cid'] in CO else 0, 1 if b['taxReq'] else 0, b['total'], 0])
    return {'d0': '2026-01-01', 'cols': ["g", "ci", "n", "rt", "grp", "ch", "ld", "bh", "pu", "pay", "tx", "rm", "fd"], 's': sl, 'g': gl}

AREA_OF = {'ความสะอาด': 'room', 'พนักงาน': 'svc', 'ทำเล': 'place', 'สิ่งอำนวยความสะดวก': 'fix', 'การจอง/เอกสาร': 'book', 'ความเงียบ': 'place',
           'ที่จอดรถ': 'place', 'WiFi': 'fix', 'ห้องพัก': 'room', 'ราคา': 'price', 'อาหารเช้า': 'food', 'ความปลอดภัย': 'room', 'เสียงดัง': 'place'}

def build_fb():
    out = []
    for r in REVIEWS:
        areas = []
        for t in r['topics']:
            a = AREA_OF[t]
            if a not in areas: areas.append(a)
        neg = r['sentiment'] in ('ลบ', 'กลาง') and r['rating_5'] <= 3
        pol = [(-1 if neg else 1)] * len(areas)
        bk = BKBY.get(r['booking_id']) if r['booking_id'] else None
        gi = GIDX[r['guest_id']] if r.get('guest_id') in GIDX else (GIDX[bk['gid']] if bk else -1)
        out.append(['G' if r['source'] == 'Google' else 'L', dno(r['created_at']) - BASE, r['rating_5'], r['text'], areas, pol, gi, [r['text']] * len(areas)])
    return out

def lit(s):
    return json.dumps(s, ensure_ascii=False).replace('</', '<\\/')

def regen_embedded(s, ovp):
    a = s.index('const RAW=') + 10
    _, e = json.JSONDecoder().raw_decode(s[a:])
    s = s[:a] + J(build_raw()) + s[a + e:]
    s = R(s, 'const D0=new Date(2024,0,1);', 'const D0=new Date(2026,0,1);', 1, 'emb-d0')
    s = R(s, '(c.getFullYear()-2024)*12', '(c.getFullYear()-2026)*12', 1, 'emb-mi')
    s = s.replace('min="2024-01-01" max="2025-12-31"', 'min="2026-01-01" max="2027-12-31"')
    s = R(s, 'const TODAY=new Date(2026,9,24);', 'const TODAY=new Date(2026,9,24);', 1, 'emb-today')
    s = R(s, "d1:'2026-10-01',d2:'2026-10-24'", "d1:'2026-10-01',d2:'2026-10-24'", 1, 'emb-ps')
    i = s.index('const RT=['); j = s.index('];', i) + 2
    s = s[:i] + 'const RT=' + J(RTL) + ';' + s[j:]
    s = R(s, "f:s=>s.rt<3?'โซนตึก':'โซนบ้าน'", "f:s=>s.rt<%d?'โซนตึก':'โซนบ้าน'" % N_TOWER_TYPES, 1, 'emb-zone')
    s = R(s, "const PU=['ทำงาน','ท่องเที่ยว','กิจกรรม'];", "const PU=" + J(PUL) + ";", 1, 'emb-PU')
    i = s.index("const ROOM=["); j = s.index("rk=t=>t===0?0:t<=2?1:t===3?2:3;", i) + len("rk=t=>t===0?0:t<=2?1:t===3?2:3;")
    rooms4 = ['โซน' + t.replace(' ', ' · ', 1) for t in RTL]
    s = s[:i] + 'const ROOM=' + J(rooms4) + ',rk=t=>t;' + s[j:]
    if ovp:
        s = R(s, "const PUC=[C('t4'),C('t1'),C('t3')];", "const PUC=[C('t4'),C('t1'),C('t3'),C('t5')];", 1, 'emb-PUC')
        s = R(s, "const n=['โซนตึก เตียงเดี่ยว','โซนตึก เตียงคู่','โซนตึก เตียงคู่','โซนบ้าน เตียงเดี่ยว','โซนบ้าน เตียงคู่'];", "const n=" + J(['โซน' + t for t in RTL]) .replace('โซนตึก ', 'โซนตึก ').replace('โซนบ้าน ', 'โซนบ้าน ') + ";", 1, 'emb-topr')
        s = s.replace('-2024*12', '-2026*12').replace('(x.getFullYear()-2024)*12', '(x.getFullYear()-2026)*12')
        j = s.index('const FB=') + 9
        _, e = json.JSONDecoder().raw_decode(s[j:])
        s = s[:j] + J(build_fb()) + s[j + e:]
        s = R(s, "const pk=g=>{const p=GU[g].ps;return p[0]==='L'?'L':p==='W3'?'W3':'B'};", "const pk=g=>{const p=(GU[g]||{ps:'L1'}).ps;return p[0]==='L'?'L':p==='W3'?'W3':'B'};", 1, 'emb-pk')
    return s

def patch_literal(h, name, ovp):
    i = h.index('const ' + name + '="')
    j = h.index('\n', i)
    line = h[i:j]
    body = line[line.index('=') + 1:].rstrip().rstrip(';')
    s = json.loads(body)
    s = regen_embedded(s, ovp)
    return h[:i] + 'const ' + name + '=' + lit(s) + ';' + h[j:]

def patch(h):
    a = h.index('/* ============ ข้อมูลตัวอย่าง (สมมติทั้งหมด) ============ */')
    b_ = h.index('BKX.forEach(x=>ST.push(x));') + len('BKX.forEach(x=>ST.push(x));')
    h = h[:a] + p_cust.data_block() + h[b_:]
    h = p_cust.apply_common(h)
    h = p_cust.analytics_fixes(h)
    h = patch_literal(h, 'COV', False)
    h = patch_literal(h, 'OVP', True)
    return h
