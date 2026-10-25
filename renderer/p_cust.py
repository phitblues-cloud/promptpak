# -*- coding: utf-8 -*-
from patch_all import R, J
from nb import *

def zone_th(r): return 'โซนตึก' if r['zone'] == 'A' else 'โซนบ้าน'

def bias_of(g):
    sg = g['segment']
    if sg.startswith('ทั่วไป-'): return sg.split('-', 1)[1]
    return 'ทำงาน'

def build_cu():
    mem_by = MEM
    first_made = {}
    for b in BK + BC:
        d = b['madeAt'] // 86400000
        first_made[b['gid']] = min(first_made.get(b['gid'], 10**9), d)
    cu = []
    for g in m['guests']:
        gid = g['guest_id']
        mb = mem_by.get(gid)
        cid = g['company_id'] if g['company_id'] in CO else ''
        cu.append({'id': gid, 'name': disp(g), 'phone': g['phone'], 'line': g['line_display_name'] or '',
                   'addr': clean_addr(g['address']), 'prov': g['home_province'] or '', 'company': cid,
                   'special': g.get('preferences_note') or '',
                   'memberNo': mb['member_id'] if mb else '', 'memberSince': dno(mb['joined_at']) if mb else None,
                   'added': first_made.get(gid, D0), 'bias': bias_of(g),
                   'bday': g['birth_date'], 'nid': re.sub(r'\D', '', g['id_card_no'] or ''), 'email': g['email'],
                   'gender': ''})
    # ข้อมูลที่พนักงานแก้/สมัครในโมดูลลูกค้า (ตาราง cust_state)
    cs = m.get('cust_state') or {}
    byid = {c['id']: c for c in cu}
    for gid, d in cs.items():
        c = byid.get(gid)
        if not c:
            if not d.get('is_new'):
                continue
            c = {'id': gid, 'name': '', 'phone': '', 'line': '', 'addr': '', 'prov': '', 'company': '', 'special': '',
                 'memberNo': '', 'memberSince': None, 'added': dno(d['added']) if d.get('added') else D0, 'bias': '',
                 'bday': '', 'nid': '', 'email': '', 'gender': ''}
            cu.append(c); byid[gid] = c
        for k in ('name', 'phone', 'line', 'addr', 'prov', 'bday', 'special', 'gender', 'purpose'):
            if k in d:
                c[k] = d[k]
        if 'company' in d:
            c['company'] = d['company'] if d['company'] in CO else ''
        if d.get('memberNo'):
            c['memberNo'] = d['memberNo']
            c['memberSince'] = dno(d['memberSince']) if d.get('memberSince') else D0
    # เอกสารยืนยันตัวตน: พนักงานเห็นเลขแบบปิดบางส่วน · ภาพบัตรโหลดตอนเจ้าของกดดูเท่านั้น
    owner = m.get('_role', 'owner') == 'owner'
    ids = m.get('cust_ids') or {}
    for c in cu:
        x = ids.get(c['id'])
        doc = {'t': x['t'], 'no': x['no'], 'img': bool(x.get('img')), 'ca': (x.get('ca') or '')[:10], 'cb': x.get('cb') or ''} if x else \
              ({'t': 'id', 'no': c['nid'], 'img': False, 'ca': '', 'cb': ''} if c.get('nid') else None)
        if doc:
            doc['mask'] = mask_doc(doc['t'], doc['no'])
            if not owner:
                doc['no'] = ''
        c['doc'] = doc
        c['nid'] = (doc['no'] if doc and doc['t'] == 'id' else '')
    return cu


def mask_doc(t, no):
    if t == 'id' and len(no) == 13:
        return f'{no[0]}-xxxx-xxxxx-xx-{no[12]}'
    return (no[:2] + 'x' * max(0, len(no) - 4) + no[-2:]) if len(no) > 4 else 'xxxx'

def build_co():
    co = []
    for c in m['companies']:
        ct = co_contact(c['company_id'])
        co.append({'id': c['company_id'], 'name': c['name_th'], 'tax': c['tax_id'], 'hq': c['billing_branch'],
                   'contact': ct['guest_id'] if ct else None, 'phone': ct['phone'] if ct else c.get('phone', ''), 'email': ct['email'] if ct else c.get('email', ''),
                   'addr': clean_addr(c['billing_address']), 'promos': []})
    return co

