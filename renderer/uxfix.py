# -*- coding: utf-8 -*-
"""ปรับหน้าตาตามที่เจ้าของอนุมัติจากภาพร่าง (25 ต.ค. 2569)

- ลูกค้าและสมาชิก (ภาพร่าง docs/mockups/cust_list_v3.png): แถบกรองแถวเดียว · เรียง 4 แบบ · ไม่แสดงรหัสลูกค้า ·
  รหัสสมาชิก PBM-0001 · ปุ่ม 🔍 ดูโปรไฟล์
- แชท LINE (ภาพร่าง docs/mockups/linechat_v3.png): ชื่อใหญ่ · บริษัทใต้ชื่อจริง · ป้ายสมาชิกขวาของชื่อ ·
  AI สรุปกล่องเล็ก (กดอ่านทั้งหมด) + ป้ายเรื่อง · สถานะการเข้าพักใต้ "ดูเพิ่มเติม" · เรียง ล่าสุด|ด่วน · กรองประเภทเรื่อง
"""


def _r(h, pairs, name):
    for old, new in pairs:
        assert h.count(old) == 1, (name, h.count(old), old[:80])
        h = h.replace(old, new)
    return h


def _css(h, css):
    k = h.rindex('</style>')
    return h[:k] + css + h[k:]


MAG = ('<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" '
       'stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L20 20"/></svg>')

CUST_BAR = r"""  const mc=(v,t)=>`<button data-mem="${v}" aria-pressed="${S.f.member===v}">${t}</button>`;
  h+=`<div class="fbar2">${isC?`<div class="sortchips" role="group" aria-label="สถานะสมาชิก">${mc('all','ทั้งหมด')}${mc('yes','สมาชิก')}${mc('no','ไม่ใช่สมาชิก')}</div>`:''}`;
  if(isC) h+=`${sel('fType','type',[['all','กลุ่มลูกค้า: ทั้งหมด'],['new','ใหม่'],['gen','ทั่วไป'],['rep','มาซ้ำ'],['often','มาบ่อย'],['lost','หาย']])}
    ${sel('fPur','purpose',[['all','วัตถุประสงค์: ทั้งหมด'],['ทำงาน','ทำงาน'],['แวะพัก','แวะพัก'],['งานบุญ','งานบุญ'],['ราชการ/อบรม','ราชการ/อบรม']])}
    <button class="iconbtn" id="ruleBtn" title="เกณฑ์กลุ่มลูกค้า" aria-label="เกณฑ์กลุ่มลูกค้า">${ico('info')}</button>`;
  h+=`<label class="sortsel">เรียง<select data-sortsel aria-label="เรียงลำดับ" onchange="S.sort=this.value;render()">${(isC?[['recent','พักล่าสุด'],['old','เก่า-ใหม่'],['new','ใหม่-เก่า'],['name','ตัวอักษร ก–ฮ']]:[['name','ชื่อ ก–ฮ'],['spend','ยอดใช้จ่ายสูงสุด']]).map(([v,t])=>`<option value="${v}" ${S.sort===v?'selected':''}>${t}</option>`).join('')}</select></label>`;
  if(isC) h+=`<button class="linkbtn" id="resetF">ล้างตัวกรอง</button>`;
"""

CUST_CSS = """
.fbar2{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;background:var(--card);border:1.5px solid var(--line);border-radius:20px;padding:.6rem .8rem;margin-bottom:.9rem}
.fbar2 select{min-height:2.7rem;border:1.5px solid var(--line);border-radius:99px;padding:0 2rem 0 1rem;background-color:#fff;font:inherit;font-weight:600}
.sortsel{display:flex;align-items:center;gap:.4rem;margin-left:auto;color:var(--soft);font-weight:600}
.iconbtn{border:0;background:none;color:var(--purple);display:grid;place-items:center;width:2.4rem;height:2.4rem}
.go2{display:inline-flex;align-items:center;gap:.3rem;color:var(--soft);font-weight:600;font-size:.85rem;white-space:nowrap}
.tr:hover .go2{color:var(--purple)}
"""


