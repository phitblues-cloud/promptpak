# -*- coding: utf-8 -*-
from patch_all import R, J
from nb import *

def out_today(b):
    """เช็คเอาท์จริงวันนี้ (ยังแสดงการ์ดไว้ให้คืนเงินประกัน)"""
    return bool(b.get('coAt')) and b['coAt'] // 86400000 == D0


def home_cards():
    cards = []
    for b in BK:
        if not b['stage'] or (b['stage'] == 'outdone' and not out_today(b)) or b['start'] > D0:
            continue
        co = company_obj(b)
        it = {'id': b['room'], 'guest': (co['name'] if co else b['guest']), 'bk': b['no'], 'nights': b['nights'],
              'rate': b['rate'], 'stage': b['stage'], 'viaLine': b['viaLine'], 'paid': b['paid'],
              'paidToday': False, 'phone': b['phone'], 'ch': b['ch'], 'pax': b['pax'], 'note': b['note'],
              'adults': b['adults'], 'kids': 0, 'email': b['email'],
              'taxTxt': ('ต้องการ · ' + b['tax']['name']) if b['tax'] else 'ไม่ต้องการ',
              'madeAtMs': b['madeAt'], 'leadD': b['lead']}
        if b['stage'] == 'stay':
            it['left'] = b['end'] - D0
        if b['ci']:
            it['ci'] = True
        if co:
            it['gname'] = b['guest']
            it['payer'] = co['payer']
            it['org'] = {'name': co['name'], 'tax': co['tax'], 'contact': co['contact']['name'] or b['guest'], 'cphone': co['contact']['phone'] or b['phone'],
                         'po': co['po'], 'payer': co['payer'], 'terms': co['terms'], 'credDays': co['credDays']}
            if co['terms'] == 'credit':
                it['credit'] = {'days': co['credDays'], 'po': co['po']}
        cards.append(it)
    return cards

