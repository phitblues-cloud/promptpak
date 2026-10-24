# -*- coding: utf-8 -*-
"""ให้ทุกโมดูลใช้วันที่จริง และไม่แสดงค่าอากาศ/ฝุ่นปลอมเมื่อดึงข้อมูลจริงไม่ได้"""
import datetime, re
from roomcodes import remap_text

MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']


def th(d):
    return f'{d.day} {MON[d.month - 1]} {d.year + 543}'


ZONE_FIX = [
    # ต้นแบบแยกโซนจากตัวอักษรแรกของรหัสห้อง (A = ตึก) แต่รหัสจริง A/B = ตึกใหม่, C = บ้านหลัง
    ("code[0]==='A'?'โซนตึก':'โซนบ้าน'", "code[0]!=='C'?'โซนตึก':'โซนบ้าน'"),
    ("id[0]==='A'?'โซนตึก':'โซนบ้าน'", "id[0]!=='C'?'โซนตึก':'โซนบ้าน'"),
    ("/^[AB]\\d/.test(x.room)", "/^[ABC]\\d/.test(x.room)"),
    # รายการห้องในโมดูลการตลาด
    ("{n:'โซนตึก · เตียงคู่ (ราคา 800)',price:800,photo:'v5'}", "{n:'โซนตึก · ห้องครอบครัว',price:800,photo:'v5'}"),
]
ZONE_LABEL = [(re.compile('โซนตึก(?!ใหม่)'), 'โซนตึกใหม่'), (re.compile('โซนบ้าน(?!หลัง)'), 'โซนบ้านหลัง')]


def rooms_2569(M):
    """ห้องจริง: ชื่อโซนใหม่ + รหัสห้องใหม่ในข้อความตัวอย่างที่ยังเหลือ"""
    for k, h in M.items():
        for old, new in ZONE_FIX:
            h = h.replace(old, new)
        for rx, new in ZONE_LABEL:
            h = rx.sub(new, h)
        M[k] = remap_text(h)
    if 'book' in M:
        h = M['book']
        for old, new in [
            # ชื่อโซนในโมดูลการจอง (ไม่ใส่คำว่า "โซน" เพื่อให้ความยาวเท่าเดิมในหัวปฏิทิน)
            ("const ZN=z=>z==='A'?'โซนตึกใหม่':z==='B'?'โซนบ้านหลัง':'โซน '+z;",
             "const ZN=z=>z==='A'?'ตึกใหม่':z==='B'?'บ้านหลัง':'โซน '+z;\n"
             "const codeRuns=cs=>{const o=[];cs.forEach(c=>{const l=o[o.length-1],n=+c.slice(1);"
             "if(l&&l.p===c[0]&&l.n+1===n){l.n=n;l.b=c}else o.push({p:c[0],n,a:c,b:c})});"
             "return o.map(r=>r.a===r.b?r.a:r.a+'–'+r.b).join(', ')};"),
            # เลขห้องที่ไม่ต่อเนื่อง แสดงเป็นช่วงจริง เช่น A01, B04–B05
            ("เลขห้อง ${codes[0]}–${codes[codes.length-1]}", "เลขห้อง ${codeRuns(codes)}"),
            # รูปห้องจริงลงช่องรูปเดิม 3 ช่อง (ไฟล์อยู่ใน public/rooms)
            ("<div class=\"gphotos\">${[1,2,3].map(()=>`<div class=\"gphoto\">${ico('image')}</div>`).join('')}</div>",
             "<div class=\"gphotos\">${[1,2,3].map(i=>{const k=ROOM_PHOTO[g.zone+'|'+g.type];"
             "return k?`<div class=\"gphoto\" style=\"position:relative;min-width:0;overflow:hidden;border-style:solid\"><img src=\"/rooms/${k}-${i}.jpg\" alt=\"${esc(ZN(g.zone)+' '+g.type)} รูปที่ ${i}\" loading=\"lazy\" "
             "style=\"position:absolute;inset:0;width:100%;height:100%;object-fit:cover\"></div>`:`<div class=\"gphoto\">${ico('image')}</div>`}).join('')}</div>"),
            # รายละเอียดเตียงจริงในฟอร์มเพิ่มการจอง (เช่น เตียงสองชั้น)
            ("<span>${two?'เตียงคู่':'เตียงเดี่ยว'}</span>",
             "<span>${esc((ROOMS.find(r=>r.zone===x.z&&r.type===x.t)||{}).bed||(two?'เตียงคู่':'เตียงเดี่ยว'))}</span>"),
            ("let ROOMS=[","const ROOM_PHOTO={'A|เตียงเดี่ยว':'tower-single','A|เตียงคู่':'tower-twin','A|ห้องครอบครัว':'tower-family',"
             "'B|เตียงเดี่ยว':'house-single','B|เตียงคู่':'house-twin'};\nlet ROOMS=["),
        ]:
            assert h.count(old) == 1, ('book-rooms', old[:40])
            h = h.replace(old, new)
        M['book'] = h