def build_st():
    return [{'no': b['no'], 'cust': b['gid'], 'room': b['room'], 'start': b['start'], 'nights': b['nights'], 'purpose': b['purpose'],
             'amount': b['total'], 'ch': b['ch'], 'madeAt': b['madeAt']} for b in BK]

def build_rev():
    return [{'src': r['source'], 'r': r['rating_5'], 'sent': r['sentiment'], 'topics': r['topics'], 'text': r['text'],
             'bk': r['booking_id'] or '', 'reply': r['reply_status'], 'at': r['created_at'][:10]} for r in REVIEWS]

def data_block():
    cu = build_cu()
    mseq = max([len(m['members'])] + [int(re.sub(r'\D', '', c['memberNo']) or 0) for c in cu if c['memberNo']])
    types = []
    for r in ROOMS:
        t = zone_th(r) + ' · ' + r['type']
        if t not in types: types.append(t)
    rtmap = {r['code']: zone_th(r) + ' · ' + r['type'] for r in ROOMS}
    s = ('/* ============ ข้อมูลจากชุด POBRAK_MOCK (อ้างอิง 24 ต.ค. 2569) ============ */\n'
         'const rtype=code=>(' + J(rtmap) + ')[code]||"";\n'
         'const RTLIST=' + J(types) + ';\n'
         'const PROMOS=[{id:\'p1\',name:\'ส่วนลดห้องพักพาร์ตเนอร์ 10%\',d:\'ทุกห้อง · ทุกวัน\',valid:\'1 ม.ค. – 31 ธ.ค. 2569\'},{id:\'p2\',name:\'พักวันธรรมดา ลด 15%\',d:\'จันทร์–พฤหัสบดี · จอง 3 ห้องขึ้นไป\',valid:\'1 ต.ค. 2569 – 31 มี.ค. 2570\'},{id:\'p3\',name:\'แถมอาหารเช้า 2 ที่\',d:\'ทุกการจอง · ต่อห้อง\',valid:\'20 ต.ค. – 30 พ.ย. 2569\'},{id:\'p4\',name:\'เรทพิเศษห้องประชุม ลด 20%\',d:\'จองล่วงหน้าอย่างน้อย 7 วัน\',valid:\'1 ม.ค. – 31 ธ.ค. 2569\'}];\n'
         'let CU=' + J(cu) + ',ST=' + J(build_st()) + ',CO=' + J(build_co()) + ',stSeq=1000,custSeq=0,memSeq=' + str(mseq) + ';\n'
         'const REV=' + J(build_rev()) + ';\n')
    return s

def patch(h):
    a = h.index('/* ============ ข้อมูลตัวอย่าง (สมมติทั้งหมด) ============ */')
    b_ = h.index('BKX.forEach(x=>ST.push(x));') + len('BKX.forEach(x=>ST.push(x));')
    h = h[:a] + data_block() + h[b_:]
    h = apply_common(h)
    return h

def apply_common(h):
    # เลขสมาชิก 3 หลัก (M001) ตามชุดข้อมูล
    h = h.replace("'M'+String(memSeq+1).padStart(4,'0')", "'M'+String(memSeq+1).padStart(3,'0')")
    h = h.replace("'M'+String(++memSeq).padStart(4,'0')", "'M'+String(++memSeq).padStart(3,'0')")
    PUS = "['ทำงาน','แวะพัก','งานบุญ','ราชการ/อบรม']"
    h = R(h, "[['all','ทั้งหมด'],['ทำงาน','ทำงาน'],['ท่องเที่ยว','ท่องเที่ยว'],['กิจกรรม','กิจกรรม']]", "[['all','ทั้งหมด'],['ทำงาน','ทำงาน'],['แวะพัก','แวะพัก'],['งานบุญ','งานบุญ'],['ราชการ/อบรม','ราชการ/อบรม']]", 1, 'cust-fpur')
    h = R(h, "['ทำงาน','ท่องเที่ยว','กิจกรรม'].map(x=>`<option", PUS + ".map(x=>`<option", 1, 'cust-rn7')
    h = R(h, "const PU=['ท่องเที่ยว','ทำงาน','กิจกรรม'];", "const PU=" + PUS + ";", 1, 'cust-PU')
    # ประเภทห้อง
    i = h.index("const RT=['โซนตึก · เตียงเดี่ยว'"); j = h.index("];", i) + 2
    h = h[:i] + "const RT=RTLIST;" + h[j:]
    return h