def patch(h):
    cards = home_cards()
    byroom = {}
    ENR, XT, CONAME = {}, {}, {}
    for b in BK:
        if not b['stage'] or (b['stage'] == 'outdone' and not out_today(b)) or b['start'] > D0:
            continue
        r = b['room']
        ENR[r] = {'line': b['line'], 'on': True, 'mem': b['mem'], 'grp': b['grp'], 'v': b['visits'], 'dep': {'held': 'held', 'unpaid': 'unpaid', 'refunded': 'refunded'}.get(b['dep'], 'unpaid')}
        if b['cid'] in CO:
            CONAME[r] = b['cshort']
        co = company_obj(b)
        XT[b['no']] = {'room': r, 'guest': (co['name'] if co else b['guest']), 'nights': b['nights'], 'stage': b['stage'], 'viaLine': b['viaLine'],
                       'left': (b['end'] - D0) if b['stage'] == 'stay' else 0, 'phone': b['phone'], 'ch': b['ch'], 'pax': b['pax'], 'note': b['note'],
                       'line': b['line'], 'on': True, 'mem': b['mem'], 'grp': b['grp'], 'v': b['visits'], 'dep': ENR[r]['dep'],
                       'lead': b['lead'], 'hm': b['hm'], 'purpose': b['purpose']}
    # --- B ---
    i = h.index('let B = ['); j = h.index('let tasks = [')
    h = h[:i] + 'let B = ' + J(cards) + ';\n' + h[j:]
    # --- tasks ---
    i = h.index('let tasks = ['); j = h.index('const DEP = 200;')
    tasks = [{'t': 'เตรียมห้อง C11 C12 ให้พร้อมก่อน 11:00 (ครอบครัวขอเช็คอินก่อนเวลา) และ C13 ก่อนบ่ายนี้', 'done': False},
             {'t': 'ออกใบแจ้งหนี้รวม Valmet ห้อง A04–A05 ตอนเช็คเอาท์ (เครดิต 30 วัน)', 'done': False},
             {'t': 'เก็บค่าห้องต่อ 1 คืนของห้อง B01 ตอนเช็คเอาท์ แล้วออกใบกำกับภาษี ไบโอเทค', 'done': False},
             {'t': 'ตอบแชท LINE OA ที่ยังค้างอยู่', 'done': False}]
    h = h[:i] + 'let tasks = ' + J(tasks) + ';\n\n' + h[j:]
    h = R(h, 'const DEP = 200;', 'const DEP = 300;', 1, 'home-dep')
    # --- CONAME / ENR / XT ---
    i = h.index('const CONAME={'); j = h.index('const coOf=')
    h = h[:i] + 'const CONAME=' + J(CONAME) + ';\n' + h[j:]
    i = h.index('const ENR = {'); j = h.index('const XT={')
    h = h[:i] + 'const ENR = ' + J(ENR) + ';\n' + h[j:]
    i = h.index('const XT={'); j = h.index('const ROOMTYPE=')
    h = h[:i] + 'const XT=' + J(XT) + ';\n' + h[j:]
    i = h.index('const ROOMTYPE='); j = h.index('const esc = s =>')
    rt = {r['code']: r['type'] for r in ROOMS}
    h = h[:i] + 'const ROOMTYPE=id=>(' + J(rt) + ')[id]||"";\nconst ZNAME=id=>id[0]===\'A\'?\'โซนตึก\':\'โซนบ้าน\';\n' + h[j:]
    h = R(h, "B.forEach(b=>{if(b.id==='A003')b.lateMin=12;const e=ENR[b.id]||{};", "B.forEach(b=>{const e=ENR[b.id]||{};", 1, 'home-late')
    # ห้อง และ FUT
    i = h.index('const ROOMS = [...Array(16)]'); j = h.index('function span(x)')
    # FUT จากการจองล่วงหน้า (ไม่รวมใบที่อยู่บนหน้าแรกแล้ว)
    onhome = set(c['bk'] for c in cards)
    FUT = {}
    for b in BK:
        if b['no'] in onhome or b['stage'] == 'outdone':
            continue
        so = b['start'] - D0
        if so + b['nights'] <= 0:
            continue
        FUT.setdefault(b['room'], []).append([so, so + b['nights']])
    rooms_js = 'const ROOMS = ' + J([{'id': r['code'], 'rate': r['rate']} for r in ROOMS]) + ';\n'
    h = h[:i] + rooms_js + 'const FUT = ' + J(FUT) + ';   // การจองล่วงหน้า (ช่วงคืน [จาก,ถึง) นับจากวันนี้)\n' + h[j:]
    # FREE (ไม่ได้ใช้งานจริง) เป็นค่าว่าง
    h = R(h, "const FREE = {A005:0, A006:1};", "const FREE = {};", 1, 'home-free')
    # สถานะทำความสะอาดห้องที่แขกจะมา
    h = R(h, "const CLN={A011:1,B001:2};", "const CLN={C11:2,C12:1,C13:1};", 1, 'home-cln')
    h = R(h, "(b.svcRemain||0)+(b.extraDue||0)+(b.paid?0:RT(b)); if(sv>0&&b.stage==='out')", "(b.svcRemain||0)+(b.extraDue||0)+((b.paid||b.credit)?0:RT(b)); if(sv>0&&b.stage==='out')", 1, 'home-credit-out')
    h = R(h, "out:()=>[['รอเช็คเอาท์','b5']],", "out:b=>b&&b.credit?[['รอเช็คเอาท์','b5'],['เครดิต · รอเบิกจ่าย','b6']]:[['รอเช็คเอาท์','b5']],", 1, 'home-credit-badge')
    h = R(h, "function renderTasks(){\n", "var CRMN={leads:[],cos:[]};\nfunction crmRows(){const r=(k,lab,x)=>`<div class=\"task urgent crmn\"><span class=\"ub\" aria-hidden=\"true\" style=\"background:var(--purple);font-size:.62rem\">${lab}</span><p><b>${x.name}</b><small>เครื่องมือ CRM · ${x.d||'ยังไม่ได้ดู'}</small></p><button class=\"btn sm\" data-crmgo=\"1\">เปิดดู</button></div>`;return CRMN.leads.map(x=>r('l','ลีดใหม่',x)).join('')+CRMN.cos.map(x=>r('c','บริษัทใหม่',x)).join('')}\ndocument.addEventListener('click',e=>{if(e.target.closest('[data-crmgo]'))try{parent.postMessage({pbr:'goto',sub:'crmtool:main'},'*')}catch(_){}});\nfunction renderTasks(){\n", 1, 'home-crmrows')
    h = R(h, "$('taskList').innerHTML = (typeof repairRows==='function'?repairRows():'') +", "$('taskList').innerHTML = crmRows() + (typeof repairRows==='function'?repairRows():'') +", 1, 'home-crmrows2')
    h = R(h, "nr=(RPR?RPR.length:0),nrl=", "nc=CRMN.leads.length+CRMN.cos.length,nr=(RPR?RPR.length:0),nrl=", 1, 'home-nc')
    h = R(h, "left=tasks.filter(k=>!k.done).length+nrl;", "left=tasks.filter(k=>!k.done).length+nrl+nc;", 1, 'home-nc2')
    h = R(h, "(tasks.length||nr) ? `เหลือ ${left} จาก ${tasks.length+nr} งาน${nr?` · ซ่อม ${nr}`:''}` : ''", "(tasks.length||nr||nc) ? `เหลือ ${left} จาก ${tasks.length+nr+nc} งาน${nr?` · ซ่อม ${nr}`:''}${nc?` · CRM ${nc}`:''}` : ''", 1, 'home-nc3')
    h = R(h, "function onPub(k,v){\n", "function onPub(k,v){\n if(k==='crmnew'){CRMN={leads:v.leads||[],cos:v.cos||[]};try{renderTasks()}catch(e){console.error(e)}}\n", 1, 'home-crmpub')
    return h
