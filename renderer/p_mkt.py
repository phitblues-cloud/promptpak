# -*- coding: utf-8 -*-
import datetime, re
from patch_all import R, J
from nb import *
from p_crmtool import co_stats, th_from_dno

OCC = [d for d in m['daily_occupancy'] if '2026-10-13' <= d['date'] <= '2026-12-06']

def wd_avg(ix):
    v = [d['rooms_sold'] for d in OCC if datetime.date.fromisoformat(d['date']).weekday() in ix]
    return sum(v) / len(v)

WK, WE, SAT, SUN = wd_avg([0, 1, 2, 3]), wd_avg([4, 5]), wd_avg([5]), wd_avg([6])
pc = lambda a, b: round(a / b * 100) if b else 0
SUNVAC = 100 - pc(SUN, 31)

# ---------------- กลุ่มลูกค้า (คำนวณจากชุดข้อมูล) ----------------
GS = {g['guest_id']: g for g in m['guests']}
MEMS = {x['guest_id']: x for x in m['members']}

def group_ids(k):
    if k == 'g1': return [g['guest_id'] for g in m['guests'] if g['purpose_group'] in ('แวะพัก', 'งานบุญ')]
    if k == 'g3': return [g['guest_id'] for g in m['guests'] if g['company_id'] in CO and g['purpose_group'] == 'ทำงาน']
    if k == 'g4': return [g['guest_id'] for g in m['guests'] if g['purpose_group'] == 'ราชการ/อบรม']
    if k == 'g5': return [g['guest_id'] for g in m['guests'] if (g['bookings_total'] or 0) <= 1 and g['guest_id'] not in MEMS]
    return []

def seg_item(k, title, pos, why, dims):
    ids = set(group_ids(k))
    n = len(ids)
    line = len([i for i in ids if i in MEMS])
    cons = len([i for i in ids if i in MEMS and MEMS[i]['consent_marketing']])
    bs = [b for b in BK if b['gid'] in ids]
    spend = round(sum(b['total'] for b in bs) / len(bs)) if bs else 0
    days = [0] * 7
    for b in bs:
        for i in range(b['nights']):
            days[(b['start'] + i + 3) % 7] += 1
    mx = max(days) or 1
    d3 = [round(x / mx * 3) for x in days]
    we_share = sum(days[4:]) / (sum(days) or 1)
    return dict(id=k, t=title, n=n, u='คน', cons=cons, line=line, spend=f'฿{spend:,} ต่อครั้ง', tr=['flat', '—'], src='กลุ่มลูกค้า', tags=[],
                why=why, pos=pos, dims=dims, days=d3, we=we_share, bs=bs)

def score_of(it):
    size = max(1, min(5, round(it['n'] / 40 * 5 + .4)))
    avgs = [b['total'] for b in it['bs']]
    val = max(1, min(5, round((sum(avgs) / len(avgs) if avgs else 0) / 800 * 5)))
    con = max(1, min(5, round(it['cons'] / (it['n'] or 1) * 5))) if it['n'] else 1
    fit = max(1, min(5, round(1 + 4 * it['we'])))
    return [size, val, 3, con], [size, val, con, fit]