def apply(M, ref):
    rooms_2569(M)
    d = datetime.date.fromisoformat(ref)
    if 'crm' in M:
        h = M['crm']
        h = h.replace('const TODAY=new Date(2026,9,24);', f'const TODAY=new Date({d.year},{d.month - 1},{d.day});')
        h = h.replace("d2:'2026-10-24'", f"d2:'{d.isoformat()}'")
        M['crm'] = h
    if 'mkt' in M:
        M['mkt'] = M['mkt'].replace('· 24 ต.ค. 2569</small>', f'· {th(d)}</small>').replace('24 ต.ค. – 30 พ.ย. 2569', f'{th(d)[:-5]} – 30 พ.ย. 2569')
    if 'book' in M:
        # จองได้โดยไม่บังคับเลขบัตรประชาชนและภาพบัตร (ถ้ากรอกเลข ต้องครบ 13 หลัก)
        h = M['book']
        for old, new in [
            ("if(!isCo&&digits(F.idno).length!==13)p.push('เลขบัตรประชาชน 13 หลัก');",
             "if(!isCo&&digits(F.idno).length&&digits(F.idno).length!==13)p.push('เลขบัตรประชาชนให้ครบ 13 หลัก (หรือเว้นว่าง)');"),
            ("if(!isCo&&!F.idfile)p.push('ภาพถ่ายบัตรประชาชน');", ""),
            ('<label for="fId">เลขประจำตัวประชาชน *</label>', '<label for="fId">เลขประจำตัวประชาชน (ถ้ามี)</label>'),
            ('<label for="fFile">ภาพถ่ายบัตรประชาชน *</label>', '<label for="fFile">ภาพถ่ายบัตรประชาชน (ถ้ามี)</label>'),
            ("<br>บัตรประชาชน ${idn.slice(0,1)}-${idn.slice(1,5)}-${idn.slice(5,10)}-${idn.slice(10,12)}-${idn.slice(12)} · แนบรูปบัตรแล้ว`",
             "<br>บัตรประชาชน ${idn?`${idn.slice(0,1)}-${idn.slice(1,5)}-${idn.slice(5,10)}-${idn.slice(10,12)}-${idn.slice(12)}`:'ไม่ได้กรอก'}"
             "${F.idfile?' · แนบรูปบัตรแล้ว':''}`"),
        ]:
            assert h.count(old) == 1, ('book-id', old[:40])
            h = h.replace(old, new)
        M['book'] = h
    if 'home' in M:
        h = M['home']
        fake_wx = "showWx(WX.clear,32,33,24,null,'ข้อมูลจริงล่าสุด 22 ต.ค. 12:00 น. (IQAir) — ออฟไลน์');"
        assert fake_wx in h, 'home weather fallback'
        h = h.replace(fake_wx, "showWx({i:'cloud',t:'ดึงข้อมูลอากาศไม่ได้'},'–','–','–',null,'ออฟไลน์');")
        assert '}catch(e){ PMV=4; }' in h, 'home pm fallback'
        h = h.replace('}catch(e){ PMV=4; }', '}catch(e){ PMV=null; window.__pmFail=1; }')
        h = h.replace("if(PMV==null){ e.innerHTML='PM2.5 กำลังโหลด…'; return; }",
                      "if(PMV==null){ e.innerHTML=window.__pmFail?'PM2.5 –':'PM2.5 กำลังโหลด…'; return; }")
        # ระดับ PM2.5 ตามเกณฑ์ไทย (กรมควบคุมมลพิษ ประกาศ ก.ค. 2566) แทนเกณฑ์สหรัฐฯ
        a = h.index('const PM_LV=['); b = h.index('];', a) + 2
        h = h[:a] + (
            "const PM_LV=[\n"
            "  [15,'ดีมาก','#3BB8F0','#2E1F2B','smile','ดีมาก (0–15)'],\n"
            "  [25,'ดี','#7CCB5B','#2E1F2B','smile','ดี (15.1–25)'],\n"
            "  [37.5,'ปานกลาง','#FDD74B','#2E1F2B','flat','ปานกลาง (25.1–37.5)'],\n"
            "  [75,'เริ่มมีผล','#FE9B57','#2E1F2B','frown','เริ่มมีผลต่อสุขภาพ (37.6–75)'],\n"
            "  [1e9,'มีผลต่อสุขภาพ','#E5484D','#FFFFFF','mask','มีผลต่อสุขภาพ (75.1 ขึ้นไป)']\n"
            "];") + h[b:]
        old = '· ${lv[5]} · เกณฑ์ US AQI`;'
        assert h.count(old) == 1, 'home pm title'
        h = h.replace(old, '· ${lv[5]} · เกณฑ์กรมควบคุมมลพิษ · ค่าประมาณจาก Open-Meteo (CAMS)`;')
        # ที่ตั้งจริงของรีสอร์ท
        old = '<div class="src" title="${src}">น้ำพอง ขอนแก่น</div>'
        assert h.count(old) == 1, 'home location'
        h = h.replace(old, '<div class="src" title="${src}">อุบลรัตน์ ขอนแก่น</div>')
        M['home'] = h
    if 'fin' in M:
        old = '<div class="sub">อ.น้ำพอง จ.ขอนแก่น'
        assert M['fin'].count(old) == 1, 'fin address'
        M['fin'] = M['fin'].replace(old, '<div class="sub">อ.อุบลรัตน์ จ.ขอนแก่น')
    return M