def cust(h):
    a = h.index('  h+=`<div class="fbar"><div class="fgrp"><span class="lb">จัดเรียงตาม</span>')
    b = h.index("  h+='</div>';\n  if(isC){", a)
    h = h[:a] + CUST_BAR + h[b:]
    h = _r(h, [
        ("  else if(S.sort==='old') L.sort((a,b)=>a.c.added-b.c.added);",
         "  else if(S.sort==='recent') L.sort((a,b)=>(b.s.last??-1e9)-(a.s.last??-1e9));\n"
         "  else if(S.sort==='old') L.sort((a,b)=>a.c.added-b.c.added);"),
        ("S={view:'list',sub:'cust',sort:'name',", "S={view:'list',sub:'cust',sort:'recent',"),
        ("S.sort='name';S.q=''", "S.sort=a.dataset.sub==='cust'?'recent':'name';S.q=''"),
        ("  if(a=t.closest('[data-sort]')){S.sort=a.dataset.sort;render();return}",
         "  if(a=t.closest('[data-sort]')){S.sort=a.dataset.sort;render();return}\n"
         "  if(a=t.closest('[data-mem]')){S.f.member=a.dataset.mem;render();return}"),
        # แบบ ง.: ไม่แสดงรหัสลูกค้า · รหัสสมาชิก PBM-0001
        ('<div class="c-code num">${c.id}</div>', ''),
        ('<div>#</div><div>รหัสลูกค้า</div><div>ชื่อ-สกุล</div>', '<div>#</div><div>ชื่อ-สกุล</div>'),
        ("const memBadge=(c,s)=>c.memberNo?`<span class=\"badge m-yes\">เป็นสมาชิก</span>`",
         "const pbm=n=>{const d=String(n||'').replace(/\\D/g,'');return d?'PBM-'+d.padStart(4,'0'):''};"
         "const memBadge=(c,s)=>c.memberNo?`<span class=\"badge m-yes\">สมาชิก · ${pbm(c.memberNo)}</span>`"),
        ("c.memberNo.toLowerCase().includes(q)", "(c.memberNo.toLowerCase().includes(q)||pbm(c.memberNo).toLowerCase().includes(q))"),
        ("${c.memberNo?'รหัสสมาชิก '+c.memberNo:'ยังไม่เป็นสมาชิก'} · รหัสลูกค้า ${c.id}</div>",
         "${c.memberNo?'รหัสสมาชิก '+pbm(c.memberNo):'ยังไม่เป็นสมาชิก'}</div>"),
        ("c.memberNo?`<b>เป็นสมาชิก</b> · ${c.memberNo} · ตั้งแต่", "c.memberNo?`<b>เป็นสมาชิก</b> · ${pbm(c.memberNo)} · ตั้งแต่"),
        ("toast(`สมัครสมาชิกให้ ${c.name} แล้ว (${c.memberNo})`);", "toast(`สมัครสมาชิกให้ ${c.name} แล้ว (${pbm(c.memberNo)})`);"),
        # ปุ่มดูโปรไฟล์: แว่นขยาย + ข้อความ แทนรูปตา
        ("<span class=\"go\">${ico('eye')}</span>", '<span class="go2">' + MAG + 'ดูโปรไฟล์</span>'),
        ('grid-template-columns:2.4rem 5rem 1.5fr 7.6rem 7.8rem 6.8rem 9.8rem 3rem',
         'grid-template-columns:2.4rem 1.7fr 7.6rem 7.8rem 6.8rem 10.5rem 7.2rem'),
    ], 'cust')
    return _css(h, CUST_CSS)


