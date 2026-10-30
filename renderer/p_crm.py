# -*- coding: utf-8 -*-
import json, re, collections
from patch_all import R, J
from nb import *
from p_cust import _svc_of
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
                   int(b['hm'][:2]), pu, 1 if b['cid'] in CO else 0, 1 if b['taxReq'] else 0, b['total'], _svc_of(b['no'], b['room'])[0]])
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


def build_funnel():
    """เส้นทางลูกค้า (กล่อง "การจอง" ในแดชบอร์ด): [ดัชนีแขก, วันที่ทักครั้งแรก, จองไหม, เข้าพักจริงไหม, กลับมาซ้ำไหม] ต่อแชท LINE ที่ผูกกับแขก"""
    by = collections.defaultdict(list)
    for b in BK + BC:
        by[b['gid']].append(b)
    out, seen = [], set()
    for t in m.get('line_chats') or []:
        gid = t.get('guest_id')
        if gid not in GIDX or gid in seen:
            continue
        cm = [x['at'] for x in t.get('messages') or [] if x.get('from') == 'ลูกค้า']
        if not cm:
            continue
        seen.add(gid)
        d0 = dno(min(cm))
        bs = by.get(gid, [])
        booked = any(b['madeAt'] // 86400000 >= d0 - 1 for b in bs if b.get('madeAt'))
        stays = [b for b in bs if b['stage'] in ('now', 'outdone') or b['ci']]
        st = bool(booked and stays)   # นับเป็นกลุ่มเดียวกันทุกขั้น (ขั้นหลังต้องผ่านขั้นก่อน)
        out.append([GIDX[gid], d0 - BASE, 1 if booked else 0, 1 if st else 0, 1 if st and len([b for b in bs if b['stage'] is not None]) >= 2 else 0])
    return out

FUN_JS = r"""
  // เส้นทางลูกค้า: ทักมา → จอง → เข้าพักจริง → กลับมาซ้ำ (นับจากคนที่ทักทาง LINE ในช่วงที่เลือก · เป็นกลุ่มคนเดียวกัน)
  const funnel=(a,b)=>{const F=FUN.filter(x=>x[1]>=a&&x[1]<=b);const n0=F.length;
    if(!n0)return `<div class="blk"><h3>เส้นทางลูกค้า</h3><p class="hl">ยังไม่มีคนทักมาทาง LINE ในช่วงนี้</p></div>`;
    const c=[n0,F.filter(x=>x[2]).length,F.filter(x=>x[3]).length,F.filter(x=>x[4]).length],L=['ทักมา','จอง','เข้าพักจริง','กลับมาซ้ำ'],N=['ทักทาง LINE','มีการจอง','เข้าพักจริง','พักตั้งแต่ 2 ครั้งขึ้นไป'];
    const dr=c.map((v,i)=>i&&c[i-1]?(1-v/c[i-1])*100:0);let wi=1;dr.forEach((v,i)=>{if(i&&v>dr[wi])wi=i});
    return `<div class="blk fnl"><h3>เส้นทางลูกค้า</h3><p class="hl">จากทักมาจนกลับมาพักซ้ำ ตรงไหนที่ลูกค้าหายไป · นับจากคนที่ทักมาในช่วงที่เลือก</p>
     ${c.map((v,i)=>`<div class="fst"><span>${L[i]}</span><div class="ftr${i===wi&&dr[i]>0?' bad':''}"><i style="width:${v/n0*100}%"></i></div><b>${(v/n0*100).toFixed(0)}%</b></div>
      <div class="fdr">${fmt(v)} คน${i&&dr[i]>0?` · หายไประหว่างทาง <em>−${dr[i].toFixed(0)}%</em>`:''}</div>`).join('')}
     ${dr[wi]>0?`<div class="fnote"><b>ตรงที่หายเยอะที่สุด:</b> จาก${L[wi-1]}ไป${L[wi]} (หาย ${dr[wi].toFixed(0)}%)</div>`:''}
     <p class="fms">ระบบนับจากคนที่ทักมาทาง LINE การจอง การเข้าพัก และการกลับมาซ้ำ · ยังไม่มีข้อมูลคนที่ "เห็นเรา" (เปิดดูเพจ/แผนที่) จึงเริ่มนับตั้งแต่ทักมา</p></div>`};
"""
FUN_CSS = """.fnl .fst{display:grid;grid-template-columns:6.2rem 1fr 3.4rem;gap:.6rem;align-items:center;margin:.5rem 0 0}.fnl .fst span{font-size:.88rem;font-weight:600}
.fnl .ftr{height:1.3rem;border-radius:8px;background:var(--grid)}.fnl .ftr i{display:block;height:100%;border-radius:8px;background:linear-gradient(90deg,var(--t5),var(--brand))}.fnl .ftr.bad i{background:linear-gradient(90deg,#E0762F,var(--accent))}
.fnl .fst b{text-align:right;font-family:var(--serif);font-size:1rem}.fnl .fdr{margin:0 0 0 6.8rem;font-size:.76rem;color:var(--mute)}.fnl .fdr em{font-style:normal;font-weight:700;color:var(--accent)}
.fnl .fnote{background:var(--rose-t);border-radius:12px;padding:.5rem .8rem;font-size:.85rem;margin-top:.7rem}.fnl .fms{font-size:.74rem;color:var(--mute);margin:.6rem 0 0}
@media(max-width:560px){.fnl .fst{grid-template-columns:4.6rem 1fr 3rem}.fnl .fdr{margin-left:5.2rem}}
"""

def lit(s):
    return json.dumps(s, ensure_ascii=False).replace('</', '<\\/')

def regen_embedded(s, ovp):
    a = s.index('const RAW=') + 10
    _, e = json.JSONDecoder().raw_decode(s[a:])
    s = s[:a] + J(build_raw()) + s[a + e:]
    s = R(s, "ค่าห้อง และค่าอาหาร · รวม", "ค่าห้อง และค่าอาหาร/บริการเสริม · รวม", 1, 'emb-fd1')
    s = R(s, "['ค่าห้อง','ค่าอาหาร']", "['ค่าห้อง','อาหาร/บริการเสริม']", 1, 'emb-fd2')
    s = R(s, 'const D0=new Date(2024,0,1);', 'const D0=new Date(2026,0,1);', 1, 'emb-d0')
    s = R(s, '(c.getFullYear()-2024)*12', '(c.getFullYear()-2026)*12', 1, 'emb-mi')
    s = s.replace('min="2024-01-01" max="2025-12-31"', 'min="2026-01-01" max="2027-12-31"')
    # ลูกค้าที่ยังไม่มีจังหวัด: ไม่ทำเป็นแท่งกราฟ แสดงเป็นตัวเลขเล็กๆ มุมขวาล่างของกล่อง
    s = R(s, "const prov={},provP={};P.gs.forEach(g=>prov[GU[g].p]=(prov[GU[g].p]||0)+1);Q.gs.forEach(g=>provP[GU[g].p]=(provP[GU[g].p]||0)+1);",
          "const prov={},provP={};P.gs.forEach(g=>prov[GU[g].p]=(prov[GU[g].p]||0)+1);Q.gs.forEach(g=>provP[GU[g].p]=(provP[GU[g].p]||0)+1);const pvN=prov['']||0;", 1, 'emb-prov')
    s = R(s, "const provR=Object.entries(prov).sort(", "const provR=Object.entries(prov).filter(([l])=>l!=='').sort(", 1, 'emb-prov2')
    s = R(s, "${hbars(provR,'คน')}</div>", "${hbars(provR,'คน')}${pvN?`<p class=\"note\" style=\"text-align:right;font-size:.72rem;margin:.5rem 0 0\">ไม่ระบุจังหวัด ${fmt(pvN)} คน</p>`:''}</div>", 1, 'emb-prov3')
    if ovp:   # ป้ายกล่อง "สถานการณ์ลูกค้าตอนนี้": บอกตามจริงว่า AI วิเคราะห์ข้อมูลจากฐานข้อมูลแล้วหรือยัง
        s = R(s, "'<span class=\"o\">AI สรุปและแนะนำ</span><span class=\"o mk\">ข้อมูลจำลอง</span>'",
              "(window.__AISUM&&window.__AISUM.length?'<span class=\"o\">AI สรุปและแนะนำ</span><span class=\"o\">วิเคราะห์จากฐานข้อมูลจริง</span>':'<span class=\"o\">AI สรุปและแนะนำ</span><span class=\"o mk\">ข้อมูลจำลอง</span>')", 1, 'emb-sumbadge')
    if "box('occa'" in s:   # กล่อง "การจอง" ในแดชบอร์ด: เพิ่มเส้นทางลูกค้า (ส่วนเดิมไม่แตะ)
        s = R(s, "  // occasions\n", "  // occasions\n" + FUN_JS, 1, 'emb-fun1')
        s = R(s, "cnt(S,s=>lb(s.ld),6),hasP?cnt(R,s=>lb(s.ld),6):null,null,'pu')}</div>`,",
              "cnt(S,s=>lb(s.ld),6),hasP?cnt(R,s=>lb(s.ld),6):null,null,'pu')}</div>${funnel(P.a,P.b)}`,", 1, 'emb-fun2')
        assert '<style>' in s; s = s.replace('<style>', '<style>' + FUN_CSS, 1)
        s = R(s, "const D0=new Date(2026,0,1);", "const FUN=" + J(build_funnel()) + ";const D0=new Date(2026,0,1);", 1, 'emb-fun4')
    if ovp:   # ป๊อปอัปกลุ่มลูกค้าแบบเส้นทางลูกค้า (ข้อมูลจริงจาก p_seg · AI เล่าตัวตนผ่าน /api/segment)
        import p_seg, os
        pop = open(os.path.join(os.path.dirname(__file__), 'seg_popup.html'), encoding='utf-8').read()
        pop = pop.replace('__SEGX__', J(p_seg.build()).replace('</', '<\\/'))
        k = s.rindex('</body>')
        s = s[:k] + pop + s[k:]
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