def build_seg():
    items = [
        seg_item('g1', 'ลูกค้าทั่วไป งานบุญ/แวะพัก', 'พักใกล้วัดและริมเขื่อน เงียบ จอดรถสะดวก ครอบครัวพักได้สบาย',
                 'ตัวเลขนับจากลูกค้าและประวัติเข้าพักจริงในระบบ', ['ลูกค้าบุคคลที่มาแวะพักหรือร่วมงานบุญ ไม่มีบริษัทต้นสังกัด']),
        seg_item('g3', 'คนทำงานจากบริษัท/หน่วยงาน', 'ใกล้โรงงานและเขื่อน ออกใบกำกับภาษีให้ทุกครั้ง ที่จอดรถตู้ได้',
                 'ตัวเลขนับจากลูกค้าและประวัติเข้าพักจริงในระบบ', ['ลูกค้าที่มาพักเพื่อทำงานและมีบริษัทต้นสังกัด']),
        seg_item('g4', 'ลูกค้าราชการ/อบรม', 'พักใกล้สถานที่อบรม ออกใบแจ้งหนี้ตามระเบียบเบิกจ่าย',
                 'ตัวเลขนับจากลูกค้าและประวัติเข้าพักจริงในระบบ', ['ลูกค้าที่มาอบรมหรือราชการ']),
        seg_item('g5', 'ลูกค้าที่พักครั้งเดียว ยังไม่เป็นสมาชิก', 'จองง่ายทาง LINE ราคาชัดเจน สมัครสมาชิกแล้วได้รับข้อมูลการพักทาง LINE',
                 'ตัวเลขนับจากลูกค้าและประวัติเข้าพักจริงในระบบ', ['มาพักครั้งเดียวและยังไม่ได้สมัครสมาชิก']),
    ]
    # บริษัท
    cs = [co_stats(c['company_id']) for c in m['companies']]
    cl = [c for c in m['company_contacts'] if c['guest_id'] and c['guest_id'] in MEMS]
    cbk = [b for b in BK if b['cid'] in CO]
    g2 = dict(id='g2', t='บริษัทและหน่วยงานลูกค้า', n=len(CO), u='บริษัท', cons=len({c['company_id'] for c in cl}), line=len({c['company_id'] for c in cl}),
              spend='฿%s ต่อบริษัท' % format(round(sum(c['spend'] for c in cs) / len(cs)), ','), tr=['flat', '—'], src='กลุ่มลูกค้า', tags=[],
              why='ตัวเลขนับจากลูกค้าและประวัติเข้าพักจริงในระบบ', pos='ใกล้โรงงานและเขื่อน ใบกำกับภาษีและใบแจ้งหนี้รวมให้ฝ่ายบัญชี ล็อกห้องล่วงหน้าให้ทีมได้',
              dims=['บริษัทและหน่วยงานที่เคยจองหรือมีการจองล่วงหน้า'], days=None, we=sum(1 for b in cbk if True) and (sum(b['nights'] for b in cbk if (b['start'] % 7) in (1, 2, 3)) / (sum(b['nights'] for b in cbk) or 1)), bs=cbk)
    days = [0] * 7
    for b in cbk:
        for i in range(b['nights']): days[(b['start'] + i + 3) % 7] += 1
    mx = max(days) or 1
    g2['days'] = [round(x / mx * 3) for x in days]
    g2['we'] = sum(days[4:]) / (sum(days) or 1)
    items.append(g2)
    for it in items:
        it['score'], it['sc'] = score_of(it)
    W = [20, 25, 20, 35]
    items.sort(key=lambda it: -sum(a * b / 100 for a, b in zip(it['sc'], W)))
    return items

def build_segments():
    stays = [(g['guest_id'], g['bookings_total'] or 0) for g in m['guests']]
    often = [i for i, n in stays if n >= 3]; rep = [i for i, n in stays if n == 2]; new = [i for i, n in stays if n <= 1]
    lnk = lambda ids: len([i for i in ids if i in MEMS])
    cl = len({c['company_id'] for c in m['company_contacts'] if c['guest_id'] in MEMS})
    return [dict(id='s1', n='บริษัทและหน่วยงานลูกค้า', c=len(CO), u='บริษัท', line=cl, email=len(CO), nights=3.4),
            dict(id='s2', n='ลูกค้ามาบ่อย', c=len(often), u='คน', line=lnk(often), email=0, nights=2.3),
            dict(id='s3', n='ลูกค้ามาซ้ำ', c=len(rep), u='คน', line=lnk(rep), email=0, nights=2.5),
            dict(id='s4', n='ลูกค้าใหม่ (ข้อมูลเริ่ม 13 ต.ค.)', c=len(new), u='คน', line=lnk(new), email=0, nights=2.0),
            dict(id='s5', n='ลูกค้าที่หายไป', c=0, u='คน', line=0, email=0, nights=2.0),
            dict(id='s6', n='คนทั่วไป (นอกฐานลูกค้า)', c=0, u='', line=0, email=0, nights=1.5)]

def seg_js():
    items = build_seg()
    out = []
    for it in items:
        out.append({k: it[k] for k in ['id', 't', 'n', 'u', 'cons', 'line', 'spend', 'tr', 'src', 'tags', 'why', 'pos', 'dims', 'score']})
    ids = [it['id'] for it in items]
    STPd = dict(days={it['id']: it['days'] for it in items},
                vals={'g1': ['เงียบ', 'ที่จอดรถ', 'ใกล้วัด'], 'g2': ['ใบกำกับภาษี', 'ใบแจ้งหนี้รวม', 'ล็อกห้องล่วงหน้า'], 'g3': ['ใกล้หน้างาน', 'ใบกำกับภาษี', 'ที่จอดรถตู้'],
                            'g4': ['ใบแจ้งหนี้หน่วยงาน', 'ใกล้สถานที่อบรม'], 'g5': ['ราคาชัด', 'จองง่ายทาง LINE']},
                who={'g1': 'ลูกค้าทั่วไป · งานบุญ/แวะพัก', 'g2': 'บริษัท/หน่วยงาน · ทำงานและอบรม', 'g3': 'คนทำงาน · มีบริษัทต้นสังกัด', 'g4': 'ราชการ/อบรม', 'g5': 'มาครั้งเดียว · ยังไม่เป็นสมาชิก'},
                sc={it['id']: it['sc'] for it in items},
                W=[['ขนาดและการเติบโต', 20], ['โอกาสทำกำไร', 25], ['ติดต่อได้', 20], ['ตรงกับคืนที่ห้องว่าง', 35]],
                change='ข้อมูลเริ่มเก็บตั้งแต่ 13 ต.ค. จึงยังไม่มีแนวโน้มเปรียบเทียบ · ห้องว่างส่วนใหญ่อยู่คืนศุกร์–อาทิตย์ (เข้าพักเฉลี่ย ศ.–ส. %d%% เทียบ จ.–พฤ. %d%%) กลุ่มที่มาสุดสัปดาห์จึงตรงกับห้องว่างมากที่สุด' % (pc(WE, 31), pc(WK, 31)),
                pos={'hotel': {'seg': 'ทีมช่าง วิศวกร และผู้ประสานงานบริษัทในพื้นที่อุบลรัตน์–น้ำพอง', 'need': 'ที่พักใกล้หน้างาน ออกเอกสารภาษีและเบิกจ่ายได้',
                               'what': 'ที่พักริมเขื่อนอุบลรัตน์', 'diff': 'ใกล้โรงงานและเขื่อน จ่ายง่าย ออกใบกำกับภาษีครบ', 'vs': 'ที่พักในตัวเมืองขอนแก่นที่ไกลจากหน้างาน',
                               'why': 'ห่างโรงงานไบโอเทค 4 กม. ห่างเขื่อน 9 กม. และมีเครดิตสำหรับบริษัท/หน่วยงาน'}},
                confirmed=False)
    return out, STPd

