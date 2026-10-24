# -*- coding: utf-8 -*-
import re, datetime
from patch_all import R, J
from nb import *

MTH = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
RD = datetime.date.fromisoformat(REF)

def ago(iso):
    d = datetime.date(*map(int, iso[:10].split('-')))
    n = (RD - d).days
    if n <= 0: return 'วันนี้'
    if n == 1: return 'เมื่อวาน'
    return f'{n} วันก่อน'

def mo_lbl(iso):
    d = datetime.date(*map(int, iso[:10].split('-')))
    return f'{MTH[d.month - 1]} {d.year + 543}'

def dth(iso):
    d = datetime.date(*map(int, iso[:10].split('-')))
    return f'{d.day} {MTH[d.month - 1]}'

def days_ago(iso):
    d = datetime.date(*map(int, iso[:10].split('-')))
    return (RD - d).days

# ---------------- ฐานลูกค้า (GU) ----------------
CHATS = {}
for c in m['line_chats']:
    CHATS.setdefault(c['guest_id'], []).append(c)
NEGREV = {r['guest_id'] for r in REVIEWS if r['sentiment'] == 'ลบ'}
PAYER_CONTACT = {c['guest_id'] for c in m['company_contacts'] if c['guest_id'] and ('จ่าย' in c['role'] or 'โอน' in c['role'])}
COORD = {g['coordinator_guest_id'] for g in m['booking_groups']}

def seg_of(g):
    bs = [b for b in BK + BC if b['gid'] == g['guest_id']]
    if g['company_id'] not in CO: return 'L'
    if any(b['kind'] != 'self' for b in bs): return 'B'
    return 'W3'

