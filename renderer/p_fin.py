# -*- coding: utf-8 -*-
import collections
from patch_all import R, J
from nb import *

RECV = {r['booking_id']: r for r in m['receivables']}

def fin_bills():
    out = []
    for b in sorted(BK + BC, key=lambda x: x['no']):
        ps = PAY.get(b['no'], [])
        roomp = [p for p in ps if p['type'].startswith('ค่าห้อง')]
        depin = [p for p in ps if p['type'] == 'มัดจำห้อง (รับ)']
        depout = [p for p in ps if p['type'] == 'มัดจำห้อง (คืน)']
        pays = [{'m': mth(p), 'amt': p['amount'], 'at': msl(p['paid_at']), 'by': SN.get(p['received_by'], ''),
                 'slip': 'sample' if mth(p) == 'transfer' else None, 'tag': 'room'} for p in roomp]
        d = {'no': b['no'], 'guest': b['guest'], 'room': b['room'], 'nights': b['nights'], 'start': b['start'], 'total': b['total'],
             'paid': sum(p['amt'] for p in pays), 'dep': 'no', 'pays0': pays, 'pays': pays, 'line': b['line']}
        if depin:
            d['dep'] = 'back' if depout else 'held'
            d['depAt'] = msl(depin[0]['paid_at']); d['depM'] = mth(depin[0])
            if depout:
                d['depOutAt'] = msl(depout[0]['paid_at']); d['depOutM'] = mth(depout[0])
        if b['kind'] == 'credit' and b['cid'] in CO:
            rv = RECV.get(b['no'])
            d['credit'] = {'org': CO[b['cid']]['name_th'], 'po': '', 'due': dno(rv['due_date']) if rv else b['end'] + CO[b['cid']]['credit_days']}
        if b.get('cancelled') or b.get('noshow'):
            d['cancelled'] = True
            d['cancelAt'] = b['cancelAt'] or (msl('2026-10-23T00:00:00') if b.get('noshow') else None)
            if b.get('noshow'):
                d['cancelWhy'] = 'ไม่มาตามนัด'
        out.append(d)
    return out

def patch(h):
    # 1) ข้อมูลบิล
    i = h.index('const DEPOSIT=200;'); j = h.index('const itemsSum=')
    rmap = {r['code']: r['type'] for r in ROOMS}
    rate = {r['code']: r['rate'] for r in ROOMS}
    new = ('const DEPOSIT=300; // เงินประกันห้อง ต่อห้อง (ตามข้อมูลโรงแรม)\n'
           'const RMTYPE=' + J(rmap) + ', RMRATE=' + J(rate) + ';\n'
           'const rate=code=>RMRATE[code]||0, rtypeOnly=code=>RMTYPE[code]||"";\n'
           "const rtype=code=>!code?'บริการอื่นๆ · ไม่มีห้องพัก':`${code[0]==='A'?'โซนตึก':'โซนบ้าน'} · ห้อง ${code} · ${rtypeOnly(code)}`;\n"
           'let BILLS=' + J(fin_bills()) + ';\n'
           'const toLoc=ms=>{const d=new Date(ms),s0=new Date(d.getFullYear(),d.getMonth(),d.getDate());return Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())+(ms-s0.getTime())};\n'
           'const nowLoc=()=>toLoc(Date.now());\n'
           'const bkOf=n=>BILLS.find(b=>b.no===n);\n')
    h = h[:i] + new + h[j:]
    h = R(h, "const rtype2=code=>!code?'บริการอื่นๆ':`${code[0]==='A'?'โซนตึก':'โซนบ้าน'} · ${rtypeOnly(code)}`;", "const rtype2=code=>!code?'บริการอื่นๆ':`${code[0]==='A'?'โซนตึก':'โซนบ้าน'} · ${rtypeOnly(code)}`;", 1, 'fin-rtype2')
    # 2) พนักงาน
    h = R(h, "const STAFF=['คุณเอก','คุณพลอย','คุณดาว'];", "const STAFF=['ป้าใจ','ดวน','ใบ','เจ้าของ'];", 1, 'fin-staff')
    # 3) ล้างตัวอย่างรายการเรียกเก็บอื่นๆ
    i = h.index('(function(){\n  const mkSv='); j = h.index('let _k=0;')
    h = h[:i] + h[j:]
    h = R(h, "pushTxn({time:TODAY*DAY+45000000,item:'ขายอาหารเช้าเพิ่ม (ไม่ผูกการจอง)',bk:'',cat:'อาหารเช้า',method:'เงินสด',type:'in',amount:170,who:pick(STAFF)});\n", "", 1, 'fin-txn-sample')
    # 4) ล้างตัวอย่าง "เมื่อวานปิดยอดแล้ว"
    i = h.index('/* ตัวอย่าง: เมื่อวานปิดยอดแล้ว'); j = h.index('CLOSED_DAYS.add(y); }', i) + len('CLOSED_DAYS.add(y); }')
    h = h[:i] + h[j:]
    h = R(h, 'DEPL[b.dep]', "(b.cancelled&&b.dep==='no'?['ไม่ได้เก็บ','b-dep-back']:DEPL[b.dep])", 4, 'fin-depl')
    h = h.replace('BK2610-0205', 'BK6910042')
    return h