def hotel_items():
    prov = collections_Counter()
    return None

def patch(h):
    seg_items, STPd = seg_js()
    segs = build_segments()
    # ---------- ศูนย์ไอเดีย: โอกาสจากข้อมูลโรงแรม ----------
    kk = sum(1 for g in m['guests'] if g['home_province'] == 'ขอนแก่น')
    comp_share = pc(sum(sum(d['by_company'].values()) for d in OCC), sum(d['rooms_sold'] for d in OCC))
    line_share = pc(sum(1 for b in BK + BC if b['ch'] == 'LINE OA'), len(BK + BC))
    top_prov = ', '.join('%s %d' % (k, v) for k, v in __import__('collections').Counter(g['home_province'] for g in m['guests']).most_common(3))
    hotel = [
        {'id': 'h1', 't': 'ห้องว่างสุดสัปดาห์เฉลี่ย %d ห้องต่อคืน' % round(31 - WE), 'why': 'อัตราเข้าพัก ศ.–ส. %d%% เทียบ จ.–พฤ. %d%%' % (pc(WE, 31), pc(WK, 31)), 'src': 'จากข้อมูลการจอง',
         'tags': [['ผลต่อรายได้สูง', 'bad']], 'nums': ['อัตราเข้าพัก จ.–พฤ. %d%%' % pc(WK, 31), 'อัตราเข้าพัก ศ.–ส. %d%%' % pc(WE, 31), 'ห้องว่างสุดสัปดาห์เฉลี่ย %d จาก 31 ห้องต่อคืน' % round(31 - WE)], 'from': 'โมดูลจัดการการจอง · 13 ต.ค.–6 ธ.ค. 2569'},
        {'id': 'h2', 't': 'บริษัทและหน่วยงาน %d แห่งเป็นลูกค้าหลัก' % len(CO), 'why': 'ห้องที่ขายได้ %d%% มาจากบริษัท/หน่วยงาน' % comp_share, 'src': 'จาก CRM',
         'tags': [['ผลต่อรายได้สูง', 'bad'], ['มีรายชื่อติดต่อได้', 'good']], 'nums': ['บริษัทในระบบ %d แห่ง' % len(CO), 'ห้องคืนที่ขายได้จากบริษัท/หน่วยงาน %d%%' % comp_share, 'ข้อมูลเริ่ม 13 ต.ค. ยังไม่มีบริษัทที่ห่างหาย'], 'from': 'โมดูลลูกค้าและสมาชิก · ประวัติเข้าพักของบริษัท'},
        {'id': 'h3', 't': 'ลูกค้า %d%% มาจากนอกจังหวัด' % pc(40 - kk, 40), 'why': 'จังหวัดต้นทางมากที่สุด: ' + top_prov, 'src': 'จาก CRM',
         'tags': [['ข้อมูลเริ่ม 13 ต.ค.', 'good']], 'nums': ['ลูกค้าจังหวัดขอนแก่น %d จาก 40 คน' % kk, 'จังหวัดต้นทาง: ' + top_prov], 'from': 'โมดูลลูกค้าและสมาชิก · ที่อยู่และประวัติเข้าพัก'},
        {'id': 'h4', 't': 'จองผ่าน LINE OA %d%% ของการจองทั้งหมด' % line_share, 'why': 'ที่เหลือจองทางโทรศัพท์', 'src': 'จากข้อมูลการจอง',
         'tags': [['ช่องทาง', 'warn']], 'nums': ['จอง LINE OA %d%%' % line_share, 'ยังไม่มีข้อมูลการกลับมาซ้ำให้เทียบ (เริ่มเก็บ 13 ต.ค.)'], 'from': 'ช่องทางจองในรายการจองทั้งหมด'},
        {'id': 'h5', 't': 'คืนวันอาทิตย์ห้องว่าง %d%%' % SUNVAC, 'why': 'คืนวันเสาร์เข้าพัก %d%% ส่วนคืนวันอาทิตย์เข้าพัก %d%%' % (pc(SAT, 31), pc(SUN, 31)), 'src': 'จากข้อมูลการจอง',
         'tags': [['โอกาสใหม่', 'good']], 'nums': ['อัตราเข้าพักคืนวันอาทิตย์ %d%%' % pc(SUN, 31), 'คืนวันเสาร์ %d%%' % pc(SAT, 31)], 'from': 'โมดูลจัดการการจอง · 13 ต.ค.–6 ธ.ค. 2569'},
    ]
    i = h.index(' hotel:{items:['); j = h.index(' trend:{src:')
    h = h[:i] + ' hotel:{items:' + J(hotel) + '},\n' + h[j:]
    # ---------- งานในพื้นที่ (จากข้อมูล CRM) ----------
    local = [
        {'id': 'l1', 't': 'ทีม shutdown โรงงานฟินิคซ น้ำพอง ปลาย พ.ย.', 'd': 'อีก 30 วัน · Valmet 7 ห้อง และฟินิคซ 6 ห้อง จองไว้แล้ว', 'src': 'จาก CRM', 'tags': [['ห่าง 28 กม.', 'warn'], ['ดึงยอดจองได้ตรง', 'good']],
         'when': 'เริ่ม 23–24 พ.ย. · ห่างโรงแรม 28 กม.', 'sum': 'บริษัท Valmet (เครดิต 30 วัน) จอง 7 ห้อง 23 พ.ย.–5 ธ.ค. และฟินิคซจอง 6 ห้อง 24 พ.ย.–4 ธ.ค. สำหรับทีมซ่อมใหญ่ประจำปี',
         'why': 'ช่วงนี้ห้องแน่นวันธรรมดาอยู่แล้ว ควรล็อกห้องและเอกสารให้ทีมล่วงหน้า และเสนอบริษัทอื่นที่ทำงานในโรงงานเดียวกัน', 'links': []},
        {'id': 'l2', 't': 'ซ่อมบำรุงก่อนหีบอ้อย KSL น้ำพอง', 'd': 'ต.ค.–พ.ย. · ผู้รับเหมาจากส่วนกลางเข้าพื้นที่', 'src': 'จากการวิเคราะห์ CRM', 'tags': [['ห่าง 28 กม.', 'warn'], ['ยังไม่เคยพัก', 'good']],
         'when': 'ต.ค.–พ.ย. · เป้าหมายใหม่', 'sum': 'โรงงานน้ำตาลขอนแก่น น้ำพอง มีงานซ่อมบำรุงก่อนเปิดหีบอ้อย ผู้รับเหมาจากส่วนกลางจะเข้าพื้นที่ ยังไม่มีผู้ติดต่อในระบบ',
         'why': 'เป็นกลุ่มบริษัทใหม่ที่ตรงกับลูกค้าหลัก (ทีมช่างหน้างาน) ควรหาผู้ติดต่อฝ่ายจัดซื้อ/ผู้รับเหมาหลักก่อนเสนอราคาทีม', 'links': []},
        {'id': 'l3', 't': 'งานกฐินและงานบุญในอำเภออุบลรัตน์', 'd': 'ปลาย ต.ค.–พ.ย. · ครอบครัวพักสุดสัปดาห์', 'src': 'จากข้อมูลการจอง', 'tags': [['ในพื้นที่', 'good'], ['คืนสุดสัปดาห์', 'good']],
         'when': 'ปลาย ต.ค.–พ.ย. · ในอำเภอ', 'sum': 'มีครอบครัวจองห้องไปร่วมงานกฐิน 24–26 ต.ค. และลูกค้าทั่วไปงานบุญอีกหลายราย',
         'why': 'เป็นกลุ่มที่พักคืนสุดสัปดาห์ ซึ่งเป็นคืนที่ห้องว่างมากที่สุด', 'links': []},
    ]
    i = h.index(' local:{src:'); j = h.index('feeds.seg={')
    h = h[:i] + ' local:{src:"จากข้อมูลการจองและ CRM ของบริษัทลูกค้าในพื้นที่",items:' + J(local) + '}\n};\n\n' + h[j:]
    # ---------- กลุ่มลูกค้า / STP / segments ----------
    i = h.index('feeds.seg={'); j = h.index('const promos=[')
    new = ('feeds.seg={src:"จาก CRM และข้อมูลการจอง",items:' + J(seg_items) + '};\n'
           'const STP=' + J(STPd) + ';\n'
           'function stpScore(id){const v=STP.sc[id];return STP.W.reduce((a,[_,w],i)=>a+v[i]*w/100,0)}\n'
           "const SCORE_LBL=['ขนาด','มูลค่า','แนวโน้ม','ติดต่อได้'];\n"
           "const HOTEL_POS='ที่พักริมเขื่อนอุบลรัตน์ ใกล้โรงงานและเขื่อน จ่ายง่าย ออกใบกำกับภาษีให้ครบ';\n"
           'const segments=' + J(segs) + ';\n'
           "feeds.seg.items.forEach(g=>{segments.push({id:'S'+g.id,n:g.t,c:g.n,u:g.u,line:g.line,email:g.id==='g2'?g.n:0,nights:g.id==='g2'?3.4:2.2})});\n")
    h = h[:i] + new + h[j:]
    # โปรโมชัน
    i = h.index('const promos=['); j = h.index('\n', i)
    promos = [{'id': 'p0', 'n': 'ไม่มีโปรโมชัน', 'f': 1}, {'id': 'p1', 'n': 'แพ็กเกจทีมงานพักยาว', 's': 'ห้องพัก + อาหารเช้า สำหรับทีมพัก 5 คืนขึ้นไป', 'f': 1},
              {'id': 'p2', 'n': 'ส่วนลดสุดสัปดาห์ 20%', 's': 'เพดานที่เจ้าของตั้งไว้ (ศุกร์–อาทิตย์)', 'f': .8}, {'id': 'p3', 'n': 'พักคืนวันอาทิตย์ลด 30%', 's': 'ต่อจากคืนวันเสาร์', 'f': .7},
              {'id': 'p4', 'n': 'แถมอาหารเช้า', 's': 'มูลค่า 170 บาทต่อคน', 'f': 1}]
    h = h[:i] + 'const promos=' + J(promos) + ';' + h[j:]
    h = R(h, 'const PRICE=571; // ราคาเฉลี่ยถ่วงน้ำหนักตาม room mix (17,700 ÷ 31)', 'const PRICE=597; // ราคาเฉลี่ยตามราคาป้าย (18,500 ÷ 31 ห้อง)', 1, 'mkt-price')
    # แคมเปญ: ยังไม่มีประวัติ
    i = h.index('let campaigns=['); j = h.index('/* tabs */')
    h = h[:i] + 'let campaigns=[];\n\n\n' + h[j:]
    # ---------- hotelLive ----------
    h = R(h, 'for(let off=-90;off<0;off++)by[dowOf(off)].push(occN(off));', 'for(let off=-11;off<=43;off++)by[dowOf(off)].push(occN(off));', 1, 'mkt-occwin')
    a = h.index("const h1=get('h1');if(h1){"); b = h.index("const h5=get('h5')")
    h = h[:a] + ("const h1=get('h1');if(h1){const lowWe=we<wk;h1.t=lowWe?`ห้องว่างสุดสัปดาห์เฉลี่ย ${Math.round(ROOMS-we)} ห้องต่อคืน`:`ห้องว่างวันธรรมดาเฉลี่ย ${Math.round(ROOMS-wk)} ห้องต่อคืน`;"
                 "h1.why=`อัตราเข้าพัก จ.–พฤ. ${pc(wk,ROOMS)}% เทียบ ศ.–ส. ${pc(we,ROOMS)}%`;h1.nums=[`อัตราเข้าพัก จ.–พฤ. ${pc(wk,ROOMS)}%`,`อัตราเข้าพัก ศ.–ส. ${pc(we,ROOMS)}%`,`ห้องว่างเฉลี่ย ${Math.round(ROOMS-(lowWe?we:wk))} จาก ${ROOMS} ห้องต่อคืน`];h1.from='โมดูลจัดการการจอง · 13 ต.ค.–6 ธ.ค. 2569'}\n ") + h[b:]
    h = R(h, "h5.nums=[`อัตราเข้าพักคืนวันอาทิตย์ ${pc(sun,ROOMS)}%`,`คืนวันเสาร์ ${pc(sat,ROOMS)}%`];h5.from='โมดูลจัดการการจอง · 90 วันล่าสุด'", "h5.nums=[`อัตราเข้าพักคืนวันอาทิตย์ ${pc(sun,ROOMS)}%`,`คืนวันเสาร์ ${pc(sat,ROOMS)}%`];h5.from='โมดูลจัดการการจอง · 13 ต.ค.–6 ธ.ค. 2569'", 1, 'mkt-h5')
    h = R(h, "const lapsed=(r.comp||[]).filter(k=>k.last!=null&&k.last>180),sp=lapsed.reduce((a,k)=>a+k.spend,0);", "const lapsed=(r.comp||[]).filter(k=>k.last!=null&&k.last>180),sp=lapsed.reduce((a,k)=>a+k.spend,0),allSp=(r.comp||[]).reduce((a,k)=>a+(k.spend||0),0);", 1, 'mkt-lapsed')
    h = R(h, "h2.t=lapsed.length?`บริษัท ${lapsed.length} แห่งไม่กลับมาเกิน 6 เดือน`:'บริษัทพาร์ตเนอร์ทุกแห่งยังมาพักภายใน 6 เดือน';h2.why=lapsed.length?`เคยใช้จ่ายรวม ${baht(sp)} · ${lapsed.map(k=>k.name).join(', ')}`:`ติดตามต่อ: ${(r.comp||[]).length} บริษัทในระบบ`;",
          "h2.t=lapsed.length?`บริษัท ${lapsed.length} แห่งไม่กลับมาเกิน 6 เดือน`:`บริษัทและหน่วยงาน ${(r.comp||[]).length} แห่งเป็นลูกค้าหลัก`;h2.why=lapsed.length?`เคยใช้จ่ายรวม ${baht(sp)} · ${lapsed.map(k=>k.name).join(', ')}`:`ใช้จ่ายรวมแล้ว ${baht(allSp)} · ข้อมูลเริ่ม 13 ต.ค. ยังไม่มีบริษัทที่ห่างหาย`;", 1, 'mkt-h2')
    h = R(h, "`พักเฉลี่ย ${avgN.toFixed(1)} คืน และ ${pc(satSt,st.length)}% พักคืนวันเสาร์`", "`พักเฉลี่ย ${avgN.toFixed(1)} คืน และ ${pc(satSt,st.length)}% พักคืนวันเสาร์`", 1, 'mkt-h3chk')
    h = R(h, "h3.t=`ลูกค้า ${pc(kk,n)}% มาจากขอนแก่นเอง`;", "h3.t=kk*2>=n?`ลูกค้า ${pc(kk,n)}% มาจากขอนแก่นเอง`:`ลูกค้า ${pc(n-kk,n)}% มาจากนอกจังหวัด`;", 1, 'mkt-h3')
    h = R(h, "h4.t=`จองครั้งแรกผ่าน LINE กลับมาซ้ำ ${pc(lR,lN)}% เทียบช่องทางอื่น ${pc(oR,oN)}%`;h4.why=`ลูกค้า ${pc(oN,all)}% จองครั้งแรกทางโทรศัพท์หรือ Walk-in`;",
          "h4.t=`ลูกค้า ${pc(lN,all)}% จองครั้งแรกผ่าน LINE`;h4.why=`ลูกค้า ${pc(oN,all)}% จองครั้งแรกทางโทรศัพท์หรือ Walk-in · กลับมาซ้ำ LINE ${pc(lR,lN)}% / ช่องทางอื่น ${pc(oR,oN)}% (ข้อมูลเริ่ม 13 ต.ค.)`;", 1, 'mkt-h4')
    # ---------- กลุ่มลูกค้าเฉพาะ (audience) ----------
    h = R(h, "Sg1:{pv:['ขอนแก่น'],pu:['ท่องเที่ยว','กิจกรรม'],wd:['we']},Sg3:{pu:['ทำงาน'],co:'no'},Sg4:{pv,pu:['ท่องเที่ยว']},Sg5:{vMax:'1',ln:'no'}}}",
          "Sg1:{pu:['แวะพัก','งานบุญ']},Sg3:{pu:['ทำงาน'],co:'yes'},Sg4:{pu:['ราชการ/อบรม']},Sg5:{vMax:'1',mem:'0'}}}", 1, 'mkt-audpre')
    h = R(h, "chips('pu',['ทำงาน','ท่องเที่ยว','กิจกรรม'])", "chips('pu',['ทำงาน','แวะพัก','งานบุญ','ราชการ/อบรม'])", 1, 'mkt-chips')
    h = R(h, "const lap=(R.comp||[]).filter(k=>k.last!=null&&k.last>270),s1=sg('s1');", "const lap=(R.comp||[]),s1=sg('s1');", 1, 'mkt-lap')
    a = h.index("const T={g1:['ลูกค้าจากขอนแก่น"); b = h.index("\n", a)
    h = h[:a] + ("const T={g1:['ลูกค้าทั่วไป งานบุญ/แวะพัก','ลูกค้าบุคคลที่มาแวะพักหรือร่วมงานบุญ ไม่มีบริษัทต้นสังกัด'],g3:['คนทำงานจากบริษัท/หน่วยงาน','ลูกค้าที่มาพักเพื่อทำงานและมีบริษัทต้นสังกัด'],g4:['ลูกค้าราชการ/อบรม','ลูกค้าที่มาอบรมหรือราชการ'],g5:['ลูกค้าที่พักครั้งเดียว ยังไม่เป็นสมาชิก','มาพักครั้งเดียวและยังไม่ได้สมัครสมาชิก']};") + h[b:]
    h = R(h, "if(g2){g2.n=lap.length;g2.u='บริษัท';", "if(g2){g2.t='บริษัทและหน่วยงานลูกค้า';g2.n=lap.length;g2.u='บริษัท';", 1, 'mkt-g2')
    h = R(h, "const s1=sg('s1');if(s1){s1.c=lap.length;", "const s1=sg('s1');if(s1){s1.n='บริษัทและหน่วยงานลูกค้า';s1.c=lap.length;", 0, 'mkt-s1chk') if False else h
    # ---------- แผน AI (menus) ----------
    a = h.index("function buildMenus(){"); b = h.index("function applySeg(list)")
    menus = r"""function buildMenus(){const ids=[...selected.keys()];
 if(ids.includes('t3'))return 'risk';
 if(ids.some(i=>['h1','h2','l1','l2','g2','g3'].includes(i)))return[
  {name:'ล็อกห้องล่วงหน้าให้ทีมงานช่วง shutdown ปลาย พ.ย.',rec:1,why:'บริษัทลูกค้ามีงานซ่อมใหญ่ปลายเดือน พ.ย. และมีผู้ติดต่อใน LINE อยู่แล้ว ใช้เงินน้อยที่สุด',goal:'ขายห้องล่วงหน้าช่วงปลาย พ.ย.–ธ.ค.',seg:['s1'],ch:['line'],promo:'p1',tools:['promo','msg','send'],level:'ง่าย'},
  {name:'ชวนลูกค้าเดิมอยู่ต่อสุดสัปดาห์',why:'ห้องว่างสุดสัปดาห์มากกว่าวันทำงานมาก แต่ส่วนลดกินกำไร 20%',goal:'เติมห้องว่าง ศ.–อา.',seg:['s3'],ch:['line'],promo:'p2',tools:['promo','msg','img','send'],level:'ปานกลาง'},
  {name:'โพสต์ที่พักริมเขื่อนสุดสัปดาห์',why:'เข้าถึงคนใหม่ แต่วัดผลยากและผลช้ากว่า',goal:'ให้คนใหม่รู้จักโรงแรมในช่วงสุดสัปดาห์',seg:['s6'],ch:['fb'],promo:'p0',tools:['msg','img'],level:'ง่าย'}];
 if(ids.some(i=>['l3'].includes(i)))return[
  {name:'แพ็กเกจครอบครัวไปงานบุญ พร้อมอาหารเช้า',rec:1,why:'ผู้ร่วมงานบุญต้องหาที่พักใกล้วัด และพักคืนสุดสัปดาห์ซึ่งเป็นคืนที่ห้องว่างมากที่สุด',goal:'ขายห้องคืนสุดสัปดาห์ช่วงงานบุญ',seg:['s6'],ch:['fb'],promo:'p4',tools:['promo','msg','img'],level:'ง่าย'},
  {name:'ชวนลูกค้าเดิมพาครอบครัวมาพักสุดสัปดาห์',why:'ลูกค้าเดิมตอบรับดีกว่า แต่จำนวนที่มีครอบครัวในพื้นที่ไม่แน่นอน',goal:'ขายห้องสุดสัปดาห์',seg:['s3','s2'],ch:['line'],promo:'p4',tools:['promo','msg','send'],level:'ง่าย'}];
 return[
  {name:'อยู่ต่ออีกคืนวันอาทิตย์',rec:1,why:'ลูกค้าวันเสาร์มีอยู่แล้ว แค่ชวนอยู่ต่อ ใช้ห้องที่ว่างอยู่ '+SUNVAC_PLACEHOLDER+'%',goal:'เติมคืนวันอาทิตย์',seg:['s3','s2'],ch:['line'],promo:'p3',tools:['promo','msg','send'],level:'ง่าย'},
  {name:'ชวนครอบครัวทีมงานมาเที่ยวสุดสัปดาห์',why:'ลูกค้าส่วนใหญ่เป็นคนทำงานจากต่างจังหวัดที่ห้องว่างสุดสัปดาห์ ชวนครอบครัวมาพักต่อ',goal:'ดึงครอบครัวมาพักสุดสัปดาห์',seg:['s4'],ch:['line','fb'],promo:'p4',tools:['promo','msg','img','send'],level:'ปานกลาง'},
  {name:'โพสต์ภาพวิวเขื่อนยามเย็น',why:'ไม่มีต้นทุนโปรโมชัน แต่ผลช้าและวัดยาก',goal:'ให้คนรู้จักโรงแรมมากขึ้น',seg:['s6'],ch:['fb'],promo:'p0',tools:['msg','img'],level:'ง่าย'}];
}
""".replace('SUNVAC_PLACEHOLDER', str(SUNVAC))
    h = h[:a] + menus + h[b:]
    h = R(h, "ติดต่อทาง LINE ได้ 71 คน'", "ติดต่อทาง LINE ได้ '+segments.find(x=>x.id==='s4').line+' คน'", 1, 'mkt-s4line')
    h = R(h, "why:'ลูกค้าที่มาครั้งแรกในปีนี้ยังไม่กลับมา และ", "why:'ลูกค้าที่มาครั้งแรกยังไม่กลับมา และ", 1, 'mkt-s4why')
    # ---------- Google Business (ปรับวัน/รีวิวให้ตรงชุดข้อมูล) ----------
    gr = [r for r in REVIEWS if r['source'] != 'LINE OA']
    st = round(sum(r['rating_5'] for r in gr) / len(gr), 1)
    nw = sum(1 for r in gr if r['created_at'][:10] >= '2026-10-17')
    h = R(h, "weeks:['21 ก.ค.','28 ก.ค.','4 ส.ค.','11 ส.ค.','18 ส.ค.','25 ส.ค.','1 ก.ย.','8 ก.ย.','15 ก.ย.','22 ก.ย.','29 ก.ย.','6 ต.ค.']",
          "weeks:['4 ส.ค.','11 ส.ค.','18 ส.ค.','25 ส.ค.','1 ก.ย.','8 ก.ย.','15 ก.ย.','22 ก.ย.','29 ก.ย.','6 ต.ค.','13 ต.ค.','20 ต.ค.']", 1, 'mkt-weeks')
    h = R(h, "events:[[4,'เพิ่มรูป 12 รูป'],[8,'เริ่มขอรีวิว'],[10,'ออกพรรษา']]", "events:[[4,'เพิ่มรูป 12 รูป'],[8,'เริ่มขอรีวิว'],[11,'ออกพรรษา']]", 1, 'mkt-events')
    h = R(h, 'me:{n:\'พบรักรีสอร์ท\',st:4.4,rv:41,nw:1,pr:null}', 'me:{n:\'พบรักรีสอร์ท\',st:%s,rv:%d,nw:%d,pr:null}' % (st, len(gr), nw), 1, 'mkt-me')
    h = R(h, 'nap:["พบรักรีสอร์ท บ้านนิคม โคกสูง ขอนแก่น","158 ม.9 ต.โคกสูง อ.อุบลรัตน์ จ.ขอนแก่น 40250","098 535 4623"]', 'nap:["พบรักรีสอร์ท บ้านนิคม โคกสูง ขอนแก่น",%s,"098 535 4623"]' % J(m['hotel']['address']), 1, 'mkt-nap')
    h = R(h, "ข้อมูลจาก Google ถึง 12 ต.ค. · ตรวจอันดับล่าสุด ศ. 10 ต.ค. · ข้อมูลทั้งหมดเป็นตัวอย่าง", "ข้อมูลจาก Google ถึง 18 ต.ค. · ตรวจอันดับล่าสุด ศ. 23 ต.ค. · ข้อมูลทั้งหมดเป็นตัวอย่าง", 1, 'mkt-gvmeta')
    h = R(h, 'Search keywords · ก.ย. 2569', 'Search keywords · ต.ค. 2569', 1, 'mkt-kwm')
    h = h.replace('ศ. 10 ต.ค.', 'ศ. 23 ต.ค.')
    # ---------- เอกสาร ----------
    h = R(h, "QT2610-${p.id.slice(-3).toUpperCase()} · 23 ต.ค. 2569", "QT2610-${p.id.slice(-3).toUpperCase()} · 24 ต.ค. 2569", 1, 'mkt-qt')
    h = R(h, "if(!p.name)p.name='ใบเสนอราคา คุณสมชาย';d.cust=d.cust||'คุณสมชาย ใจดี';d.items=[{d:'ห้องพัก (เตียงเดี่ยว) 2 คืน',q:2,p:900},{d:'อาหารเช้า',q:4,p:80}];d.note='ชำระมัดจำ 50% ก่อนเข้าพัก'",
          "if(!p.name)p.name='ใบเสนอราคา ทีมงานบริษัท';d.cust=d.cust||'คุณศิริพร ใจดี';d.co=d.co||'บริษัท วาลเมท (ประเทศไทย) จำกัด';d.items=[{d:'ห้องพัก (ดีลักซ์ เตียงใหญ่) 12 คืน × 7 ห้อง',q:84,p:700},{d:'อาหารเช้า',q:84,p:80}];d.note='เครดิต 30 วัน ออกใบแจ้งหนี้รวม'", 1, 'mkt-quote')
    h = R(h, "'เช่น ใบเสนอราคา คุณสมชาย'", "'เช่น ใบเสนอราคา ทีมงานบริษัท'", 1, 'mkt-ph1')
    h = R(h, "'เช่น คุณสมชาย ใจดี'", "'เช่น คุณศิริพร ใจดี'", 1, 'mkt-ph2')
    h = R(h, "g.spend=S.n?baht(S.perVisit)+' ต่อครั้ง':'—'", "g.spend=S.n&&S.perVisit?baht(S.perVisit)+' ต่อครั้ง':'ยังไม่มีประวัติเข้าพัก'", 1, 'mkt-spend0')
    h = h.replace('20 ต.ค. – 30 พ.ย. 2569','24 ต.ค. – 30 พ.ย. 2569')
    h = R(h, '<span class="sample">ข้อมูลทั้งหมดเป็นตัวอย่าง</span>', '<span class="sample">ข้อมูลสมมติเพื่อสาธิต</span>', 1, 'mkt-sample')
    return h