LC_CSS = """
.th-h h2{font-size:1.75rem!important;line-height:1.2}
.th-h .coline{margin-top:.15rem;color:#2E7D5B;font-weight:700}
.aisum2{display:block;width:calc(100% - 2.2rem);margin:.6rem 1.1rem 0;text-align:left;border:1.5px solid transparent;border-radius:14px;cursor:pointer;
  background:linear-gradient(#fff,#fff) padding-box,linear-gradient(110deg,#8B5CF6,#EC4899 60%,#FB923C) border-box;padding:.45rem .75rem;font:inherit;flex:none}
.aisum2 .aih{display:flex;align-items:center;gap:.5rem;font-size:.74rem}
.aisum2 .aih b{background:linear-gradient(90deg,#7C3AED,#DB2777);-webkit-background-clip:text;background-clip:text;color:transparent}
.aisum2 .aih .grp{font-size:.85rem!important;padding:.12rem .7rem!important;font-weight:800}
.aisum2 .ait{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:.9rem;line-height:1.45;color:#2A1F33;margin-top:.15rem}
.aisum2.open .ait{-webkit-line-clamp:unset}
.sr1x{display:flex;justify-content:space-between;align-items:flex-start;gap:.6rem}
.srr{display:flex;flex-direction:column;align-items:flex-end;gap:.3rem}
.srr .more{margin:0}
.gbox .flt button,.flt button{padding:.05rem .55rem!important;font-size:.74rem!important;min-height:1.8rem!important}
.fzone{display:flex!important;flex-wrap:wrap;align-items:center;gap:.4rem}
.tpsel{min-height:1.8rem;border:1.5px solid var(--line);border-radius:99px;padding:0 1.6rem 0 .7rem;background-color:#fff;font:inherit;font-size:.74rem;font-weight:600;color:var(--ink);max-width:100%}
.tpc{font-size:.8rem!important;padding:.12rem .6rem!important;border-radius:8px!important}
.th2{display:block!important}
.th2 .nmrow{display:flex;align-items:flex-start;justify-content:space-between;gap:.6rem}
.th2 .nmc{flex:1;min-width:0}
.th2 .tags{padding-top:.35rem}
.th2 .coline{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.aisum2 .aih{justify-content:space-between}
.srl{display:flex;flex-direction:column;gap:.3rem;min-width:0}
.srs{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center}
.sr1x .more{margin:0!important;flex:none}
.statbox .purp{line-height:1.6;padding-bottom:.05rem}
.prow{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .6rem}
.prow .sr3{border-top:0!important;padding-top:0!important;flex-wrap:wrap}
.prow .addn{padding:.05rem .5rem!important;font-size:.72rem!important;min-height:0!important}
.pancol .statbox{padding:.5rem .8rem .45rem!important;gap:.15rem!important}
.th2{padding:.55rem 1.1rem!important}
.th2 h2{line-height:1.15!important}
.th2 small{line-height:1.4}
.gbox .gh{padding:.5rem 1.1rem!important}
.fzone{padding:.4rem .6rem!important;gap:.3rem!important}
.fzone .flt{gap:.2rem!important}
.fzone .flt button{padding:.05rem .45rem!important;font-size:.72rem!important;min-height:1.75rem!important}
.fzone{flex-wrap:nowrap!important}
.fzone .flt{flex:0 1 auto;min-width:0;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap!important}
.fzone .flt button{white-space:nowrap;flex:none}
.fzone .tpsel{flex:0 0 auto;width:6.6rem;font-size:.72rem;margin-left:auto;padding:0 1.3rem 0 .55rem;text-overflow:ellipsis}
"""


