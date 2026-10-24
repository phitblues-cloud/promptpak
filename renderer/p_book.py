# -*- coding: utf-8 -*-
from patch_all import R, J
from nb import *

def book_item(b):
    o = {'id': 'b' + str(int(b['no'][4:])), 'no': b['no'], 'room': b['room'], 'start': b['start'], 'nights': b['nights'],
         'guest': b['guest'], 'phone': b['phone'], 'paid': b['paid'], 'payM': b['payM'], 'ch': b['ch'], 'pax': b['pax'],
         'adults': b['adults'], 'kids': 0, 'madeAt': b['madeAt'], 'note': b['note'], 'rate': b['rate'], 'purpose': b['purpose'],
         'bf': 0, 'disc': 0, 'code': '', 'email': b['email'], 'tax': b['tax'], 'cid': b['gid'], 'dep': b['dep'],
         'grp': b['grp'], 'mem': b['mem'], 'visits': b['visits'], 'lineNm': b['line'], 'lineOn': True}
    co = company_obj(b)
    if co:
        o['co'] = {'name': co['name'], 'tax': co['tax'], 'addr': co['addr'], 'hq': co['hq']}
        o['contact'] = co['contact']
        o['payer'] = co['payer']; o['terms'] = co['terms']; o['credDays'] = co['credDays']; o['po'] = co['po']
    if b.get('cancelled'):
        o['cancelled'] = True
    if b.get('noshow'):
        o['noshow'] = True
    if b['stage'] and b['start'] <= D0:
        o['hx'] = {'room': b['room'], 'guest': b['guest'], 'nights': b['nights'], 'stage': b['stage'], 'viaLine': b['viaLine'],
                   'left': (b['end'] - D0) if b['stage'] in ('stay',) else 0, 'phone': b['phone'], 'ch': b['ch'], 'pax': b['pax'],
                   'note': b['note'], 'line': b['line'], 'on': True, 'mem': b['mem'], 'grp': b['grp'], 'v': b['visits'],
                   'dep': b['dep'], 'lead': b['lead'], 'hm': b['hm'], 'purpose': b['purpose']}
    return o

def patch(h):
    # 1) ห้อง
    i = h.index('let ROOMS=[];'); tail = "ROOMS.find(r=>r.code==='B014').open=false;"
    j = h.index(tail) + len(tail)
    h = h[:i] + 'let ROOMS=' + J(ROOMS) + ';' + h[j:]
    # 2) ข้อมูลการจอง
    h = R(h, 'let B=[], seq=100;', 'let B=[], seq=77;', 1, 'book-seq')
    a = h.index('function mk(room'); b_ = h.index('const statusOf')
    data = ('/* ข้อมูลจากชุด POBRAK_MOCK (อ้างอิง 24 ต.ค. 2569) */\n'
            'const BC=' + J([book_item(x) for x in BC]) + ';\n'
            'B.push(...' + J([book_item(x) for x in BK]) + ');\n'
            'pubOcc();\n')
    h = h[:a] + data + h[b_:]
    h = R(h, "const statusOf=b=>{const e=endOf(b);", "const statusOf=b=>{if(b.cancelled)return ['ยกเลิก','b6','past'];if(b.noshow)return ['ไม่มาตามนัด','b6','past'];const e=endOf(b);", 1, 'book-statusOf')
    # 3) รายละเอียดการจอง
    h = R(h, "function detail(id,ctx){\n  const b=B.find(x=>x.id===id); if(!b) return;", "function detail(id,ctx){\n  const b=B.find(x=>x.id===id)||BC.find(x=>x.id===id); if(!b) return;", 1, 'book-detail')
    h = R(h, "if(d.pbr==='bkdetail'){const b=B.find(x=>x.no===d.no);", "if(d.pbr==='bkdetail'){const b=B.find(x=>x.no===d.no)||BC.find(x=>x.no===d.no);", 1, 'book-bkdetail')
    h = R(h, "const dep=h?h.dep:(b.start>=TODAY?'unpaid':'held');", "const dep=h?h.dep:(b.dep||(b.start>=TODAY?'unpaid':'held'));", 1, 'book-dep')
    h = R(h, "const depPill=dep==='unpaid'?pill('ยังไม่รับ','b2'):", "const depPill=dep==='none'?pill('ไม่ได้เก็บ','b6'):dep==='unpaid'?pill('ยังไม่รับ','b2'):", 1, 'book-depPill')
    h = R(h, "const lineOn=h?h.on:b.ch==='LINE OA', lineNm=h?h.line:gname;", "const lineOn=h?h.on:(b.lineOn!=null?b.lineOn:b.ch==='LINE OA'), lineNm=h?h.line:(b.lineNm||gname);", 1, 'book-line')
    h = R(h, "grp:h?h.grp:(co?'ลูกค้าบริษัท':'ลูกค้าทั่วไป'),mem:h?h.mem:false,visits:h?h.v:1,regBtn:!((h?h.mem:false)||co),",
          "grp:h?h.grp:(b.grp||(co?'ลูกค้าบริษัท':'ลูกค้าทั่วไป')),mem:h?h.mem:!!b.mem,visits:h?h.v:(b.visits||1),regBtn:!((h?h.mem:!!b.mem)||co),", 1, 'book-grp')
    h = R(h, "const roomPill=b.paid?pill('จ่ายแล้ว','b3'):", "const roomPill=b.cancelled?pill('คืนเงินแล้ว','b6'):b.noshow?pill('ไม่มีรายการเงิน','b6'):b.paid?pill('จ่ายแล้ว','b3'):", 1, 'book-roomPill')
    h = R(h, "const DEP_AMT=200;", "const DEP_AMT=300;", 1, 'book-dep-amt')
    h = R(h, "const depOf=b=>b.hx?b.hx.dep:(b.start>TODAY?'unpaid':'held');", "const depOf=b=>b.hx?b.hx.dep:(b.dep||(b.start>TODAY?'unpaid':'held'));", 1, 'book-depOf')
    # 4) เลขจองใหม่ต่อจากชุดข้อมูล: BK6910078...
    h = R(h, "const draftNo='BK2610-'+String(seq+1).padStart(4,'0');", "const draftNo='BK6910'+String(seq+1).padStart(3,'0');", 1, 'book-draft')
    h = R(h, "no='BK2610-'+String(n0).padStart(4,'0')", "no='BK6910'+String(n0).padStart(3,'0')", 1, 'book-no')
    return h