def build_gu():
    out = []
    for g in m['guests']:
        gid = g['guest_id']
        bs = sorted([b for b in BK + BC if b['gid'] == gid], key=lambda b: b['start'])
        act = [b for b in bs if b['stage']]
        seg = seg_of(g)
        roles = ['guest']
        if gid in COORD or gid in {b['gid'] for b in act if b['group'] and any(x['no'] != b['no'] and x['group'] == b['group'] and x['gid'] != gid for x in BK)}:
            roles.append('booker')
        if seg != 'B' or gid in PAYER_CONTACT:
            roles.append('payer')
        if 'หัวหน้า' in g['segment']:
            roles.append('leader')
        mb = MEM.get(gid)
        chats = CHATS.get(gid, [])
        line = 'linked' if mb else ('friend' if chats else 'none')
        if act:
            lastb = act[-1]
            ref = min(lastb['end'], D0) if lastb['start'] <= D0 else (lastb['madeAt'] // 86400000)
            ref = max(ref, max((x['madeAt'] // 86400000) for x in act))if lastb['start'] > D0 else ref
            last = max(0, D0 - ref)
        else:
            last = 0
        by, bm, bd = map(int, g['birth_date'].split('-'))
        nxt = datetime.date(RD.year, bm, bd)
        if nxt < RD: nxt = datetime.date(RD.year + 1, bm, bd)
        bdM = (nxt - RD).days <= 30
        latest = act[-1] if act else (bs[-1] if bs else None)
        nights = latest['nights'] if latest else 1
        room = 'ตึก' if (latest and latest['room'][0] == 'A') else 'บ้าน'
        ch = latest['ch'] if latest else 'LINE OA'
        joined = dno(mb['joined_at']) if mb else None
        out.append({'n': disp(g), 'seg': seg, 'roles': roles, 'line': line, 'member': bool(g['is_member']), 'room': room, 'ch': ch,
                    'nights': nights, 'stays': max(1, g['bookings_total'] or 1), 'bday': True, 'tags': list(g['tags']),
                    'tax': any(b['taxReq'] for b in bs), 'last': last,
                    'f': {'complaint': gid in NEGREV or any('ร้องเรียน' in t for c in chats for t in c['topic_tags']),
                          'cancel': any(b.get('cancelled') or b.get('noshow') for b in bs),
                          'urgent': any(c['status'] == 'รอพนักงาน' for c in chats),
                          'booked': (g['upcoming_bookings'] or 0) > 0,
                          'noMkt': not (mb and mb['consent_marketing']),
                          'block': False},
                    'nf': bool(joined and D0 - joined <= 14), 'chat': bool(chats), 'recent': last <= 90, 'bdM': bdM,
                    'cyc': (g['bookings_total'] or 0) >= 2})
    return out

# ---------------- บริษัท ----------------
def co_stats(cid):
    bs = [b for b in BK if b['cid'] == cid]
    st = [b for b in bs if b['start'] <= D0]
    fut = [b for b in bs if b['start'] > D0]
    times = len({b['group'] for b in st})
    people = len({b['gid'] for b in st})
    rn = sum(b['nights'] for b in st)
    spend = sum(b['total'] for b in st)
    zones = sorted({('ตึก' if b['room'][0] == 'A' else 'บ้าน') for b in st})
    nxt = min((b['start'] for b in fut), default=None)
    return dict(times=times, people=people, rn=rn, spend=spend, zones=zones, fut=len(fut), nxt=nxt, avg=(rn / len(st) if st else 0))

def name_of(cid):
    if cid in CO: return CO[cid]['name_th']
    return next(p['name_th'] for p in m['prospects'] if p['company_id'] == cid)

def th_from_dno(n):
    d = EPOCH + datetime.timedelta(days=n)
    return f'{d.day} {MTH[d.month - 1]}'

def contact_name(ct):
    if ct['guest_id']: return gname(ct['guest_id'])
    return ct['name'].replace(' (ผู้ติดต่อสมมติ)', '')

def role_of(ct):
    d = ct['decision']
    if d.startswith('ผู้ตัดสินใจ'): return 'ผู้ตัดสินใจ'
    if 'จ่าย' in d: return 'ผู้ดำเนินการจ่าย'
    return 'ผู้ประสานงาน'

def timeline_for(cid, opp=None):
    rows = sorted([a for a in m['crm_activities'] if a['company_id'] == cid], key=lambda a: (a['date'], a['activity_id']), reverse=True)
    tl = []
    for a in rows:
        who = 'ระบบ' if a['type'] == 'ระบบแจ้งเตือน' else (SN[a['by']] + ' · ' + a['type'])
        tl.append({'w': ago(a['date']), 'who': who, 't': a['summary'], 's': ''})
    if opp:
        tl.append({'w': ago(opp['created_at']), 'who': 'ระบบ', 't': 'เปิดดีล: ' + opp['title'], 's': opp['note']})
    return tl

def build_ds():
    stage_map = {'ปิดการขายได้': 'won', 'ยืนยันแล้ว': 'won', 'เจรจา': 'neg', 'เป้าหมาย-ยังไม่ติดต่อ': 'prof'}
    ds = []
    for o in m['crm_opportunities']:
        cid = o['company_id']
        cts = [c for c in m['company_contacts'] if c['company_id'] == cid]
        people = [{'n': contact_name(c), 'r': role_of(c)} for c in cts]
        s = co_stats(cid) if cid in CO else dict(times=0, people=0, rn=0, zones=[])
        acts = sorted([a for a in m['crm_activities'] if a['company_id'] == cid], key=lambda a: a['date'], reverse=True)
        idle = days_ago(acts[0]['date']) if acts else days_ago(o['created_at'])
        stage = stage_map[o['stage']]
        nxt, nxt_text = None, ''
        if stage == 'neg':
            nxt_text = 'รอฝ่ายจัดซื้อพิจารณาสัญญาราคาพิเศษรายปี'
        elif stage == 'prof':
            nxt, nxt_text = 0, 'หาผู้ติดต่อ KSL น้ำพอง / ผู้รับเหมาซ่อมก่อนหีบอ้อย'
        if cid in CO:
            note = f"{s['people']} คน · {s['rn']} ห้องคืน" + (' · ' + '/'.join(s['zones']) if s['zones'] else '')
            if not s['times']: note = 'ยังไม่เคยพัก · จองล่วงหน้าไว้แล้ว'
        else:
            pr = next(p for p in m['prospects'] if p['company_id'] == cid)
            note = 'ยังไม่เคยพัก · ' + pr['why_target']
        ds.append({'id': 'd' + str(len(ds) + 1), 'name': name_of(cid), 'stage': stage, 'src': 'ใหม่', 'idle': idle, 'next': nxt,
                   'nextText': nxt_text, 'val': o['value_baht'], 'people': people,
                   'stays': {'n': s['times'], 'rn': s['rn'], 'note': note}, 'tl': timeline_for(cid, o)})
    # เรียงให้ดีลที่ยังเปิดอยู่มาก่อน
    return ds

def build_lb():
    cid = 'G900'
    cts = [c for c in m['company_contacts'] if c['company_id'] == cid]
    s = co_stats(cid)
    return [{'id': 'b1', 'name': name_of(cid), 'd': 'ส่งใบเสนอราคา 20 ต.ค. (2 ห้อง 3 คืน) · ยังไม่มีดีลในไปป์ไลน์',
             'btn': 'ทำข้อเสนอ', 'people': [{'n': contact_name(c), 'r': role_of(c)} for c in cts],
             'stays': {'n': s['times'], 'rn': s['rn'], 'note': 'จองล่วงหน้า %d ห้อง · เครดิตหน่วยงานราชการ %d วัน' % (s['fut'], CO[cid]['credit_days'])}}]

def msgs_for(cid):
    gids = {g['guest_id'] for g in m['guests'] if g['company_id'] == cid}
    th = sorted([c for c in m['line_chats'] if c['guest_id'] in gids], key=lambda c: c['last_message_at'])
    if not th: return []
    c = th[-1]
    out = []
    for x in c['messages']:
        if x['from'] == 'ระบบอัตโนมัติ' or not x.get('text'): continue
        out.append({'w': 'cu' if x['from'] == 'ลูกค้า' else 'me', 't': x['text'], 'd': ago(x['at'])})
    return out[-5:]

def build_cl():
    cl = []
    for c in m['companies']:
        cid = c['company_id']
        s = co_stats(cid)
        ct = co_contact(cid)
        acts = sorted([a for a in m['crm_activities'] if a['company_id'] == cid], key=lambda a: (a['date'], a['activity_id']), reverse=True)
        opp = next((o for o in m['crm_opportunities'] if o['company_id'] == cid), None)
        ai = []
        if s['times']:
            ai.append(f"พักแล้ว {s['times']} ครั้ง โดย {s['people']} คน · {s['rn']} ห้องคืน · เฉลี่ย {s['avg']:.1f} คืนต่อห้อง")
        else:
            ai.append('ยังไม่เคยเข้าพัก')
        if s['fut']:
            ai.append(f"จองล่วงหน้าไว้แล้ว {s['fut']} ห้อง · เข้าพักครั้งถัดไป {th_from_dno(s['nxt'])}")
        ai.append('การชำระเงิน: ' + c['billing_mode'])
        o = {'id': 'c' + cid[1:] if cid.startswith('C') else 'c' + cid, 'name': c['name_th'], 'tax': c['tax_id'],
             'st': 'new' if cid == 'C004' else 'talk', 'seen': cid != 'C004', 'contact': gname(ct['guest_id']) if ct else '',
             'biz': c['industry'], 'phone': ct['phone'] if ct else '', 'email': ct['email'] if ct else '',
             'line': ct['line_display_name'] if ct else '', 'addr': clean_addr(c['billing_address']),
             'people': s['people'], 'times': s['times'], 'spend': s['spend'], 'special': [],
             'ai': ' · '.join(ai), 'msgs': {'line': msgs_for(cid), 'email': []},
             'tl': [{'mo': mo_lbl(a['date']), 'd': ago(a['date']), 'w': 'sys' if a['type'] == 'ระบบแจ้งเตือน' else 'me', 'ch': ('ระบบ' if a['type'] == 'ระบบแจ้งเตือน' else a['type']), 't': a['summary'], 's': ''} for a in acts]}
        if cid == 'C004':
            o['when'] = ago(c['first_stay']); o['why'] = 'เช็คอินแล้วขอใบกำกับภาษี/เครดิตในนามบริษัท'
        nx = {'C001': 'รอฝ่ายจัดซื้อพิจารณาสัญญาราคาพิเศษรายปี', 'G900': 'รอผลใบเสนอราคา 2 ห้อง 3 คืน', 'C004': 'ออกใบแจ้งหนี้รวมตามรอบเครดิต 30 วัน'}.get(cid, '')
        o['nx'] = nx
        if msgs_for(cid):
            o['chatAi'] = 'คุยล่าสุดทาง LINE: ' + msgs_for(cid)[-1]['t'][:60]
        cl.append(o)
    return cl

def lines_stats():
    friends = len([g for g in m['guests'] if g['line_user_id'] or g['line_display_name']])
    linked = len(m['members'])
    auto = sum(1 for c in m['line_chats'] for x in c['messages'] if x['from'] == 'ระบบอัตโนมัติ')
    cons = sum(1 for x in m['members'] if x['consent_marketing'])
    return friends, linked, auto, cons

def patch(h):
    friends, linked, auto, cons = lines_stats()
    # ตัวแปรตัวอย่างในพรีวิวข้อความ
    e01 = next(b for b in BK if b['gid'] == 'E01')
    h = R(h, "const VARS={'ชื่อ':'คุณสมชาย','ห้อง':'A007','วันเข้าพัก':'20 ต.ค.','จำนวนคืน':'4',",
          "const VARS={'ชื่อ':" + J('คุณ' + G['E01']['first_name']) + ",'ห้อง':" + J(e01['room']) + ",'วันเข้าพัก':" + J(th_from_dno(e01['start'])) + ",'จำนวนคืน':" + J(str(e01['nights'])) + ",", 1, 'ct-vars')
    h = R(h, "const TAGS=['VIP','มากับครอบครัว','ขอห้องเงียบ','พักประจำ'];",
          "const TAGS=['ขอใบกำกับภาษี','ช่างในสังกัด','เครดิตองค์กร','วันเกิดช่วง พ.ย.–ธ.ค.','ผู้จองให้ทีม'];", 1, 'ct-tags')
    # ฐานลูกค้า
    i = h.index("/* ฐานลูกค้าตัวอย่าง"); j = h.index('const POOL=')
    h = h[:i] + '/* ฐานลูกค้าจากชุดข้อมูล POBRAK_MOCK (40 คน) */\nconst GU=' + J(build_gu()) + ';\n' + h[j:]
    # LINE OA
    i = h.index("const LS={oa:"); j = h.index('\n', i)
    ls = ("const LS={oa:'@pobrakresort',api:true,hook:true,lastEv:'วันนี้',friends:%d,linked:%d,ways:{qr:true,link:true,otp:false},qFrom:'21:00',qTo:'08:00',cap:2,capSvc:false,plan:300,used:%d,askConsent:true,consentMkt:%d};" % (friends, linked, auto, round(cons / friends * 100)))
    h = h[:i] + ls + h[j:]
    # สถิติข้อความอัตโนมัติ: ไม่มีประวัติการส่งในชุดข้อมูล
    h, n = re.subn(r"n:'(?:ส่ง|ตอบ)[^']*',res:'[^']*'", "n:'ยังไม่มีสถิติ',res:''", h)
    assert n == 8, n
    # ประวัติการส่งตัวอย่าง
    a = h.index("const hist=m.st==='on'?`<div class=\"hist\">ประวัติการส่งล่าสุด (ตัวอย่าง)")
    b = h.index(":'<div class=\"hist\">ยังไม่มีประวัติการส่ง", a)
    h = h[:a] + "const hist=" + h[b + 1:]
    # แคมเปญตัวอย่าง
    i = h.index("const CAMPS=["); j = h.index('\n', i)
    h = h[:i] + 'const CAMPS=[];' + h[j:]
    # ไปป์ไลน์การขาย
    i = h.index('let DS=['); j = h.index('const nextLbl=')
    h = h[:i] + 'let DS=' + J(build_ds()) + ';\nlet LN=[];\nlet LB=' + J(build_lb()) + ';\n' + h[j:]
    i = h.index('const EXTRA_CO=['); j = h.index('\n', i)
    h = h[:i] + 'const EXTRA_CO=[];' + h[j:]
    h = R(h, "DS.forEach(d=>add({n:d.name,m:true,info:`พัก ${d.stays.n} ครั้ง · ${d.stays.rn} ห้องคืน`,deal:d.id}));",
          "DS.forEach(d=>add({n:d.name,m:true,info:d.stays.n?`พัก ${d.stays.n} ครั้ง · ${d.stays.rn} ห้องคืน`:'ยังไม่เคยพัก · เป็นเป้าหมาย',deal:d.id}));", 1, 'ct-coall')
    # รายชื่อบริษัท
    i = h.index('const CL=['); j = h.index('const clBy=')
    h = h[:i] + 'const CL=' + 'CLDATA.map(mkCo);\n' + h[j:]
    h = h.replace('const CL=CLDATA', 'const CLDATA=' + J(build_cl()) + ';\nconst CL=CLDATA', 1)
    h = R(h, '<span class="samp-pill">ข้อมูลตัวอย่าง</span>', '<span class="samp-pill">ข้อมูลสมมติ</span>', 1, 'ct-samp')
    h = R(h, "<div class=\"tile\"><small>ส่งเดือนนี้</small><b>412</b></div><div class=\"tile\"><small>อัตราอ่าน</small><b>78%</b></div><div class=\"tile\"><small>อัตราบล็อก</small><b>0.8%</b></div>",
          "<div class=\"tile\"><small>ส่งเดือนนี้</small><b>${LS.used}</b></div><div class=\"tile\"><small>อัตราอ่าน</small><b>—</b></div><div class=\"tile\"><small>อัตราบล็อก</small><b>0%</b></div>", 1, 'ct-stats')
    h = R(h, "<small>จองซ้ำจากข้อความ</small><b>9 ครั้ง</b>", "<small>จองซ้ำจากข้อความ</small><b>—</b>", 1, 'ct-rebook')
    h = R(h, "let _ps='';setInterval(", "let _cn='';setInterval(()=>{try{const L={leads:LN.map(l=>({id:l.id,name:l.name,d:l.d||''})),cos:CL.filter(c=>!c.seen).map(c=>({id:c.id,name:c.name,d:(c.why||'')+(c.when?' · '+c.when:'')}))};const sg=JSON.stringify(L);if(sg!==_cn){_cn=sg;pub('crmnew',L)}}catch(_){}},800);\nlet _ps='';setInterval(", 1, 'ct-pubnew')
    return h
