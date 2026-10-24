# -*- coding: utf-8 -*-
import collections
from patch_all import R, J
from nb import *

def month_rows():
    agg = collections.OrderedDict()
    for d in m['daily_occupancy']:
        k = d['date'][:7]
        a = agg.setdefault(k, {'days': 0, 'sold': 0, 'rev': 0, 'past': 0})
        a['days'] += 1; a['sold'] += d['rooms_sold']; a['rev'] += d['room_revenue']
        if d['date'] <= REF: a['past'] += 1
    out = []
    MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
    for k, a in agg.items():
        y, mo = int(k[:4]), int(k[5:])
        out.append({'l': f'{MON[mo-1]} {str((y+543)%100)}', 'days': a['days'], 'past': a['past'], 'sold': a['sold'], 'rev': a['rev'],
                    'occ': round(a['sold'] * 100 / (31 * a['days']), 1)})
    return out

def patch(h):
    i = h.index('const HIST=['); j = h.index('\n', i)
    h = h[:i] + 'const HIST=[]; // ยังไม่มีข้อมูลย้อนหลังก่อน 13 ต.ค. 2569' + h[j:]
    h = R(h, "const ROOMS=31,PRICE=17700/31;", "const ROOMS=31,PRICE=%d/31;" % sum(r['rate'] for r in ROOMS), 1, 'rep-price')
    i = h.index("const PRE_Y={"); j = h.index("\n", i)
    h = h[:i] + "const PRE_Y={};" + h[j:]
    h = R(h, "ข้อมูลตัวอย่าง (เดือนปัจจุบันดึงสดจากเมนูการเงิน * ยังไม่ครบเดือน)", "เดือนปัจจุบันดึงสดจากเมนูการเงิน * ยังไม่ครบเดือน · ยังไม่มีข้อมูลก่อน 13 ต.ค. 69", 1, 'rep-sub')
    # ภาพรวม: ตัดคำเตือนแนวโน้ม 3 เดือน (ไม่มีข้อมูลย้อนหลัง)
    i = h.index("W.push([n3<p3?'warn':'info'"); j = h.index("\n", i)
    h = h[:i] + h[j + 1:]
    # ผลประกอบการ
    i = h.index("function renderPl(){"); j = h.index("/* ---------- pace (sample) ---------- */")
    rows = month_rows()
    pl = ("const MROWS=" + J(rows) + ";\n"
          "function renderPl(){\n yoyChart('c16',300);\n"
          " $('plSub').textContent='ยังไม่มีข้อมูลย้อนหลังก่อน 13 ต.ค. 2569 และยังไม่มีรายจ่ายที่บันทึกในระบบ';\n"
          " $('yoyH').textContent='เทียบรายปี';\n"
          " $('yoy').innerHTML='<tbody><tr><td>ยังไม่มีข้อมูลปีก่อนให้เทียบ</td></tr></tbody>';$('yoyNote').textContent='';\n"
          " $('be').innerHTML='<p>ยังคำนวณจุดคุ้มทุนไม่ได้ ต้องมีรายจ่ายที่บันทึกอย่างน้อย 2–3 เดือน</p>';\n"
          " $('mt').innerHTML='<thead><tr><th>เดือน</th><th class=\"n\">วันที่มีข้อมูล</th><th class=\"n\">ห้อง-คืนที่ขายได้</th><th class=\"n\">ค่าห้อง (บาท)</th><th class=\"n\">Occupancy</th></tr></thead><tbody>'+MROWS.map(x=>`<tr><td>${x.l}</td><td class=\"n\">${x.days}${x.past<x.days?` <span class=\"tag est\" title=\"วันที่ยังมาไม่ถึงนับจากการจองล่วงหน้า\">มีจองล่วงหน้า</span>`:''}</td><td class=\"n\">${fmt(x.sold)}</td><td class=\"n\">${fmt(x.rev)}</td><td class=\"n\">${x.occ}%</td></tr>`).join('')+'</tbody>';\n"
          "}\n")
    h = h[:i] + pl + h[j:]
    h = R(h, "Occupancy ประมาณจาก รายรับ ÷ ราคาตั้งเฉลี่ย 571 บาท × 31 ห้อง", "ห้อง-คืนที่ขายได้และค่าห้อง จากข้อมูลการจองตามวันเข้าพัก", 1, 'rep-mt-sub')
    # เดือนปัจจุบัน: นับตั้งแต่วันที่เริ่มมีข้อมูล (13 ต.ค.)
    h = R(h, "let occN=0;for(let k=1;k<=day;k++){", "const d0=13,dn=Math.max(1,day-d0+1);let occN=0;for(let k=d0;k<=day;k++){", 1, 'rep-d0')
    h = R(h, "return{r:f.rev||0,e:f.exp||0,roomRev:f.roomRev||0,day,occN,occ:occN/(ROOMS*day),", "return{r:f.rev||0,e:f.exp||0,roomRev:f.roomRev||0,day,dn,occN,occ:occN/(ROOMS*dn),", 1, 'rep-curM')
    h = R(h, "ห้อง-คืนที่มีคนพัก ${c.occN} จาก ${ROOMS*c.day}", "ห้อง-คืนที่มีคนพัก ${c.occN} จาก ${ROOMS*c.dn}", 1, 'rep-occ')
    h = R(h, "fmt(c.r/(ROOMS*c.day))", "fmt(c.r/(ROOMS*c.dn))", 1, 'rep-revpar')
    h = R(h, "`เดือนนี้ ${c.day} วันแรก · ดึงสดจากเมนูการเงินและจัดการการจอง`", "`เดือนนี้ตั้งแต่ 13 ต.ค. (${c.dn} วัน) · ดึงสดจากเมนูการเงินและจัดการการจอง`", 1, 'rep-ovsub')
    h = R(h, "`สะสม ${c.day} วัน · รับจริงจากใบเรียกเก็บ`", "`สะสม ${c.dn} วัน (ตั้งแต่ 13 ต.ค.) · รับจริงจากใบเรียกเก็บ`", 1, 'rep-acc')
    h = R(h, "เดือนก่อนหน้าเป็นข้อมูลตัวอย่างย้อนหลัง", "ข้อมูลเริ่มตั้งแต่ 13 ต.ค. 2569 จึงยังไม่มีเดือนก่อนให้เทียบ", 1, 'rep-notice')
    return h