def linechat(h):
    h = _r(h, [
        ("""<div class="th-h"><div>${nmH}<small>${c.real&&c.real!==c.name?esc(c.real)+' · ':''}LINE: ${esc(c.line)}</small></div><div class="tags"><span class="grp ${grp[1]}">${esc(grp[0])}</span>${warnIc(warnLv(c,a),'2.1rem')}<button type="button" class="btn ghost sm pinfo" data-act="pop" aria-label="เปิดแผงเครื่องมือ">เครื่องมือ</button></div><div class="gtags"><span class="tg">${memOf(c)?'เป็นสมาชิก':'ไม่ได้เป็นสมาชิก'}</span><span class="tg">${SEG[c.seg]}</span>${c.co?`<span class="tg tg-co">🏢 ${esc(c.co)}</span>`:''}</div></div>""",
         """<div class="th-h th2"><div class="nmrow"><div class="nmc">${nmH}</div><div class="tags"><span class="tg">${memOf(c)?'เป็นสมาชิก':'ไม่ได้เป็นสมาชิก'}</span><span class="tg">${SEG[c.seg]}</span>${warnIc(warnLv(c,a),'2.1rem')}<button type="button" class="btn ghost sm pinfo" data-act="pop" aria-label="เปิดแผงเครื่องมือ">เครื่องมือ</button></div></div><small>${c.real&&c.real!==c.name?esc(c.real)+' · ':''}LINE: ${esc(c.line)}</small>${c.co?`<small class="coline">🏢 ${esc(c.co)}</small>`:''}</div>"""),
        ("""<div class="aisum"><h3>✦ AI สรุป</h3><p>${esc(a.sum)}</p></div>""",
         """<button type="button" class="aisum2" onclick="this.classList.toggle('open')" title="กดเพื่ออ่านทั้งหมด"><span class="aih"><span class="grp ${grp[1]}">${esc(grp[0])}</span><b>✦ AI สรุป</b></span><span class="ait">${esc(a.sum)}</span></button>"""),
        ("""<div class="statbox"><div class="sr1"><span class="bs ${bs[1]}">${bs[0]}</span>${bd.unpaid?'<span class="tg tg-red">ยังไม่ชำระ</span>':''}<button type="button" class="more" data-act="more">ดูเพิ่มเติม ›</button></div>${(()=>{const p=bparts(c),pu=purpOf(c);return p?`<div class="sr2"><div class="rmw"><span class="rmb">${esc(p[0])}</span><span class="rmr">${esc(p[1])}</span></div>${pu?`<div class="purp">${esc(pu)}</div>`:''}</div>`:''})()}""",
         """<div class="statbox"><div class="sr1x"><div class="srl">${(()=>{const p=bparts(c),pu=purpOf(c),st=`<div class="srs"><span class="bs ${bs[1]}">${bs[0]}</span>${bd.unpaid?'<span class="tg tg-red">ยังไม่ชำระ</span>':''}</div>`;return p?`<div class="rmw"><span class="rmb">${esc(p[0])}</span><span class="rmr">${esc(p[1])}</span></div>${st}<div class="prow">${pu?`<div class="purp">${esc(pu)}</div>`:''}<div class="sr3">${noteH}</div></div>`:`${st}<div class="prow"><div class="purp">ยังไม่มีการจอง</div><div class="sr3">${noteH}</div></div>`})()}</div><button type="button" class="more" data-act="more">ดูเพิ่มเติม ›</button></div>"""),
        ("""<button type="button" data-sort="ai" aria-pressed="${S.sort==='ai'}">ด่วนก่อน</button><button type="button" data-sort="new" aria-pressed="${S.sort==='new'}">ล่าสุด</button>""",
         """<button type="button" data-sort="new" aria-pressed="${S.sort==='new'}">ล่าสุด</button><button type="button" data-sort="ai" aria-pressed="${S.sort==='ai'}">ด่วน</button>"""),
        ("const S={f:'all',tp:'all',q:'',sel:2,sort:'ai',", "const S={f:'all',tp:'all',q:'',sel:2,sort:'new',"),
        ("""<div class="fzone"><div class="flt" role="tablist" aria-label="สถานะ">${fl}</div></div>""",
         """<div class="fzone"><div class="flt" role="tablist" aria-label="สถานะ">${fl}</div><select class="tpsel" aria-label="ประเภทเรื่อง" onchange="S.tp=this.value;render()">${[['all','ทุกเรื่อง',all.length],...(nu?[['urg','ด่วน',nu]]:[]),...TOPICS.filter(t=>tc[t[0]]).map(t=>[t[0],t[1],tc[t[0]]])].map(([k,t,v])=>`<option value="${k}" ${S.tp===k?'selected':''}>${k==='all'?'ทุกเรื่อง':t+' ('+v+')'}</option>`).join('')}</select></div>"""),
        ('ดูเพิ่มเติม ›</button></div><div class="sr3">${noteH}</div></div>`;', 'ดูเพิ่มเติม ›</button></div></div>`;'),
        ('const floor=7.9*parseFloat(', 'const floor=5.2*parseFloat('),
    ], 'linechat')
    return _css(h, LC_CSS)


def apply(M):
    if 'cust' in M:
        M['cust'] = cust(M['cust'])
    if 'linechat' in M:
        M['linechat'] = linechat(M['linechat'])
    return M