REVJS = r'''
function revStat(){const n=REV.length,avg=n?REV.reduce((a,r)=>a+r.r,0)/n:0;const pos=REV.filter(r=>r.sent==='บวก').length,neg=REV.filter(r=>r.sent==='ลบ').length;
  const tp={};REV.forEach(r=>r.topics.forEach(t=>{(tp[t]=tp[t]||[]).push(r.r)}));
  const tops=Object.entries(tp).sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0],'th')).slice(0,5);
  return {n,avg,pos,neg,mid:n-pos-neg,tops}}
'''

def analytics_fixes(h):
    n_cancel = sum(1 for b in BC if b.get('cancelled')); n_ns = sum(1 for b in BC if b.get('noshow'))
    # แหล่งข้อมูลรีวิว: เติมหลัง REV
    h = R(h, "const REV=", REVJS + "const REV=", 1, 'cust-revjs')
    # วัตถุประสงค์อื่นนอกจากทำงาน (ยังไม่ได้เก็บรายละเอียด)
    i = h.index("else if(p==='ท่องเที่ยว') body=")
    j = h.index("return `<details data-d=\"pu-${p}\"", i)
    h = h[:i] + "else body='<p class=\"cnote\">ฟอร์มจองยังไม่ได้เก็บรายละเอียดของวัตถุประสงค์นี้</p>';\n    " + h[j:]
    # มาพัก/ไม่มา/ยกเลิก
    tot = len(BK) + len(BC)
    def pc(x): return round(x * 100 / tot)
    h = R(h, "<h5>มาพัก / ไม่มา / ยกเลิก ${SAMP}</h5>\n     ${bars([['มาพัก',87,'87%'],['ยกเลิก',10,'10%'],['ไม่มา',3,'3%']])}\n     <p class=\"cnote\">ยังไม่มีเมนูยกเลิกการจอง/บันทึกไม่มาตามนัด</p></div>",
          f"<h5>มาพัก / ไม่มา / ยกเลิก</h5>\n     ${{bars([['มาพัก / จองไว้',{len(BK)},'{pc(len(BK))}%'],['ยกเลิก',{n_cancel},'{pc(n_cancel)}%'],['ไม่มา',{n_ns},'{pc(n_ns)}%']])}}\n     <p class=\"cnote\">นับทุกการจองในระบบ {tot} รายการ (ตั้งแต่ 20 ต.ค. 2569)</p></div>", 1, 'cust-outcome')
    # CSAT / VOC / ร้องเรียน
    a = h.index('<div class="cc s4"><h4>ความพึงพอใจ (CSAT) ${SAMP}</h4>'); b = h.index('<div class="cc s4"><h4>ลูกค้ากลับมาจองซ้ำ')
    csat = ('<div class="cc s4"><h4>ความพึงพอใจ (CSAT) ${sc_(\'จากรีวิวจริงในระบบ\')}</h4>${(()=>{const V=revStat();const g=new Set(ST.filter(s=>s.start<=TODAY).map(s=>s.cust)).size;'
            'return `<div class="cbig">${V.avg.toFixed(1)} <small>/ 5</small></div><p class="csub">รีวิว ${V.n} รายการ จากผู้เข้าพัก ${g} คน</p><h5>หัวข้อที่พูดถึง</h5>'
            '${V.tops.map(([t,a])=>`<div class="score"><span>${esc(t)}</span><b>${(a.reduce((x,y)=>x+y,0)/a.length).toFixed(1)}</b></div>`).join(\'\')}`})()}</div>\n\n   ')
    h = h[:a] + csat + h[b:]
    a = h.index('<div class="cc s4"><h4>เสียงลูกค้า (VOC) ${SAMP}</h4>'); b = h.index('<div class="cc s12"><h4>ข้อร้องเรียนและการติดตาม ${SAMP}</h4>')
    voc = ('<div class="cc s4"><h4>เสียงลูกค้า (VOC) ${sc_(\'จากรีวิวจริงในระบบ\')}</h4><p class="csub">LINE OA และ Google</p>${(()=>{const V=revStat();const pp=pct(V.pos,V.n),nn=pct(V.neg,V.n),mm=100-pp-nn;'
           'const best=REV.filter(r=>r.sent===\'บวก\').sort((x,y)=>y.r-x.r)[0],worst=REV.filter(r=>r.sent===\'ลบ\').sort((x,y)=>x.r-y.r)[0];'
           'return `<div class="donutrow" style="margin-top:.6rem"><div class="donut" style="background:conic-gradient(#3E8E6B 0 ${pp}%,#CDBFAE ${pp}% ${pp+mm}%,#B3263E ${pp+mm}% 100%)" role="img" aria-label="บวก ${pp} กลาง ${mm} ลบ ${nn}"></div>'
           '<div class="dl"><div><i style="background:#3E8E6B"></i>เชิงบวก ${pp}%</div><div><i style="background:#CDBFAE"></i>กลาง ${mm}%</div><div><i style="background:#B3263E"></i>เชิงลบ ${nn}%</div></div></div>'
           '<h5>หัวข้อที่พูดถึงบ่อย</h5>${bars(V.tops.map(([t,a])=>[t,a.length]))}'
           '${best?`<div class="quote"><b>${esc(best.src)} · ดาว ${best.r}</b><small>${esc(best.text)}</small></div>`:\'\'}${worst?`<div class="quote neg"><b>${esc(worst.src)} · ดาว ${worst.r}</b><small>${esc(worst.text)}</small></div>`:\'\'}`})()}</div>\n\n   ')
    h = h[:a] + voc + h[b:]
    a = h.index('<div class="cc s12"><h4>ข้อร้องเรียนและการติดตาม ${SAMP}</h4>'); b = h.index('\n  </div></div>`;', a)
    cmp_ = ('<div class="cc s12"><h4>รีวิวที่ควรติดตาม ${sc_(\'จากรีวิวจริงในระบบ\')}</h4>${(()=>{const L=REV.filter(r=>r.r<=3||r.reply!==\'ตอบแล้ว\');const nr=REV.filter(r=>r.reply!==\'ตอบแล้ว\').length,low=REV.filter(r=>r.r<=3).length;'
            'return `<div class="ckpis"><div><span class="csub">ดาว 3 หรือต่ำกว่า</span><b style="color:#B3263E">${low}</b></div><div><span class="csub">ยังไม่ตอบรีวิว</span><b>${nr}</b></div><div><span class="csub">รีวิวทั้งหมด</span><b>${REV.length}</b></div></div>'
            '<div class="ctw"><table><thead><tr><th>รีวิว</th><th>ช่องทาง</th><th>ดาว</th><th>การจอง</th><th>สถานะ</th></tr></thead><tbody>${REV.filter(r=>r.r<=3).map(r=>`<tr><td>${esc(r.text)}</td><td>${esc(r.src)}</td><td>${r.r}</td><td>${esc(r.bk||\'-\')}</td><td><span class="chip ${r.reply===\'ตอบแล้ว\'?\'ok\':\'red\'}">${esc(r.reply)}</span></td></tr>`).join(\'\')||\'<tr><td colspan="5">ไม่มี</td></tr>\'}</tbody></table></div>`})()}</div>')
    h = h[:a] + cmp_ + h[b:]
    h = R(h, "ตัวเลขที่ไม่มีป้าย คำนวณจากข้อมูลลูกค้า/การจองตัวอย่างในโมดูลนี้ · ป้าย ${SAMP} คือข้อมูลสมมติเพราะยังไม่มีแหล่งข้อมูล", "ตัวเลขทั้งหมดคำนวณจากข้อมูลลูกค้า การจอง และรีวิวในระบบ · หัวข้อที่ยังไม่มีแหล่งข้อมูลจะแสดงว่า \"ยังไม่มีข้อมูล\"", 1, 'cust-proto')
    return h

_old_patch = patch
def patch(h):
    h = _old_patch(h)
    return analytics_fixes(h)
