# -*- coding: utf-8 -*-
"""ให้ทุกโมดูลใช้วันที่จริง และไม่แสดงค่าอากาศ/ฝุ่นปลอมเมื่อดึงข้อมูลจริงไม่ได้"""
import datetime

MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']


def th(d):
    return f'{d.day} {MON[d.month - 1]} {d.year + 543}'


def apply(M, ref):
    d = datetime.date.fromisoformat(ref)
    if 'crm' in M:
        h = M['crm']
        h = h.replace('const TODAY=new Date(2026,9,24);', f'const TODAY=new Date({d.year},{d.month - 1},{d.day});')
        h = h.replace("d2:'2026-10-24'", f"d2:'{d.isoformat()}'")
        M['crm'] = h
    if 'mkt' in M:
        M['mkt'] = M['mkt'].replace('· 24 ต.ค. 2569</small>', f'· {th(d)}</small>').replace('24 ต.ค. – 30 พ.ย. 2569', f'{th(d)[:-5]} – 30 พ.ย. 2569')
    if 'home' in M:
        h = M['home']
        fake_wx = "showWx(WX.clear,32,33,24,null,'ข้อมูลจริงล่าสุด 22 ต.ค. 12:00 น. (IQAir) — ออฟไลน์');"
        assert fake_wx in h, 'home weather fallback'
        h = h.replace(fake_wx, "showWx({i:'cloud',t:'ดึงข้อมูลอากาศไม่ได้'},'–','–','–',null,'ออฟไลน์');")
        assert '}catch(e){ PMV=4; }' in h, 'home pm fallback'
        h = h.replace('}catch(e){ PMV=4; }', '}catch(e){ PMV=null; window.__pmFail=1; }')
        h = h.replace("if(PMV==null){ e.innerHTML='PM2.5 กำลังโหลด…'; return; }",
                      "if(PMV==null){ e.innerHTML=window.__pmFail?'PM2.5 –':'PM2.5 กำลังโหลด…'; return; }")
        M['home'] = h
    return M
