# -*- coding: utf-8 -*-
"""ข้อมูลจริงของ "กลุ่มลูกค้า" (CRM › ภาพรวมลูกค้า) สำหรับป๊อปอัปเส้นทางลูกค้า
ทุกตัวเลขคำนวณจากการจอง/เมนูการเงิน/แบบสอบถามในฐานข้อมูล (ไม่แต่งเอง) · AI เล่าตัวตนจากตัวเลขชุดนี้ (api/segment.js)
กลุ่มใช้กฎเดิมของระบบ (persona) B=ลูกค้าบริษัท, W3=ช่างจ่ายเอง, L=ลูกค้าทั่วไป"""
import collections, statistics
from nb import *
from p_cust import _svc_of
import p_crm

MIN_STAGE = 3          # ข้อมูลน้อยกว่านี้ ไม่แสดงกล่องของช่วงนั้น
MIN_GROUP = 10         # จำนวนการเข้าพักต่ำสุดของกลุ่มที่จะบอกว่า "ข้อมูลพอ"
WIN = 90               # 1 ไตรมาส = 90 วัน

CHN = {'LINE OA': 'line', 'โทรศัพท์': 'phone', 'Walk-in': 'walk'}

def _key(g):
    p = p_crm.persona(g)
    return 'L' if p[0] == 'L' else ('W3' if p == 'W3' else 'B')

def _hhmm(mins):
    return '%02d:%02d' % (int(mins) // 60, int(mins) % 60)

def _med(a):
    return statistics.median(a) if a else None

def _mins(ms):
    return (ms // 60000) % 1440

ROOMT = {r['code']: ('ตึกใหม่ ' if r['zone'] == 'A' else 'บ้านหลัง ') + r['type'] for r in ROOMS}

def build():
    gk = {g['guest_id']: _key(g) for g in m['guests']}
    gby = {g['guest_id']: g for g in m['guests']}
    by = collections.defaultdict(list)
    for b in BK:
        if b['gid'] in gk:
            by[gk[b['gid']]].append(b)
    tot_g = len({b['gid'] for b in BK})
    allst = collections.defaultdict(list)       # ครั้งที่เข้าพักทั้งหมดของแต่ละแขก (เรียงวัน) ไว้นับ "กลับมาซ้ำ"
    for b in BK:
        allst[b['gid']].append(b['start'])
    out = {}
    for k in ('B', 'W3', 'L'):
        A = by.get(k, [])
        gs = {b['gid'] for b in A}
        o = {'n': len(A), 'ng': len(gs), 'share': round(100 * len(gs) / tot_g) if tot_g else 0,
             'enough': len(A) >= MIN_GROUP}
        # ช่องทางจอง
        cc = collections.Counter(CHN.get(b['ch'], 'line') for b in A)
        if A:
            main, c = cc.most_common(1)[0]
            leads = [b['lead'] for b in A if b['lead'] is not None and CHN.get(b['ch']) != 'walk']
            o['ch'] = {'main': main, 'pct': round(100 * c / len(A)), 'lead': (round(_med(leads)) if len(leads) >= MIN_STAGE else None)}
        # เวลาถึง/เช็คอิน และเช็คเอาท์ (เวลาจริงที่พนักงานกด)
        ci = [_mins(b['ciAt']) for b in A if b['ciAt']]
        co = [_mins(b['coAt']) for b in A if b['coAt']]
        o['ci'] = _hhmm(_med(ci)) if len(ci) >= MIN_STAGE else None
        o['co'] = _hhmm(_med(co)) if len(co) >= MIN_STAGE else None
        if A:
            o['pax'] = round(sum(b['pax'] for b in A) / len(A), 1)
            o['rooms'] = round(sum(len([x for x in BK if x['group'] == b['group']]) for b in A) / len(A), 1)
            o['nights'] = round(sum(b['nights'] for b in A) / len(A), 1)
            rt = collections.Counter(ROOMT.get(b['room'], '') for b in A)
            t, c = rt.most_common(1)[0]
            o['room'] = {'t': t, 'pct': round(100 * c / len(A))}
        # ซักรีด/อาหารเช้า
        sv = [_svc_of(b['no'], b['room']) for b in A]
        lau = sum(1 for _, its in sv if any('ซัก' in (i[0] or '') for i in its))
        o['laundry'] = {'pct': round(100 * lau / len(A)), 'n': lau} if A else None
        bf = sum(1 for b in A if (b.get('bf') or 0) > 0)
        o['bf'] = {'pct': round(100 * bf / len(A)), 'n': bf} if A else None
        # ใช้จ่ายต่อคน / กลับมาซ้ำ / ความพึงพอใจ
        def spend(sub):
            if not sub:
                return None
            pax = sum(b['pax'] for b in sub) or 1
            return round(sum(b['total'] + _svc_of(b['no'], b['room'])[0] for b in sub) / pax)
        o['spend'] = spend(A)
        o['rep'] = round(100 * sum(1 for g in gs if len(allst[g]) >= 2) / len(gs)) if gs else None
        sc = [CSAT_G[g] for g in gs if g in CSAT_G]
        n_sc = sum(x[1] for x in sc)
        o['sat'] = {'avg': round(sum(x[0] * x[1] for x in sc) / n_sc, 1), 'n': n_sc} if n_sc else None
        # ตัวติดตามเทียบไตรมาส: 4 ช่วง ช่วงละ 90 วัน (ล่าสุดอยู่ท้ายสุด)
        sp, rp = [], []
        for w in range(3, -1, -1):
            hi, lo = D0 - w * WIN, D0 - w * WIN - WIN + 1
            sub = [b for b in A if lo <= b['start'] <= hi]
            sp.append(spend(sub))
            g2 = {b['gid'] for b in sub}
            rp.append(round(100 * sum(1 for g in g2 if sum(1 for s in allst[g] if s <= hi) >= 2) / len(g2)) if g2 else None)
        o['trk'] = {'spend': sp, 'rep': rp}
        # ตัวตน
        ages = [gby[g]['age'] for g in gs if gby[g].get('age')]
        pv = collections.Counter(gby[g]['home_province'] for g in gs if gby[g].get('home_province'))
        o['facts'] = {'age': round(sum(ages) / len(ages)) if ages else None,
                      'prov': pv.most_common(1)[0][0] if pv else None,
                      'provPct': round(100 * pv.most_common(1)[0][1] / len(gs)) if pv and gs else None,
                      'company': collections.Counter(CO[gby[g]['company_id']]['name_th'] for g in gs if gby[g].get('company_id') in CO).most_common(1)[0][0]
                      if any(gby[g].get('company_id') in CO for g in gs) else None}
        out[k] = o
    return out
