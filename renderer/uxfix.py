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
.fbar2{flex-wrap:nowrap;gap:.45rem;padding:.5rem .7rem;align-items:center}
.fbar2 .sortchips{display:flex;gap:.25rem;flex:none}
.fbar2 .sortchips button{min-height:2.3rem!important;padding:0 .85rem!important;font-size:.88rem!important;white-space:nowrap}
.fbar2 select{min-height:2.3rem!important;font-size:.88rem!important;padding:0 1.7rem 0 .8rem!important;min-width:0;max-width:12rem}
.fbar2 .iconbtn{flex:none;width:2.1rem;height:2.1rem}
.fbar2 .sortsel{font-size:.88rem;white-space:nowrap;flex:none}
.fbar2 #resetF{white-space:nowrap;font-size:.84rem;flex:none}
@media (max-width:1000px){.fbar2{flex-wrap:wrap}}
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
.rep{display:flex!important;align-items:flex-end;gap:.4rem;width:100%!important;box-sizing:border-box;max-width:none!important}
.rep textarea{flex:1 1 auto;min-width:0;width:auto!important}
.rep>.btn{flex:none}
.rep{flex-wrap:wrap;row-gap:.2rem}
.rep .lnbar{flex:0 0 100%;margin-bottom:-.1rem}
.rep .lnb{width:2.3rem;height:2.1rem}
.lnbar{display:flex;gap:.15rem;align-items:center;flex:none}
.lnb{border:0;background:none;color:var(--soft);width:2.6rem;height:2.6rem;border-radius:12px;display:grid;place-items:center;cursor:pointer}
.lnb:hover,.lnb.on{background:#F3EEF9;color:var(--purple)}
.stkpan{border-top:1.5px solid var(--line);background:#fff;flex:none}
.stktabs{display:flex;gap:.3rem;padding:.35rem .6rem;border-bottom:1px solid var(--line);overflow-x:auto}
.stktabs button{border:0;background:none;border-radius:10px;padding:.15rem;width:2.6rem;height:2.6rem;flex:none;cursor:pointer}
.stktabs button.on{background:#F3EEF9}.stktabs img{width:100%;height:100%;object-fit:contain}
.stkgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(4.6rem,1fr));gap:.3rem;padding:.5rem .6rem;max-height:13rem;overflow-y:auto}
.stkgrid button{border:0;background:none;border-radius:12px;padding:.25rem;cursor:pointer;aspect-ratio:1}
.stkgrid button:hover{background:#F6F0FB}.stkgrid img{width:100%;height:100%;object-fit:contain}
.b .stk{display:block;width:7.5rem;height:auto;margin:.1rem 0}
.b .attimg{max-width:14rem;max-height:14rem;border-radius:12px;display:block;margin:.2rem 0}
.b a.attfile{display:inline-flex;gap:.3rem;align-items:center;color:var(--purple);text-decoration:underline}
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
.th2 .nmrow{flex-direction:column-reverse;align-items:stretch;gap:.1rem}
.th2 .tags{justify-content:flex-end;padding-top:0;height:1.6rem;align-items:center;overflow:visible}
.th2 .tags svg,.th2 .tags img{max-height:1.4rem}
.th2 .nmb{max-width:100%;min-width:0;display:inline-flex;align-items:center;min-height:0!important;height:auto!important;padding:0!important;margin:0!important;vertical-align:top}
.th2 .nmc{display:flex;flex-direction:column;align-items:flex-start;gap:0}
.th2 .nmc small{max-width:100%;margin:0}
.th2 .nmc .nmb+small{margin-top:.3rem}
.th2 .coline{margin-top:.15rem!important}
.th2 .nmrow{flex:none}
.th2 .nmb h2{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.th2 .coline{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.aisum2 .aih{justify-content:space-between}
.aisum2{position:relative;z-index:3;margin-top:-1.4rem!important;margin-bottom:.35rem!important;box-shadow:0 6px 18px rgba(46,31,43,.13),0 1px 3px rgba(46,31,43,.08)}
.srl{display:flex;flex-direction:column;gap:.3rem;min-width:0}
.srs{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center}
.sr1x .more{margin:0!important;flex:none}
.statbox .purp{line-height:1.6;padding-bottom:.05rem}
.prow{display:flex;flex-direction:column;align-items:flex-start;gap:.2rem}
.prow .sr3{border-top:0!important;padding-top:0!important;flex-wrap:nowrap!important;white-space:nowrap;overflow-x:auto;scrollbar-width:none;max-width:100%}
.prow .sr3 .sn{white-space:nowrap}
.prow .sr3 .addn{order:-1;flex:none}
.prow{max-width:100%;min-width:0}
.prow .addn{padding:.05rem .5rem!important;font-size:.72rem!important;min-height:0!important}
.pancol .statbox{padding:.5rem .8rem .45rem!important;gap:.15rem!important}
.th2{padding:.55rem 1.1rem!important;display:flex!important;flex-direction:column!important;flex-wrap:nowrap!important;align-items:stretch!important;justify-content:flex-start;overflow:hidden;box-sizing:border-box}
.th2 small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pancol .statbox{justify-content:flex-start!important;overflow:hidden;box-sizing:border-box}
.th2 h2{line-height:1.15!important}
.th2 small{line-height:1.4}
.gbox .gh{padding:.5rem 1.1rem!important}
.fzone{padding:.4rem .6rem!important;gap:.3rem!important}
.fzone .flt{gap:.2rem!important}
.fzone .flt button{padding:.05rem .45rem!important;font-size:.72rem!important;min-height:1.75rem!important}
.fzone{flex-wrap:nowrap!important;flex-direction:column!important;align-items:stretch!important;justify-content:center;gap:.4rem!important}
.fz1{display:flex;align-items:center;gap:.3rem;min-width:0}
.fzone .srch{min-height:2.2rem;padding:.25rem .75rem;font-size:.88rem;box-sizing:border-box}
@media (min-width:901px){.listcol,.thrcol,.pancol{height:calc((100vh - 6.4rem) * 1.5)!important}
#app{padding-bottom:1.2rem!important}.listcol,.thrcol,.pancol{min-height:39rem!important}}
.th2 .nmb h2{line-height:1.55!important;padding:.05rem 0 .2rem!important;margin:0!important}
.th2 .nmc .nmb+small{margin-top:.35rem}
.th2 .nmc small{line-height:1.5}
.th2{padding-bottom:1.9rem!important}
.fzone .flt{flex:0 1 auto;min-width:0;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap!important}
.fzone .flt button{white-space:nowrap;flex:none}
.fzone .tpsel{flex:0 0 auto;width:6.6rem;font-size:.72rem;margin-left:auto;padding:0 1.3rem 0 .55rem;text-overflow:ellipsis}
"""


def linechat(h):
    h = _r(h, [
        ("""<div class="th-h"><div>${nmH}<small>${c.real&&c.real!==c.name?esc(c.real)+' · ':''}LINE: ${esc(c.line)}</small></div><div class="tags"><span class="grp ${grp[1]}">${esc(grp[0])}</span>${warnIc(warnLv(c,a),'2.1rem')}<button type="button" class="btn ghost sm pinfo" data-act="pop" aria-label="เปิดแผงเครื่องมือ">เครื่องมือ</button></div><div class="gtags"><span class="tg">${memOf(c)?'เป็นสมาชิก':'ไม่ได้เป็นสมาชิก'}</span><span class="tg">${SEG[c.seg]}</span>${c.co?`<span class="tg tg-co">🏢 ${esc(c.co)}</span>`:''}</div></div>""",
         """<div class="th-h th2"><div class="nmrow"><div class="nmc">${nmH}<small>${c.real&&c.real!==c.name?esc(c.real)+' · ':''}LINE: ${esc(c.line)}</small>${c.co?`<small class="coline">🏢 ${esc(c.co)}</small>`:''}</div><div class="tags"><span class="tg">${memOf(c)?'เป็นสมาชิก':'ไม่ได้เป็นสมาชิก'}</span><span class="tg">${SEG[c.seg]}</span>${warnIc(warnLv(c,a),'1.35rem')}<button type="button" class="btn ghost sm pinfo" data-act="pop" aria-label="เปิดแผงเครื่องมือ">เครื่องมือ</button></div></div></div>"""),
        ("""<div class="aisum"><h3>✦ AI สรุป</h3><p>${esc(a.sum)}</p></div>""",
         """<button type="button" class="aisum2" onclick="this.classList.toggle('open')" title="กดเพื่ออ่านทั้งหมด"><span class="aih"><span class="grp ${grp[1]}">${esc(grp[0])}</span><b>✦ AI สรุป</b></span><span class="ait">${esc(a.sum)}</span></button>"""),
        ("""<div class="statbox"><div class="sr1"><span class="bs ${bs[1]}">${bs[0]}</span>${bd.unpaid?'<span class="tg tg-red">ยังไม่ชำระ</span>':''}<button type="button" class="more" data-act="more">ดูเพิ่มเติม ›</button></div>${(()=>{const p=bparts(c),pu=purpOf(c);return p?`<div class="sr2"><div class="rmw"><span class="rmb">${esc(p[0])}</span><span class="rmr">${esc(p[1])}</span></div>${pu?`<div class="purp">${esc(pu)}</div>`:''}</div>`:''})()}""",
         """<div class="statbox"><div class="sr1x"><div class="srl">${(()=>{const p=bparts(c),pu=purpOf(c),st=`<div class="srs"><span class="bs ${bs[1]}">${bs[0]}</span>${bd.unpaid?'<span class="tg tg-red">ยังไม่ชำระ</span>':''}</div>`;return p?`<div class="rmw"><span class="rmb">${esc(p[0])}</span><span class="rmr">${esc(p[1])}</span></div>${st}<div class="prow">${pu?`<div class="purp">${esc(pu)}</div>`:''}<div class="sr3">${noteH}</div></div>`:`${st}<div class="prow"><div class="purp">ยังไม่มีการจอง</div><div class="sr3">${noteH}</div></div>`})()}</div><button type="button" class="more" data-act="more">ดูเพิ่มเติม ›</button></div>"""),
        ("""<button type="button" data-sort="ai" aria-pressed="${S.sort==='ai'}">ด่วนก่อน</button><button type="button" data-sort="new" aria-pressed="${S.sort==='new'}">ล่าสุด</button>""",
         """<button type="button" data-sort="new" aria-pressed="${S.sort==='new'}">ล่าสุด</button><button type="button" data-sort="ai" aria-pressed="${S.sort==='ai'}">ด่วน</button>"""),
        ("const S={f:'all',tp:'all',q:'',sel:2,sort:'ai',", "const S={f:'all',tp:'all',q:'',sel:2,sort:'new',"),
        ("""<div class="fzone"><div class="flt" role="tablist" aria-label="สถานะ">${fl}</div></div>""",
         """<div class="fzone"><div class="fz1"><div class="flt" role="tablist" aria-label="สถานะ">${fl}</div><select class="tpsel" aria-label="ประเภทเรื่อง" onchange="S.tp=this.value;render()">${[['all','ทุกเรื่อง',all.length],...(nu?[['urg','ด่วน',nu]]:[]),...TOPICS.filter(t=>tc[t[0]]).map(t=>[t[0],t[1],tc[t[0]]])].map(([k,t,v])=>`<option value="${k}" ${S.tp===k?'selected':''}>${k==='all'?'ทุกเรื่อง':t+' ('+v+')'}</option>`).join('')}</select></div><input class="srch" id="q" type="search" placeholder="ค้นหาชื่อ ชื่อ LINE ห้อง หรือเรื่อง" value="${esc(S.q)}" aria-label="ค้นหาแชท"></div>"""),
        ('<input class="srch" id="q" type="search" placeholder="ค้นหาชื่อ ชื่อ LINE ห้อง หรือเรื่อง" value="${esc(S.q)}" aria-label="ค้นหาแชท">\n', ''),
        ('ดูเพิ่มเติม ›</button></div><div class="sr3">${noteH}</div></div>`;', 'ดูเพิ่มเติม ›</button></div></div>`;'),
        ('const floor=7.9*parseFloat(', 'const floor=10.2*parseFloat('),
        # ความสูงหัวกล่องคงที่ทุกแชท ไม่ยืดหดตามเนื้อหา
        ('const H=Math.ceil(Math.max(rh(th),rh(sb),gH+rh(fz),floor));', 'const H=Math.ceil(Math.max(gH+rh(fz),floor));'),
    ], 'linechat')
    return _css(h, LC_CSS)


def apply(M):
    if 'cust' in M:
        M['cust'] = custprof(cust(M['cust']))
    if 'linechat' in M:
        M['linechat'] = chatsave(linechat(M['linechat']))
    if 'hk' in M:
        M['hk'] = hk(M['hk'])
    if 'book' in M:
        M['book'] = bkback(bkpage(M['book']))
    if 'home' in M:
        M['home'] = homepop(M['home'])
    if 'fin' in M:
        M['fin'] = finsave(M['fin'])
    if 'mkt' in M:
        M['mkt'] = mktsend(M['mkt'])
    for k in ('hk', 'crmtool', 'cust', 'crm', 'mkt'):
        if k in M:
            M[k] = modsave(M[k], k)
    return M


# ---------- หน้าแชท LINE: ปุ่มบันทึกจริง (ต้องรัน supabase/07_chat.sql) ----------
CHAT_HELPER = r"""
function ppChat(k,d){
  const body=JSON.stringify(Object.assign({k},d||{}));
  return fetch(top.location.origin+'/api/app?part=chat',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body})
   .then(r=>r.json().catch(()=>({})).then(j=>{if(!r.ok)throw new Error(j.error||('รหัส '+r.status));try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}return j}));
}
/* ---------- สื่อในแชท: รูป / สติกเกอร์ (ชุดฟรีที่ LINE ให้บัญชีทางการใช้) / ไฟล์ ---------- */
const LNI={img:'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-8 9"/></svg>',
 stk:'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M8.5 14.5c1.8 2 5.2 2 7 0"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>',
 file:'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11.5l-8 8a5 5 0 01-7-7l8.5-8.5a3.5 3.5 0 015 5L10 17.5a2 2 0 01-3-3l7.5-7.5"/></svg>'};
const STKP=[{p:11537,a:52002734,n:40},{p:11538,a:51626494,n:40},{p:11539,a:52114110,n:40},{p:446,a:1988,n:40},{p:789,a:10855,n:40}];
const stkUrl=id=>`https://stickershop.line-scdn.net/stickershop/v1/sticker/${id}/android/sticker.png`;
function stkPanel(){const P=STKP[S.stkP||0];
  return `<div class="stkpan"><div class="stktabs">${STKP.map((x,i)=>`<button type="button" data-act="stkp" data-i="${i}" class="${i===(S.stkP||0)?'on':''}"><img src="${stkUrl(x.a)}" alt="ชุด ${i+1}" loading="lazy"></button>`).join('')}</div>
   <div class="stkgrid">${Array.from({length:P.n},(_,i)=>P.a+i).map(id=>`<button type="button" data-act="stks" data-p="${P.p}" data-s="${id}"><img src="${stkUrl(id)}" alt="สติกเกอร์" loading="lazy"></button>`).join('')}</div></div>`}
function sendSticker(p,sid){const c=CV.find(x=>x.id===S.sel);if(!c||window.__ppSending)return;window.__ppSending=1;
  ppChat('send',{key:c.key,body:'[สติกเกอร์]',media:{type:'sticker',pkg:String(p),sid:String(sid)}}).then(()=>{c.m.push(['s','',nowTm(),[{t:'stk',src:stkUrl(sid),name:'สติกเกอร์'}]]);S.stk=false;c.st='wait';c.read=true;render();
    toast(String(c.key).startsWith('db:')?'ส่งสติกเกอร์แล้ว':'บันทึกแล้ว · แชทตัวอย่าง')}).catch(ppChatFail).finally(()=>{window.__ppSending=0})}
function ppImgData(file){return new Promise((ok,no)=>{const u=URL.createObjectURL(file),im=new Image();im.onload=()=>{const k=Math.min(1,1600/Math.max(im.width,im.height)),cv=document.createElement('canvas');
  cv.width=Math.round(im.width*k);cv.height=Math.round(im.height*k);cv.getContext('2d').drawImage(im,0,0,cv.width,cv.height);URL.revokeObjectURL(u);ok(cv.toDataURL('image/jpeg',.8))};im.onerror=()=>no(new Error('อ่านรูปไม่ได้'));im.src=u})}
function ppFileData(file){return new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=()=>no(new Error('อ่านไฟล์ไม่ได้'));r.readAsDataURL(file)})}
function ppChatFail(e){const msg='⚠️ บันทึกไม่สำเร็จ: '+e.message;try{toast(msg)}catch(_){console.error(msg)}}
try{const k=sessionStorage.getItem('pp_lc_sel'),c=CV.find(x=>x.key===k);if(c)S.sel=c.id}catch(_){}
"""

CHAT_SAVE = [
    # หมายเหตุ: เก็บกับแชท (บันทึกจริง)
    ("const snOf=c=>{const h=hbOf(c);return h?(h.note?h.note.split(' · '):[]):c.sn};",
     "const snOf=c=>c.sn||[];"),
    ("function setNotes(c,arr){const h=hbOf(c);if(h){h.note=arr.join(' · ');try{parent.postMessage({pbr:'bknote',bk:h.bk,note:h.note},'*')}catch(_){}}else c.sn=arr}",
     "function setNotes(c,arr){const old=c.sn||[];c.sn=arr;ppChat('notes',{key:c.key,notes:arr}).catch(e=>{c.sn=old;render();ppChatFail(e)})}"),
    # ส่งข้อความ: แชทจริงส่งเข้า LINE แล้วจึงแสดง · แชทตัวอย่างบันทึกอย่างเดียว
    ("""  c.m.push(['s',txt,nowTm(),PEND.slice()]); PEND=[]; $('#rt').value=''; c.st='wait'; c.ago=0; render(); toast('ส่งแล้ว · สถานะเป็น "รอตอบ" (ต้นแบบ: ยังไม่ได้ส่งเข้า LINE จริง)');""",
     """  if(window.__ppSending)return;window.__ppSending=1;const sb=document.querySelector('[data-act="send"]');if(sb){sb.disabled=true;sb.textContent='กำลังส่ง…'}
  const items=PEND.slice();let n=0;
  const one=(body,media,att)=>ppChat('send',{key:c.key,body,media}).then(j=>{c.m.push(['s',att?'':body,nowTm()].concat(att?[att]:[]));n++;return j});
  items.reduce((pr,a)=>pr.then(()=>a.t==='img'?ppImgData(a.f).then(d=>one('[รูปภาพ]',{type:'image',data:d},[{t:'img',src:d,name:a.name}]))
      :ppFileData(a.f).then(d=>one('[ไฟล์] '+a.name,{type:'file',name:a.name,data:d},[{t:'file',name:a.name,size:a.size}]))),Promise.resolve())
   .then(()=>txt?one(txt):null).then(j=>{PEND=[]; if($('#rt'))$('#rt').value=''; c.st='wait'; c.ago=0; c.read=true; render();
    toast(c.key&&String(c.key).startsWith('db:')?`ส่งเข้า LINE แล้ว (${n} ข้อความ)`:'บันทึกแล้ว · แชทตัวอย่าง ไม่ได้ส่งเข้า LINE')})
   .catch(e=>{if(n){PEND=PEND.slice(n);render()}ppChatFail(e)}).finally(()=>{window.__ppSending=0;const b2=document.querySelector('[data-act="send"]');if(b2){b2.disabled=false;b2.textContent='ส่ง'}});"""),
    # เก็บไฟล์จริงไว้ส่ง
    ("PEND.push(kind==='img'?{t:'img',name:f.name,size:fsz(f.size),src:URL.createObjectURL(f)}:{t:'file',name:f.name,size:fsz(f.size)})",
     "if(kind!=='img'&&f.size>2.5*1048576){toast('ไฟล์ '+f.name+' ใหญ่เกิน 2.5 MB');return}PEND.push(kind==='img'?{t:'img',name:f.name,size:fsz(f.size),src:URL.createObjectURL(f),f}:{t:'file',name:f.name,size:fsz(f.size),f})"),
    # แสดงรูป/สติกเกอร์/ไฟล์ในบับเบิล
    ("function attH(at){return (at||[]).map(a=>a.t==='img'?`<img class=\"attimg\" src=\"${a.src}\" alt=\"${esc2(a.name)}\">`:`<span class=\"attfile\"><b>${esc2(a.name)}</b> <small>${esc2(a.size)}</small></span>`).join('')}",
     "function attH(at){return (at||[]).map(a=>a.t==='stk'?`<img class=\"stk\" src=\"${a.src}\" alt=\"สติกเกอร์\">`:a.t==='img'?`<a href=\"${a.src}\" target=\"_blank\" rel=\"noopener\"><img class=\"attimg\" src=\"${a.src}\" alt=\"${esc2(a.name)}\"></a>`:"
     "(a.u?`<a class=\"attfile\" href=\"${a.u}\" target=\"_blank\" rel=\"noopener\">📎 <b>${esc2(a.name)}</b> <small>${esc2(a.size||'')}</small></a>`:`<span class=\"attfile\">📎 <b>${esc2(a.name)}</b> <small>${esc2(a.size||'')}</small></span>`)).join('')}"),
    # ช่องพิมพ์แบบแอป LINE: ปุ่มรูป / สติกเกอร์ / ไฟล์
    ("<div class=\"plw\"><button type=\"button\" class=\"plus\" data-act=\"plus\" aria-label=\"เพิ่มภาพหรือไฟล์เอกสาร\" aria-expanded=\"false\">+</button><div class=\"plm\" id=\"plm\" hidden><button type=\"button\" data-act=\"pickimg\">ภาพ</button><button type=\"button\" data-act=\"pickfile\">ไฟล์เอกสาร</button></div></div>",
     "<div class=\"lnbar\"><button type=\"button\" class=\"lnb\" data-act=\"pickimg\" title=\"ส่งรูป\" aria-label=\"ส่งรูป\">${LNI.img}</button><button type=\"button\" class=\"lnb${S.stk?' on':''}\" data-act=\"stk\" title=\"สติกเกอร์\" aria-label=\"สติกเกอร์\">${LNI.stk}</button><button type=\"button\" class=\"lnb\" data-act=\"pickfile\" title=\"ส่งไฟล์\" aria-label=\"ส่งไฟล์\">${LNI.file}</button></div>"),
    ("<div class=\"attrow\" id=\"att\">${chipsH()}</div>", "<div class=\"attrow\" id=\"att\">${chipsH()}</div>${S.stk?stkPanel():''}"),
    ("else if(a==='pickimg'){$('#plm').hidden=true;$('#fiImg').click()}", "else if(a==='pickimg'){$('#fiImg').click()}\n    else if(a==='stk'){S.stk=!S.stk;render()}\n    else if(a==='stkp'){S.stkP=+b.dataset.i;render()}\n    else if(a==='stks'){sendSticker(b.dataset.p,b.dataset.s)}"),
    ("else if(a==='pickfile'){$('#plm').hidden=true;$('#fiDoc').click()}", "else if(a==='pickfile'){$('#fiDoc').click()}"),
    # ปิดเคส
    ("else if(a==='close'){const c=CV.find(x=>x.id===S.sel);c.st='done';render();toast('ปิดเคสแล้ว · งานด่วนในหน้าแรกจะหายไปด้วย')}",
     "else if(a==='close'){const c=CV.find(x=>x.id===S.sel),o=c.st;c.st='done';c.read=true;render();ppChat('close',{key:c.key}).then(()=>toast('ปิดเคสแล้ว · งานด่วนในหน้าแรกจะหายไปด้วย')).catch(e=>{c.st=o;render();ppChatFail(e)})}"),
    # เปลี่ยนชื่อแชท
    ("else if(a==='nmsave'){const v=$('#nmI').value.trim();const c=CV.find(x=>x.id===S.sel);if(v)c.name=v;S.edn=false;render();toast('เปลี่ยนชื่อแชทแล้ว (ต้นแบบ)')}",
     "else if(a==='nmsave'){const v=$('#nmI').value.trim();const c=CV.find(x=>x.id===S.sel),o=c.name;if(v)c.name=v;S.edn=false;render();if(v)ppChat('name',{key:c.key,alias:v}).then(()=>toast('เปลี่ยนชื่อแชทแล้ว')).catch(e=>{c.name=o;render();ppChatFail(e)})}"),
    ("else if(a==='nmreal'){const c=CV.find(x=>x.id===S.sel);c.name=c.real;S.edn=false;render()}",
     "else if(a==='nmreal'){const c=CV.find(x=>x.id===S.sel),o=c.name;c.name=c.real;S.edn=false;render();ppChat('name',{key:c.key,alias:c.real}).then(()=>toast('ใช้ชื่อจริงแล้ว')).catch(e=>{c.name=o;render();ppChatFail(e)})}"),
    # เปิดอ่านแชท -> บันทึกว่าอ่านแล้ว
    ("if(b=q('.cv')){S.sel=+b.dataset.id;",
     "if(b=q('.cv')){S.sel=+b.dataset.id;{const c=CV.find(x=>x.id===S.sel);if(c&&unreadOf(c)){c.read=true;ppChat('read',{key:c.key}).catch(()=>{})}}"),
    # จำแชทที่เปิดอยู่ ตอนหน้าจอโหลดข้อมูลใหม่
    ("function render(){\n  const keep=",
     "function render(){\n  try{const c=CV.find(x=>x.id===S.sel);if(c)sessionStorage.setItem('pp_lc_sel',c.key)}catch(_){}\n  const keep="),
]


def chatsave(h):
    h = _r(h, CHAT_SAVE, 'linechat-save')
    k = h.index('function render(){')
    return h[:k] + CHAT_HELPER + h[k:]


# ---------- ลูกค้าและสมาชิก: หน้าโปรไฟล์ใหม่ + บันทึกจริง (ต้องรัน supabase/08_cust.sql) ----------
CUST_DETAIL = r"""function custDetail(c){
  const s=stat(c), t=S.detail.tab, ed=S.edit, k=c.company?coOf(c.company):null, rooms=staysOf(c.id,true).length;
  const row=(lab,val,auto)=>`<div class="kvr"><span>${lab}${auto?'<i class="auto">คำนวณอัตโนมัติ</i>':''}</span><div>${val}</div></div>`;
  let h=`<button class="back" data-back>${ico('left')}${S.fromBk?'กลับหน้าการจอง':'กลับรายการลูกค้า'}</button>
  <div class="dhead"><div class="avatar" aria-hidden="true">${esc(initial(c.name))}</div>
    <div><h3>${esc(c.name)}</h3><div class="sub">${c.memberNo?'รหัสสมาชิก '+pbm(c.memberNo):'ยังไม่เป็นสมาชิก'}</div></div>
    <div class="lvl lvl2"><small>กลุ่มลูกค้า</small>${badge(s.st)}</div></div>`;
  h+=`<div class="stats stats4"><div class="stat"><small>จำนวนครั้งที่พัก</small><b>${s.n} ครั้ง</b></div><div class="stat"><small>จำนวนห้องพักสะสม</small><b>${rooms} ห้อง</b></div><div class="stat"><small>ยอดใช้จ่ายรวม</small><b>${fmt(s.spend)} ฿</b></div><div class="stat"><small>พักล่าสุด</small><b style="font-size:1rem">${s.last?fD(s.last,{day:'numeric',month:'short',year:'2-digit'}):'-'}</b></div></div>`;
  h+=`<div class="pbar">${c.memberNo?'':`<button class="btn sm" data-reg="${c.id}">${ico('plus')}สมัครสมาชิก</button>`}<div class="dtabs dtabs2" role="tablist"><button role="tab" data-tab="info" aria-selected="${t==='info'}">ข้อมูล</button><button role="tab" data-tab="hist" aria-selected="${t==='hist'}">ประวัติ</button></div></div>`;
  if(t==='hist') return h+`<div class="dbox dbox2"><h4>ประวัติการพัก <span class="hint" style="font-family:inherit;font-size:.8rem;color:var(--soft)">กดเลขการจองเพื่อดูรายละเอียด</span></h4>${histTable(staysOf(c.id,true))}</div>`;
  h+=`<div class="dbox dbox2"><h4>ข้อมูลลูกค้า ${ed?`<span><button class="btn ghost sm" data-cancel>ยกเลิก</button> <button class="btn sm" data-save>บันทึก</button></span>`:`<button class="btn ghost sm" data-edit>${ico('pen')}แก้ไขข้อมูล</button>`}</h4>`;
  if(S.err) h+=`<div class="err" role="alert">${esc(S.err)}</div>`;
  const GEN=['ชาย','หญิง','เพศหลากหลาย','ไม่ระบุ'];
  const coH=(k?`<button class="linkbtn" data-open="k:${k.id}">${esc(k.name)}</button>`:'<b>-</b>')+` <button class="btn ghost sm" data-copick style="margin-left:.5rem">ตั้งค่า</button>`;
  if(ed){
    h+=row('ชื่อ-สกุล *',`<input id="eName" value="${esc(c.name)}">`)+row('เพศ',`<select id="eGen"><option value="">— เลือก —</option>${GEN.map(x=>`<option ${x===c.gender?'selected':''}>${x}</option>`).join('')}</select>`)
      +row('เบอร์โทร *',`<input id="ePhone" type="tel" value="${esc(c.phone)}">`)+row('Line ID',`<input id="eLine" value="${esc(c.line)}">`)
      +row('วันเกิด',`<input id="eBd" type="date" value="${esc(c.bday||'')}">`)+row('ที่อยู่',`<input id="eAddr" value="${esc(c.addr)}">`)+row('จังหวัด',`<input id="eProv" value="${esc(c.prov)}">`)
      +row('บริษัท (ถ้ามี)',k?`<b>${esc(k.name)}</b>`:'<b>-</b>');
  } else {
    h+=row('ชื่อ-สกุล',`<b>${esc(c.name)}</b>`)+row('เพศ',`<b>${esc(c.gender||'-')}</b>`)+row('เบอร์โทร',`<b>${esc(c.phone)}</b>`)+row('Line ID',`<b>${esc(c.line||'-')}</b>`)+row('ที่อยู่',`<b>${esc(c.addr||'-')}</b>`)+row('จังหวัด',`<b>${esc(c.prov||'-')}</b>`)+row('วันเกิด',`<b>${esc(bdFmt(c.bday))}</b>`)+row('เอกสารยืนยันตัวตน',docH(c))
      +row('บริษัท (ถ้ามี)',coH);
  }
  h+=row('สถานะสมาชิก',c.memberNo?`<b>เป็นสมาชิก</b> · ${pbm(c.memberNo)} · ตั้งแต่ ${fD(c.memberSince)}`:`<b>ไม่เป็นสมาชิก</b>`)
    +row('กลุ่มลูกค้า',badge(s.st)+(s.last?` <span class="hint">พักล่าสุด ${Math.max(0,TODAY-s.last)} วันที่แล้ว</span>`:''),true)
    +row('วัตถุประสงค์การพัก',s.n?`<b>${s.purpose}</b> <span class="hint">(${s.purposeN} จาก ${s.n} ครั้ง)</span>`:(c.purpose?`<b>${esc(c.purpose)}</b> <span class="hint">(ระบุตอนสมัคร)</span>`:'<b>-</b>'),true)
    +row('ประเภทห้องพัก',s.n?`<b>${s.roomT}</b> <span class="hint">(${s.roomN} จาก ${s.n} ครั้ง)</span>`:'<b>-</b>',true)
    +row('ระยะเวลาการพัก',s.n?`<b>เฉลี่ย ${s.avgN.toFixed(1)} คืน / ครั้ง</b>`:'<b>-</b>',true)
    +row('ความต้องการพิเศษ',ed?`<input id="eSpec" value="${esc(c.special)}" placeholder="เช่น ไม่ทานเนื้อหมู ขอห้องชั้นล่าง">`:`<b>${esc(c.special||'-')}</b>`);
  return h+'</div>';
}
/* ---------- เอกสารยืนยันตัวตน (เลขบัตร/หนังสือเดินทาง + ภาพบัตรเมื่อลูกค้ายินยอม) ---------- */
const DOCT={id:'บัตรประชาชน',passport:'หนังสือเดินทาง'};
function thaiIdOk(d){if(!/^\d{13}$/.test(d))return false;let s=0;for(let i=0;i<12;i++)s+=+d[i]*(13-i);return (11-s%11)%10===+d[12]}
function docErr(t,no){const d=t==='id'?no.replace(/\D/g,''):no.replace(/[^0-9A-Za-z]/g,'');
  if(!d)return 'กรุณากรอกเลข'+DOCT[t];
  if(t==='id'){if(d.length!==13)return 'เลขบัตรประชาชนต้องมี 13 หลัก';if(!thaiIdOk(d))return 'เลขบัตรประชาชนไม่ถูกต้อง กรุณาตรวจอีกครั้ง'}
  else if(d.length<6||d.length>12)return 'เลขหนังสือเดินทางต้องมี 6–12 ตัว';
  return ''}
function docMask(t,no){no=String(no||'');return t==='id'&&no.length===13?`${no[0]}-xxxx-xxxxx-xx-${no[12]}`:(no.length>4?no.slice(0,2)+'x'.repeat(no.length-4)+no.slice(-2):'xxxx')}
function docH(c){const d=c.doc;
  if(!d)return `<b>-</b> <button class="btn ghost sm" data-docedit style="margin-left:.5rem">${ico('plus')}เพิ่มเอกสาร</button>`;
  const owner=!!d.no;
  return `<span class="hint" style="margin-right:.4rem">${DOCT[d.t]}</span><b class="num">${esc(owner&&S.docShow?(d.t==='id'?nidFmt(d.no):d.no):d.mask)}</b>
   ${owner?`<button class="btn ghost sm" data-docshow>${S.docShow?'ซ่อนเลข':'แสดงเลข'}</button>`:''}
   ${d.img?(owner?`<button class="btn ghost sm" data-docimg>ดูภาพบัตร</button>`:'<span class="hint">มีภาพบัตร (เจ้าของดูได้)</span>'):'<span class="hint">ไม่มีภาพบัตร</span>'}
   <button class="btn ghost sm" data-docedit>แก้ไข</button>
   ${d.img&&d.ca?`<div class="hint" style="margin-top:.2rem">ลูกค้ายินยอมให้เก็บภาพเมื่อ ${esc(bdFmt(d.ca))} · ลบภาพอัตโนมัติ 1 ปีหลังเข้าพักครั้งล่าสุด</div>`:''}`}
function docImg(c){
  openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">ภาพ${DOCT[c.doc.t]}</div><div class="bkn">${esc(c.name)} · เฉพาะเจ้าของ</div></div><div class="sb" id="dimg"><div class="empty">กำลังโหลด…</div></div><div class="sf"><button class="btn" data-close>ปิด</button></div>`,()=>{
    fetch(top.location.origin+'/api/app?part=idimg&gid='+encodeURIComponent(c.id),{credentials:'same-origin'}).then(r=>r.json()).then(j=>{
      $('dimg').innerHTML=j.img?`<img src="${j.img}" alt="ภาพบัตร" style="max-width:100%;border-radius:12px;border:1.5px solid var(--line)">`:`<div class="empty">${esc(j.error||'ไม่มีภาพ (อาจถูกลบตามระยะเก็บ 1 ปี)')}</div>`}).catch(()=>{$('dimg').innerHTML='<div class="empty">โหลดภาพไม่ได้</div>'})});
}
function ppImg(file){return new Promise((ok,no)=>{const u=URL.createObjectURL(file),im=new Image();im.onload=()=>{const k=Math.min(1,1200/Math.max(im.width,im.height)),cv=document.createElement('canvas');
  cv.width=Math.round(im.width*k);cv.height=Math.round(im.height*k);cv.getContext('2d').drawImage(im,0,0,cv.width,cv.height);URL.revokeObjectURL(u);ok(cv.toDataURL('image/jpeg',.72))};im.onerror=no;im.src=u})}
/* ช่องกรอกเอกสาร ใช้ทั้งในขั้นสมัครสมาชิกและหน้าแก้ไข · D={t,no,consent,img} */
function docFields(D){
  return `<div class="fld full"><span class="lb">ประเภทเอกสาร *</span><div class="regchips">${Object.entries(DOCT).map(([k,v])=>`<button type="button" data-dt="${k}" aria-pressed="${D.t===k}">${v}</button>`).join('')}</div></div>
   <div class="fld full consent"><label class="ck"><input type="checkbox" id="dcon" ${D.consent?'checked':''}> <span>แจ้งลูกค้าแล้วว่าโรงแรมเก็บข้อมูลเพื่อทะเบียนผู้พักตามกฎหมาย และ<b>ลูกค้ายินยอมให้เก็บภาพบัตร</b></span></label>
    <small class="hint">ภาพบัตรไม่บังคับ · ดูได้เฉพาะเจ้าของ · ลบอัตโนมัติ 1 ปีหลังเข้าพักครั้งล่าสุด</small></div>
   <div class="fld full"><span class="lb">ภาพบัตร (ถ้ามี)</span>${D.img?`<div class="docprev"><img src="${D.img}" alt="ภาพบัตร"><button type="button" class="btn ghost sm" id="dimgx">ลบภาพ</button></div>`:
     `<label class="btn ghost docpick${D.consent?'':' off'}"><input type="file" id="dfile" accept="image/*" capture="environment" ${D.consent?'':'disabled'} hidden>${ico('plus')} ถ่ายรูป / เลือกรูปบัตร (ระบบกรอกข้อมูลให้อัตโนมัติ)</label>${D.consent?'':'<small class="hint">ติ๊กยินยอมก่อนจึงแนบภาพได้</small>'}`}${D.ocr?`<div class="ocrst ${D.ocr.split(':')[0]}">${D.ocr==='busy'?'⏳ กำลังอ่านข้อมูลจากบัตร…':D.ocr==='ok'?'✓ กรอกข้อมูลจากบัตรให้แล้ว กรุณาตรวจสอบความถูกต้องอีกครั้ง':D.ocr==='chk'?'อ่านบัตรได้ แต่เลขบัตรตรวจหลักสุดท้ายไม่ผ่าน กรุณาแก้เลขให้ถูก':'อ่านข้อมูลจากบัตรไม่ได้ ('+esc(D.ocr.slice(4))+') · กรอกเอง'}</div>`:''}</div>
   <div class="fld full"><label for="dno">เลข${DOCT[D.t]} *</label><input id="dno" ${D.t==='id'?'inputmode="numeric" maxlength="17" placeholder="X-XXXX-XXXXX-XX-X"':'maxlength="12" placeholder="เช่น AA1234567" style="text-transform:uppercase"'} value="${esc(D.t==='id'?nidFmt(D.no):D.no)}"><small class="hint" id="dnoh">${D.t==='id'?'ระบบตรวจหลักสุดท้ายให้อัตโนมัติ':'ตัวอักษรและตัวเลขตามหน้าหนังสือเดินทาง'}</small></div>`}
function docBind(D,redraw,onOcr){
  const q=s=>$('msheet').querySelector(s);
  $('msheet').querySelectorAll('[data-dt]').forEach(b=>b.onclick=()=>{if(D.t!==b.dataset.dt){D.t=b.dataset.dt;D.no=''}redraw()});
  q('#dno').oninput=e=>{{const er=$('msheet').querySelector('.err');if(er)er.remove()}if(D.t==='id'){const d=e.target.value.replace(/\D/g,'').slice(0,13);D.no=d;e.target.value=d.length===13?nidFmt(d):d;
      const h=q('#dnoh');if(h){const er=d.length===13?docErr('id',d):'';h.textContent=er||(d.length===13?'✓ เลขถูกต้อง':'ระบบตรวจหลักสุดท้ายให้อัตโนมัติ');h.style.color=er?'#B3263E':(d.length===13?'#2E7D5B':'')}}
    else{D.no=e.target.value.toUpperCase().replace(/[^0-9A-Z]/g,'').slice(0,12)}};
  q('#dcon').onchange=e=>{D.consent=e.target.checked;if(!D.consent)D.img='';redraw()};
  if(q('#dfile'))q('#dfile').onchange=e=>{const f=e.target.files[0];if(!f)return;ppImg(f).then(u=>{D.img=u;D.ocr='busy';redraw();
    return fetch(top.location.origin+'/api/app?part=idocr',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({img:u})}).then(r=>r.json()).then(j=>{
      if(j.error){D.ocr='err:'+j.error}else{D.t=j.doc_type==='passport'?'passport':'id';if(j.doc_no)D.no=j.doc_no;D.ocr=j.id_ok?'ok':'chk';if(onOcr)onOcr(j)}
      redraw()}).catch(()=>{D.ocr='err:เชื่อมต่อไม่ได้';redraw()})}).catch(()=>toast('อ่านไฟล์ภาพไม่ได้'))};
  if(q('#dimgx'))q('#dimgx').onclick=()=>{D.img='';redraw()};
}
function docSave(c,D){
  const no=D.t==='id'?D.no.replace(/\D/g,''):D.no,body={gid:c.id,doc_type:D.t,doc_no:no,consent:!!D.consent};
  if(D.img)body.img=D.img; else if(D.had&&!D.consent)body.img='';
  const view=D.owner||!c.doc, img=D.img?true:(body.img===''?false:!!D.had);
  return ppCust('idcard',body).then(()=>{c.doc={t:D.t,no:view?no:'',mask:docMask(D.t,no),img,ca:D.img?new Date().toISOString().slice(0,10):((c.doc&&c.doc.ca)||''),cb:''};c.nid=(D.t==='id'&&view)?no:''})}
function docModal(c){
  const owner=!!(c.doc&&c.doc.no)||!c.doc;
  const D={t:c.doc?c.doc.t:'id',no:c.doc&&c.doc.no?c.doc.no:'',consent:!!(c.doc&&c.doc.img),img:'',img0:'',had:!!(c.doc&&c.doc.img),owner:!!(c.doc&&c.doc.no)};
  let err='';
  const draw=()=>openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">เอกสารยืนยันตัวตน</div><div class="bkn">${esc(c.name)}${c.doc&&!c.doc.no?' · กรอกเลขใหม่ทั้งหมด (พนักงานไม่เห็นเลขเดิม)':''}</div></div>
    <div class="sb regbody">${docFields(D)}${D.had&&!D.img?`<div class="full hint">มีภาพบัตรเดิมเก็บไว้ ${owner?'· ติ๊กยินยอมออกเพื่อลบภาพเดิม':''}</div>`:''}${err?`<div class="err full" role="alert">${esc(err)}</div>`:''}</div>
    <div class="sf"><button class="btn ghost" data-close>ยกเลิก</button><span style="flex:1"></span><button class="btn" id="dok">บันทึก</button></div>`,()=>{
      $('msheet').classList.add('wide');docBind(D,draw);
      $('dok').onclick=()=>{err=docErr(D.t,D.no);if(err)return draw();if(!D.consent&&D.had){D.img=''}
        $('dok').disabled=true;docSave(c,D).then(()=>{closeModal();render();toast('บันทึกเอกสารแล้ว')}).catch(e=>{err='บันทึกไม่สำเร็จ: '+e.message;draw()})}});
  draw();
}
/* บันทึกลงฐานข้อมูลจริง */
function ppCust(k,d){
  return fetch(top.location.origin+'/api/app?part=cust',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({k},d||{}))})
   .then(r=>r.json().catch(()=>({})).then(j=>{if(!r.ok)throw new Error(j.error||('รหัส '+r.status));try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}return j}));
}
function ppCustFail(e){toast('⚠️ บันทึกไม่สำเร็จ: '+e.message)}
/* ============ เพิ่ม / แก้ไขข้อมูลบริษัท (4 ขั้น · บันทึกจริง) ============ */
const COTYPE=['เอกชน','หน่วยงานราชการ','รัฐวิสาหกิจ'],COPAY={self:'ผู้เข้าพักจ่ายเอง',prepay:'บริษัทโอนค่าห้องล่วงหน้า',credit:'วางบิลเครดิต'};
const coPayTxt=k=>k.pay==='credit'?`วางบิลเครดิต ${k.credit||0} วัน`:(COPAY[k.pay]||k.paytxt||'-');
function compModal(k0){
  const isNew=!k0,k=k0||{};
  const K={name:k.name||'',short:k.short||'',type:k.type||'',site:k.site||'',tax:String(k.tax||'').replace(/\D/g,''),branch:k.hq||'สำนักงานใหญ่',addr:k.addr||'',
    pay:k.pay||'',credit:String(k.credit||''),cname:k.cname||'',crole:k.crole||'',cphone:k.phone||'',cemail:k.email||'',cline:k.cline||'',cdecide:!!k.cdecide};
  const STEPS=['ข้อมูลบริษัท','ใบกำกับภาษี (ถ้ามี)','ผู้ติดต่อ','ตรวจสอบและยืนยัน'],LAST=STEPS.length;
  let step=1,err='',busy=false;
  const inp=(id,lab,key,o={})=>`<div class="fld${o.full?' full':''}"><label for="${id}">${lab}</label><input id="${id}" data-kk="${key}" ${o.im?`inputmode="${o.im}"`:''} ${o.ml?`maxlength="${o.ml}"`:''} placeholder="${o.ph||''}" value="${esc(K[key]||'')}"></div>`;
  const chips=(key,list,lab,lb)=>`<div class="fld full"><span class="lb">${lab}</span><div class="regchips">${list.map(x=>`<button type="button" data-ckk="${key}" data-cv="${x}" aria-pressed="${K[key]===x}">${lb?lb(x):x}</button>`).join('')}</div></div>`;
  function body(){
    if(step===1) return inp('k1','ชื่อบริษัท / หน่วยงาน *','name',{ph:'เช่น บริษัท ตัวอย่าง จำกัด',full:true})+inp('k2','ชื่อย่อ (แสดงบนการ์ดหน้าแรก)','short',{ph:'เช่น ตัวอย่าง'})
      +'<div></div>'+chips('type',COTYPE,'ประเภทธุรกิจ *')+inp('k3','สถานที่ทำงานใกล้โรงแรม (ถ้ามี)','site',{ph:'เช่น โรงงาน/หน้างาน ต.โคกสูง อ.อุบลรัตน์',full:true})
      +'<small class="hint full" style="margin-top:-.5rem">ที่ที่พนักงานของบริษัทมาทำงานระหว่างพักกับเรา ซึ่งอาจไม่ใช่ที่อยู่ออกใบกำกับภาษี</small>';
    if(step===2) return inp('k4','เลขประจำตัวผู้เสียภาษี (13 หลัก)','tax',{im:'numeric',ml:13,ph:'0105XXXXXXXXX'})+inp('k5','สำนักงานใหญ่ / สาขา','branch',{ph:'สำนักงานใหญ่ หรือ สาขาที่ 00001'})
      +inp('k6','ที่อยู่สำหรับออกใบกำกับภาษี','addr',{ph:'เลขที่ ถนน ตำบล อำเภอ จังหวัด รหัสไปรษณีย์',full:true})
      +'<small class="hint full">ไม่บังคับ · กรอกเมื่อบริษัทต้องการใบกำกับภาษี</small>';
    if(step===3) return inp('k8','ชื่อผู้ติดต่อ *','cname',{ph:'เช่น คุณสมศักดิ์ ใจดี'})+inp('k9','ตำแหน่ง / บทบาท','crole',{ph:'เช่น ฝ่ายจัดซื้อ, ผู้จองห้องให้ทีม'})
      +inp('k10','เบอร์โทร *','cphone',{im:'tel',ph:'08X-XXX-XXXX'})+inp('k11','อีเมล (ส่งใบแจ้งหนี้)','cemail',{ph:'account@company.co.th'})+inp('k12','LINE','cline',{ph:'ชื่อ LINE หรือ ID'})
      +`<div class="fld"><span class="lb">&nbsp;</span><label class="ck" style="display:flex;gap:.5rem;align-items:center;min-height:3rem"><input type="checkbox" id="k13" ${K.cdecide?'checked':''} style="width:1.3rem;height:1.3rem;min-height:0;accent-color:var(--pink)"> เป็นผู้ตัดสินใจเลือกที่พัก</label></div>`;
    const kv=(a,b)=>`<div class="kvr"><span>${a}</span><div><b>${esc(b||'-')}</b></div></div>`;
    return `<div class="full regsum">${kv('ชื่อบริษัท',K.name)}${kv('ชื่อย่อ',K.short)}${kv('ประเภทธุรกิจ',K.type)}${kv('สถานที่ทำงานใกล้โรงแรม',K.site)}${kv('เลขผู้เสียภาษี',K.tax)}${kv('สำนักงานใหญ่ / สาขา',K.branch)}${kv('ที่อยู่ออกใบกำกับภาษี',K.addr)}
      ${kv('ผู้ติดต่อ',K.cname+(K.crole?' · '+K.crole:'')+(K.cdecide?' (ผู้ตัดสินใจ)':''))}${kv('เบอร์โทร',K.cphone)}${kv('อีเมล',K.cemail)}${kv('LINE',K.cline)}</div>`;
  }
  function vErr(){
    if(step===1){if(!K.name.trim())return 'กรุณากรอกชื่อบริษัท';if(!K.type)return 'กรุณาเลือกประเภทธุรกิจ';
      const n=strip(K.name).toLowerCase(),d=CO.find(x=>x.id!==k.id&&strip(x.name).toLowerCase()===n);if(d)return `${d.name} มีในระบบแล้ว`}
    if(step===2&&K.tax){if(K.tax.length!==13)return 'เลขผู้เสียภาษีต้องมี 13 หลัก';if(!thaiIdOk(K.tax))return 'เลขผู้เสียภาษีไม่ถูกต้อง กรุณาตรวจอีกครั้ง';
      const d=CO.find(x=>x.id!==k.id&&String(x.tax||'').replace(/\D/g,'')===K.tax);if(d)return `เลขผู้เสียภาษีนี้คือ ${d.name} ซึ่งมีในระบบแล้ว`}
    if(step===3){if(!K.cname.trim())return 'กรุณากรอกชื่อผู้ติดต่อ';if(digits(K.cphone).length<9)return 'กรุณากรอกเบอร์โทรให้ครบ';
      if(K.cemail&&!/^\S+@\S+\.\S+$/.test(K.cemail))return 'อีเมลไม่ถูกต้อง'}
    return ''}
  function draw(){
    const st=STEPS.map((t,i)=>`<li class="${i+1<step?'done':i+1===step?'on':''}"><i>${i+1<step?'✓':i+1}</i><span>${t}</span></li>`).join('');
    openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">${isNew?'เพิ่มบริษัท':'แก้ไขข้อมูลบริษัท'}</div><div class="bkn">${isNew?'ลงทะเบียนบริษัท/หน่วยงานที่ส่งพนักงานมาพัก':esc(k.name)}</div><ol class="regsteps">${st}</ol></div>
     <div class="sb regbody">${body()}${err?`<div class="err full" role="alert">${esc(err)}</div>`:''}</div>
     <div class="sf">${step>1?`<button class="btn ghost" id="kBack">ย้อนกลับ</button>`:`<button class="btn ghost" data-close>ยกเลิก</button>`}<span style="flex:1"></span>
      <button class="btn" id="kNext">${step<LAST?'ถัดไป':busy?'กำลังบันทึก…':isNew?'ยืนยันเพิ่มบริษัท':'บันทึกการแก้ไข'}</button></div>`,()=>{
      $('msheet').classList.add('wide');
      $('msheet').querySelectorAll('[data-kk]').forEach(e=>e.oninput=()=>{const f=e.dataset.kk;K[f]=f==='tax'?(e.value=e.value.replace(/\D/g,'').slice(0,13)):f==='credit'?(e.value=e.value.replace(/\D/g,'').slice(0,3)):e.value});
      $('msheet').querySelectorAll('[data-ckk]').forEach(b=>b.onclick=()=>{K[b.dataset.ckk]=b.dataset.cv;draw()});
      if($('k13'))$('k13').onchange=e=>{K.cdecide=e.target.checked};
      if($('kBack'))$('kBack').onclick=()=>{err='';step--;draw()};
      $('kNext').onclick=()=>{if(busy)return;err=vErr();if(err)return draw();if(step<LAST){step++;return draw()}save()};
      const f=$('msheet').querySelector('.regbody input:not([type=checkbox])');if(f&&step<LAST)setTimeout(()=>f.focus(),30);
    });
  }
  function save(){
    busy=true;draw();
    const cid=isNew?'K'+Date.now().toString(36).toUpperCase():k.id;
    const d={name:K.name.trim(),short:K.short.trim(),type:K.type,site:K.site.trim(),tax:K.tax,branch:K.branch.trim()||'สำนักงานใหญ่',addr:K.addr.trim(),
      cname:K.cname.trim(),crole:K.crole.trim(),cphone:K.cphone.trim(),cemail:K.cemail.trim(),cline:K.cline.trim(),cdecide:K.cdecide?'1':'0'};
    ppCust('comp',{gid:cid,data:d}).then(()=>{
      const o=isNew?{id:cid,contact:null,promos:[]}:k;
      Object.assign(o,{name:d.name,short:d.short,type:d.type,site:d.site,tax:d.tax,hq:d.branch,addr:d.addr,cname:d.cname,crole:d.crole,phone:d.cphone,email:d.cemail,cline:d.cline,cdecide:K.cdecide});
      if(isNew)CO.push(o);
      closeModal();S.detail={kind:'k',id:cid,tab:'info'};render();window.scrollTo({top:0,behavior:'smooth'});
      toast(isNew?`เพิ่ม ${d.name} แล้ว`:'บันทึกข้อมูลบริษัทแล้ว');
    }).catch(e=>{busy=false;err='บันทึกไม่สำเร็จ: '+e.message;draw()});
  }
  draw();
}
/* ผูกบริษัท: เลือกจากรายชื่อบริษัทในระบบ (ลูกค้า 1 คน ผูกได้ 1 บริษัท) */
function coPick(c){
  let q='',sel=c.company||'';
  const list=()=>CO.filter(x=>!q||strip(x.name).toLowerCase().includes(q)).map(x=>`<button class="copick${x.id===sel?' on':''}" data-pk="${x.id}" aria-pressed="${x.id===sel}"><b>${esc(x.name)}</b><small>${esc(x.hq||'')} · ผูกแล้ว ${CU.filter(u=>u.company===x.id).length} คน</small></button>`).join('')||'<div class="empty">ไม่พบบริษัท</div>';
  const save=(id,msg)=>{const old=c.company;if(id===old){closeModal();return}c.company=id;closeModal();render();
    ppCust('company',{gid:c.id,company:id}).then(()=>toast(msg)).catch(e=>{c.company=old;render();ppCustFail(e)})};
  function draw(){
    openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">ตั้งค่าบริษัท</div><div class="bkn">${esc(c.name)} · ผูกได้ 1 บริษัท</div></div>
     <div class="sb"><input id="coq" type="search" placeholder="ค้นหาชื่อบริษัท" style="width:100%;margin-bottom:.6rem" value="${esc(q)}"><div id="colist" class="colist">${list()}</div></div>
     <div class="sf">${c.company?'<button class="btn ghost danger" id="coUn" style="margin-right:auto">ลบการผูก</button>':''}<button class="btn ghost" data-close>ยกเลิก</button><button class="btn" id="coOk">ยืนยัน</button></div>`,()=>{
      $('msheet').classList.remove('wide');
      $('coq').oninput=e=>{q=strip(e.target.value).toLowerCase();$('colist').innerHTML=list()};
      $('colist').onclick=e=>{const b=e.target.closest('[data-pk]');if(!b)return;sel=b.dataset.pk;$('colist').innerHTML=list()};
      $('coOk').onclick=()=>{if(!sel){closeModal();return}save(sel,`ผูก ${c.name} กับ ${coOf(sel).name} แล้ว`)};
      if($('coUn'))$('coUn').onclick=()=>{const nm=(coOf(c.company)||{}).name||'';save('',`ลบการผูกกับ ${nm} แล้ว`)};
    });
  }
  draw();
}
"""

CUST_SAVE = [
    # บันทึกแก้ไขข้อมูล (+ เพศ) ลงฐานข้อมูล · บริษัทแก้ผ่านปุ่มผูกบริษัท
    ("Object.assign(c,{name:n,phone:p,line:$('eLine').value.trim(),addr:$('eAddr').value.trim(),nid:($('eNid').value||'').replace(/\\D/g,''),bday:$('eBd').value||'',prov:$('eProv').value.trim(),company:$('eCo').value,special:$('eSpec').value.trim()});\n    S.edit=false;S.err='';render();toast('บันทึกข้อมูลลูกค้าแล้ว');return}",
     "const old=Object.assign({},c),d={name:n,phone:p,line:$('eLine').value.trim(),addr:$('eAddr').value.trim(),bday:$('eBd').value||'',prov:$('eProv').value.trim(),special:$('eSpec').value.trim(),gender:$('eGen').value};\n"
     "    Object.assign(c,d);\n"
     "    S.edit=false;S.err='';render();ppCust('edit',{gid:c.id,data:d}).then(()=>toast('บันทึกข้อมูลลูกค้าแล้ว')).catch(e=>{Object.assign(c,old);render();ppCustFail(e)});return}\n"
     "  if(a=t.closest('[data-copick]')){coPick(cuOf(S.detail.id));return}\n"
     "  if(a=t.closest('[data-docedit]')){docModal(cuOf(S.detail.id));return}\n"
     "  if(a=t.closest('[data-docshow]')){S.docShow=!S.docShow;render();return}\n"
     "  if(a=t.closest('[data-docimg]')){docImg(cuOf(S.detail.id));return}\n"
     "  if(a=t.closest('[data-bkno]')){try{parent.postMessage({pbr:'bkdetail',no:a.dataset.bkno},'*')}catch(_){}return}"),
    # เลขการจองในประวัติ กดดูรายละเอียด (ป๊อปอัปเดียวกับหน้าแรก/การจอง)
    ("else h+=`<div class=\"lrow\"><div><span class=\"num\">${s.no}</span>",
     "else h+=`<div class=\"lrow\"><div><button class=\"bkno num\" data-bkno=\"${s.no}\">${s.no}</button>"),
    ("if(withName){const c=cuOf(s.cust);h+=`<div class=\"lrow\"><div class=\"num\">${s.no}</div>",
     "if(withName){const c=cuOf(s.cust);h+=`<div class=\"lrow\"><div><button class=\"bkno num\" data-bkno=\"${s.no}\">${s.no}</button></div>"),
]

PROF_CSS = """
.dhead .lvl2 small{font-size:.95rem!important}
.dhead .lvl2 .badge{font-size:1.35rem!important;padding:.35rem 1.3rem!important;margin-top:.3rem!important;font-weight:800}
.stats4{grid-template-columns:repeat(4,1fr)!important;margin-top:.9rem!important}
@media (max-width:700px){.stats4{grid-template-columns:1fr 1fr!important}}
.pbar{display:flex;align-items:flex-end;justify-content:space-between;gap:.6rem;margin-top:.2rem}
.pbar .dtabs2{margin:0 0 0 auto!important}
.dtabs2 button{border-bottom-left-radius:0!important;border-bottom-right-radius:0!important;border-bottom:0!important;min-height:2.6rem!important}
.pbar>.btn{margin-bottom:.45rem}
.dbox2{border-top-right-radius:0!important}
.bkno{border:0;background:none;padding:0;color:var(--purple);font-weight:700;text-decoration:underline;cursor:pointer;font:inherit;font-weight:700}
.colist{display:flex;flex-direction:column;gap:.45rem;max-height:52vh;overflow:auto}
.copick{display:flex;flex-direction:column;align-items:flex-start;text-align:left;border:1.5px solid var(--line);background:#fff;border-radius:14px;padding:.6rem .9rem;cursor:pointer;font:inherit}
.copick small{color:var(--soft)}
.copick.on{border-color:var(--purple);background:#F6F0FB}
#coq{border:1.5px solid var(--line);border-radius:12px;padding:.55rem .85rem;font:inherit;background:#fff;box-sizing:border-box}
#coUn{color:#B3263E!important;border-color:#E9B8C0!important}
.sheet.wide{width:min(52rem,100%)!important}
.regsteps{list-style:none;display:flex;gap:.4rem;margin:.8rem 0 0;padding:0;flex-wrap:wrap}
.regsteps li{display:flex;align-items:center;gap:.35rem;font-size:.85rem;opacity:.75;background:rgba(255,255,255,.14);border-radius:99px;padding:.2rem .7rem .2rem .25rem}
.regsteps li i{font-style:normal;width:1.5rem;height:1.5rem;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.25);font-weight:700;font-size:.8rem}
.regsteps li.on{opacity:1;background:#fff;color:var(--pink);font-weight:700}
.regsteps li.on i{background:var(--pink);color:#fff}
.regsteps li.done{opacity:1}
.regbody{grid-template-columns:1fr 1fr!important;gap:.9rem 1rem!important;padding:1.1rem 1.4rem .8rem!important;align-content:start;min-height:16rem}
.regbody .full{grid-column:1/-1}
.regchips{display:flex;flex-wrap:wrap;gap:.45rem}
.regchips button{border:2px solid var(--line);background:#fff;border-radius:99px;padding:.45rem 1.1rem;font:inherit;font-weight:600;min-height:2.8rem;cursor:pointer}
.regchips button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:#fff}
.regsum .kvr{padding:.35rem 0}
.lookbar{background:#F3EEF9;border:1.5px solid #DDCDEE;border-radius:16px;padding:.75rem .9rem;display:grid;gap:.45rem}
.lookbar label{font-weight:700}
.lookbar.ok{display:flex;justify-content:space-between;align-items:center;gap:.6rem;background:#EAF6EF;border-color:#BFE3CC}
.lkrow{display:flex;gap:.5rem}.lkrow input{flex:1;min-width:0;border:2px solid var(--line);background:#fff;border-radius:12px;padding:.5rem .8rem;min-height:2.8rem;font:inherit}
.lkres{display:grid;gap:.35rem}
.lkit{display:flex;flex-direction:column;align-items:flex-start;text-align:left;border:1.5px solid var(--line);background:#fff;border-radius:12px;padding:.5rem .8rem;font:inherit;cursor:pointer}
.lkit small{color:var(--soft)}.lkit:disabled{opacity:.55;cursor:default}
.ocrst{margin-top:.45rem;font-size:.88rem;font-weight:600;border-radius:10px;padding:.4rem .7rem}
.ocrst.busy{background:#FFF6DD;color:#8A6200}.ocrst.ok{background:#EAF6EF;color:#2E7D5B}.ocrst.chk,.ocrst.err{background:#FDECEE;color:#B3263E}
.regsec{font-family:var(--serif);font-weight:700;color:var(--pink);font-size:1.05rem;border-top:1.5px dashed var(--line);padding-top:.8rem;margin-top:.2rem}
.compbox{background:#F8F4FC;border:1.5px solid #E2D4EF;border-radius:16px;padding:.9rem 1rem}
.compbox .regbody{display:grid}
.compbox .regsec{border-top:0;padding-top:0;margin-bottom:.5rem}
.consent{background:#FFF8E8;border:1.5px solid #F1DDAE;border-radius:14px;padding:.7rem .9rem}
.consent .ck{display:flex;gap:.6rem;align-items:flex-start;font-weight:500;cursor:pointer;line-height:1.5}
.consent .ck input{width:1.4rem;height:1.4rem;min-height:0;flex:none;margin-top:.15rem;accent-color:var(--pink)}
.docpick{display:inline-flex;align-items:center;gap:.4rem;cursor:pointer;width:max-content}
.docpick.off{opacity:.45;pointer-events:none}
.docprev{display:flex;align-items:flex-end;gap:.8rem}
.docprev img{max-height:9rem;max-width:60%;border-radius:12px;border:1.5px solid var(--line)}
@media (max-width:640px){.regbody{grid-template-columns:1fr!important}}
"""


REG_MODAL = r"""
/* ============ สมัครสมาชิก (แบบเป็นขั้นตอน · บันทึกจริง) ============ */
function regModal(preId,q0,ph){
  const qn=String(q0||'').trim().toLowerCase(),pd=digits(ph||'');
  let pre=(preId&&cuOf(preId))||CU.find(c=>!c.memberNo&&((qn&&strip(c.name).toLowerCase().includes(qn))||(pd.length>=9&&digits(c.phone)===pd)))||null;
  const P=pre||{};
  const R={name:P.name||(q0||''),gender:P.gender||'',bday:P.bday||'',phone:P.phone||(ph||''),line:P.line||'',addr:P.addr||'',prov:P.prov||'',
    company:P.company||'',purpose:P.purpose||'',special:P.special||''};
  const D={t:(P.doc&&P.doc.t)||'id',no:(P.doc&&P.doc.no)||'',consent:false,img:'',had:!!(P.doc&&P.doc.img),owner:!!(P.doc&&P.doc.no)};
  const GEN=['ชาย','หญิง','เพศหลากหลาย','ไม่ระบุ'],PUR=['ทำงาน','แวะพัก','งานบุญ','ราชการ/อบรม'];
  const STEPS=['ข้อมูลส่วนตัวและบัตร','ติดต่อ ที่อยู่ และบริษัท','การเข้าพัก','ตรวจสอบและยืนยัน'],LAST=STEPS.length;
  let step=1,err='',busy=false;
  const nextNo=()=>pbm('M'+String(memSeq+1).padStart(3,'0'));
  const inp=(id,lab,k,o={})=>`<div class="fld${o.full?' full':''}"><label for="${id}">${lab}</label><input id="${id}" data-k="${k}" ${o.type?`type="${o.type}"`:''} ${o.im?`inputmode="${o.im}"`:''} placeholder="${o.ph||''}" value="${esc(R[k]||'')}"></div>`;
  const chips=(k,list,lab)=>`<div class="fld full"><span class="lb">${lab}</span><div class="regchips" role="group" aria-label="${lab}">${list.map(x=>`<button type="button" data-ck="${k}" data-cv="${x}" aria-pressed="${R[k]===x}">${x}</button>`).join('')}</div></div>`;
  const dupOf=()=>{const d=digits(R.phone);return d.length>=9?CU.find(x=>digits(x.phone)===d&&(!pre||x.id!==pre.id)):null};
  let lq='',lr=null;
  function fill(c){pre=c;R.name=c.name||'';R.gender=c.gender||'';R.bday=c.bday||'';R.phone=c.phone||'';R.line=c.line||'';R.addr=c.addr||'';R.prov=c.prov||'';
    R.company=c.company||'';R.purpose=c.purpose||'';R.special=c.special||'';
    if(c.doc){D.t=c.doc.t;D.no=c.doc.no||'';D.had=!!c.doc.img;D.owner=!!c.doc.no}lr=null;lq='';err='';draw()}
  function lookH(){
    if(pre)return `<div class="full lookbar ok"><span>สมัครให้ลูกค้าเดิม: <b>${esc(pre.name)}</b> · ${esc(pre.phone||'')} · ดึงข้อมูลเดิมมากรอกแล้ว</span><button type="button" class="linkbtn" id="lkx">ไม่ใช่คนนี้</button></div>`;
    return `<div class="full lookbar"><label for="lkq">ลูกค้าเคยมาพักแล้ว? ค้นหาจากเบอร์โทร</label><div class="lkrow"><input id="lkq" type="tel" inputmode="tel" placeholder="พิมพ์เบอร์โทรอย่างน้อย 4 ตัว" value="${esc(lq)}"><button type="button" class="btn ghost sm" id="lkb">ค้นหา</button></div>
      ${lr?(lr.length?`<div class="lkres">${lr.map(c=>`<button type="button" class="lkit" data-lk="${c.id}" ${c.memberNo?'disabled':''}><b>${esc(c.name)}</b><small>${esc(c.phone)}${c.memberNo?' · เป็นสมาชิกแล้ว '+pbm(c.memberNo):' · ยังไม่เป็นสมาชิก — แตะเพื่อดึงข้อมูล'}</small></button>`).join('')}</div>`:'<small class="hint">ไม่พบเบอร์นี้ในระบบ · กรอกเป็นลูกค้าใหม่ได้เลย</small>'):''}</div>`}
  function body(){
    if(step===1) return lookH()+inp('rg1','ชื่อ-สกุล *','name',{ph:'เช่น คุณสมชาย ใจดี',full:true})+chips('gender',GEN,'เพศ')+inp('rg3','วันเกิด (ถ้ามี)','bday',{type:'date'})
      +'<div class="full regsec">เอกสารยืนยันตัวตน</div>'+docFields(D)+(pre&&pre.doc&&!pre.doc.no?`<div class="full hint">ลูกค้ามีเอกสารในระบบแล้ว (${esc(pre.doc.mask)}) · กรอกเลขอีกครั้งเพื่อยืนยัน</div>`:'');
    if(step===2) return inp('rg4','เบอร์โทร *','phone',{type:'tel',im:'tel',ph:'08X-XXX-XXXX'})+inp('rg5','Line ID *','line',{ph:'ชื่อ LINE หรือ ID'})
      +inp('rg6','ที่อยู่','addr',{ph:'บ้านเลขที่ หมู่ ตำบล อำเภอ',full:true})+inp('rg7','จังหวัด','prov',{ph:'เช่น ขอนแก่น'})+`<div class="fld full"><label for="rg8">บริษัท (ถ้ามี)</label><select id="rg8"><option value="">— ไม่มี —</option>${CO.map(x=>`<option value="${x.id}" ${x.id===R.company?'selected':''}>${esc(x.name)}</option>`).join('')}</select><small class="hint">บริษัทใหม่ เพิ่มได้ที่แท็บ "บริษัท" → ปุ่ม "เพิ่ม"</small></div>`;
    if(step===3) return chips('purpose',PUR,'วัตถุประสงค์การเข้าพัก (ถ้ามี)')+inp('rg9','ความต้องการพิเศษ','special',{ph:'เช่น ไม่ทานเนื้อหมู ขอห้องชั้นล่าง',full:true});
    const kv=(k,v)=>`<div class="kvr"><span>${k}</span><div><b>${esc(v||'-')}</b></div></div>`;
    return `<div class="full regsum">${pre?`<div class="sum" style="margin-bottom:.6rem">สมัครให้ลูกค้าเดิมในระบบ: <b>${esc(pre.name)}</b> (ข้อมูลจะอัปเดตตามนี้)</div>`:''}
      ${kv('ชื่อ-สกุล',R.name)}${kv('เพศ',R.gender)}${kv('วันเกิด',R.bday?bdFmt(R.bday):'')}${kv(DOCT[D.t],docMask(D.t,D.t==='id'?D.no.replace(/\D/g,''):D.no)+(D.img?' · แนบภาพแล้ว (ลูกค้ายินยอม)':''))}${kv('เบอร์โทร',R.phone)}${kv('Line ID',R.line)}${kv('ที่อยู่',R.addr)}${kv('จังหวัด',R.prov)}
      ${kv('บริษัท',R.company?(coOf(R.company)||{}).name:'')}${kv('วัตถุประสงค์',R.purpose)}${kv('ความต้องการพิเศษ',R.special)}
      <div class="sum" style="margin-top:.7rem">รหัสสมาชิกที่จะออกให้: <b>${nextNo()}</b> (ออกอัตโนมัติเมื่อยืนยัน)</div></div>`;
  }
  function draw(){
    const st=STEPS.map((t,i)=>`<li class="${i+1<step?'done':i+1===step?'on':''}"><i>${i+1<step?'✓':i+1}</i><span>${t}</span></li>`).join('');
    openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">สมัครสมาชิก</div><div class="bkn">สมาชิกใช้สิทธิ์แลกของและร่วมโปรโมชัน</div><ol class="regsteps">${st}</ol></div>
     <div class="sb regbody">${body()}${err?`<div class="err full" role="alert">${esc(err)}</div>`:''}</div>
     <div class="sf">${step>1?`<button class="btn ghost" id="rgBack">ย้อนกลับ</button>`:`<button class="btn ghost" data-close>ยกเลิก</button>`}<span style="flex:1"></span>
      <button class="btn" id="rgNext">${step<LAST?'ถัดไป':busy?'กำลังบันทึก…':'ยืนยันสมัครสมาชิก'}</button></div>`,()=>{
      $('msheet').classList.add('wide');
      if(step===1){docBind(D,draw,j=>{const nm=[j.first_name,j.last_name].filter(Boolean).join(' ');if(nm)R.name='คุณ'+nm.replace(/^คุณ/,'');
          if(j.gender)R.gender=j.gender;if(j.birth_date)R.bday=j.birth_date;if(j.address)R.addr=j.address;if(j.province)R.prov=j.province.replace(/^จ\.\s*|^จังหวัด/,'')});
        const lk=()=>{const d=digits($('lkq')?$('lkq').value:'');lq=$('lkq')?$('lkq').value:'';if(d.length<4){lr=null;err='พิมพ์เบอร์โทรอย่างน้อย 4 ตัว';return draw()}
          err='';lr=CU.filter(c=>digits(c.phone).includes(d)).slice(0,6);draw()};
        if($('lkb'))$('lkb').onclick=lk;if($('lkq'))$('lkq').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();lk()}};
        $('msheet').querySelectorAll('[data-lk]').forEach(b=>b.onclick=()=>fill(cuOf(b.dataset.lk)));
        if($('lkx'))$('lkx').onclick=()=>{pre=null;Object.keys(R).forEach(k=>R[k]='');D.no='';D.had=false;D.owner=false;draw()}}
      if(step===2){const sc=$('rg8');if(sc)sc.onchange=()=>{R.company=sc.value}}
      $('msheet').querySelectorAll('[data-k]').forEach(e=>e.oninput=e.onchange=()=>{R[e.dataset.k]=e.value});
      $('msheet').querySelectorAll('[data-ck]').forEach(b=>b.onclick=()=>{const k=b.dataset.ck;R[k]=R[k]===b.dataset.cv?'':b.dataset.cv;draw()});
      if($('rgBack'))$('rgBack').onclick=()=>{err='';step--;draw()};
      $('rgNext').onclick=next;
      const f=$('msheet').querySelector('.regbody input:not([type=checkbox]):not([type=file])');if(f&&step<LAST)setTimeout(()=>f.focus(),30);
    });
  }
  function next(){
    if(busy)return;err='';
    if(step===1&&!R.name.trim()){err='กรุณากรอกชื่อ-สกุล';return draw()}
    if(step===1){const e=docErr(D.t,D.no);if(e){err=e;return draw()}}
    if(step===2){
      if(digits(R.phone).length<9){err='กรุณากรอกเบอร์โทรให้ครบ';return draw()}
      if(!R.line.trim()){err='กรุณากรอก Line ID';return draw()}
      const d=dupOf();
      if(d&&d.memberNo){err=`เบอร์นี้เป็นสมาชิกอยู่แล้ว (${d.name} · ${pbm(d.memberNo)})`;return draw()}
      if(d&&!pre){pre=d;['line','addr','prov','company','purpose','special','gender','bday'].forEach(k=>{if(!R[k]&&d[k])R[k]=d[k]})}
    }
    if(step<LAST){step++;return draw()}
    save();
  }
  function save(){
    busy=true;draw();

    const isNew=!pre, c=pre||{id:'N'+Date.now().toString(36).toUpperCase(),name:'',phone:'',line:'',addr:'',prov:'',company:'',special:'',memberNo:'',memberSince:null,added:TODAY,bias:'',gender:''};
    const data={name:R.name.trim(),phone:R.phone.trim(),line:R.line.trim(),addr:R.addr.trim(),prov:R.prov.trim(),bday:R.bday||'',gender:R.gender,purpose:R.purpose,special:R.special.trim()};
    ppCust('member',{gid:c.id,is_new:isNew,base:memSeq,company:R.company||'',data}).then(j=>{
      if(!isNew&&(R.company||'')!==(c.company||''))ppCust('company',{gid:c.id,company:R.company||''}).catch(()=>{});
      Object.assign(c,data,{company:R.company||'',memberNo:j.memberNo,memberSince:TODAY});
      docSave(c,D).then(()=>render()).catch(e=>toast('⚠️ บันทึกเอกสารไม่สำเร็จ: '+e.message+' · แก้ไขได้ที่หน้าโปรไฟล์'));
      if(isNew)CU.push(c);
      memSeq=Math.max(memSeq,+String(j.memberNo).replace(/\D/g,''));
      closeModal(); S.detail={kind:'c',id:c.id,tab:'info'}; S.edit=false; S.view='list'; render(); window.scrollTo({top:0,behavior:'smooth'});
      toast(`สมัครสมาชิกให้ ${c.name} แล้ว (${pbm(c.memberNo)})`);
      try{parent.postMessage({pbr:'memreg',name:c.name,phone:c.phone,no:c.memberNo},'*')}catch(_){}
    }).catch(e=>{busy=false;err='บันทึกไม่สำเร็จ: '+e.message;draw()});
  }
  draw();
}
"""


def custprof(h):
    i = h.index('function custDetail(c){')
    j = h.index('function compDetail(k){')
    h = h[:i] + CUST_DETAIL + h[j:]
    h = _r(h, CUST_SAVE, 'cust-save')
    i = h.index('function regModal(')
    j = h.index('function ruleModal(')
    h = h[:i] + REG_MODAL.lstrip() + h[j:]
    h = _r(h, [
        # แท็บบริษัท: ปุ่ม "เพิ่ม" แทน "สมัครสมาชิก"
        ("<button class=\"btn\" id=\"regBtn\" style=\"margin-left:auto\">${ico('plus')}สมัครสมาชิก</button>",
         "<button class=\"btn\" id=\"regBtn\" style=\"margin-left:auto\">${ico('plus')}${isC?'สมัครสมาชิก':'เพิ่ม'}</button>"),
        ('<div class="k-contact">${ct?esc(ct.name):\'-\'}</div>', '<div class="k-contact">${esc(k.cname||(ct?ct.name:\'-\'))}</div>'),
        ("if(t.closest('#regBtn')){regModal();return}", "if(t.closest('#regBtn')){if(S.sub==='comp')compModal();else regModal();return}"),
        ("if(a=t.closest('[data-copick]'))", "if(a=t.closest('[data-coedit]')){compModal(coOf(S.detail.id));return}\n  if(a=t.closest('[data-copick]'))"),
        # หน้าข้อมูลบริษัท: ข้อมูลครบ + แก้ไขได้
        ("<div class=\"dbox\"><h4>ข้อมูลบริษัท</h4>${row('ชื่อบริษัท',`<b>${esc(k.name)}</b>`)+row('เลขผู้เสียภาษี',`<b>${k.tax}</b>`)+row('สำนักงานใหญ่ / สาขา',`<b>${esc(k.hq)}</b>`)\n    +row('ผู้ติดต่อ',ct?`<button class=\"linkbtn\" data-open=\"c:${ct.id}\">${esc(ct.name)}</button>`:'<b>-</b>')+row('เบอร์โทร',`<b>${esc(k.phone)}</b>`)+row('อีเมล',`<b>${esc(k.email)}</b>`)+row('ที่อยู่',`<b>${esc(k.addr)}</b>`)}",
         "<div class=\"dbox\"><h4>ข้อมูลบริษัท <button class=\"btn ghost sm\" data-coedit>${ico('pen')}แก้ไขข้อมูล</button></h4>${row('ชื่อบริษัท',`<b>${esc(k.name)}</b>`)+row('ชื่อย่อ',`<b>${esc(k.short||'-')}</b>`)+row('ประเภทธุรกิจ',`<b>${esc(k.type||'-')}</b>`)+row('สถานที่ทำงานใกล้โรงแรม',`<b>${esc(k.site||'-')}</b>`)"
         "+row('เลขผู้เสียภาษี',`<b>${esc(k.tax||'-')}</b>`)+row('สำนักงานใหญ่ / สาขา',`<b>${esc(k.hq||'-')}</b>`)+row('ที่อยู่ออกใบกำกับภาษี',`<b>${esc(k.addr||'-')}</b>`)"
         "+row('ผู้ติดต่อ',(ct?`<button class=\"linkbtn\" data-open=\"c:${ct.id}\">${esc(k.cname||ct.name)}</button>`:`<b>${esc(k.cname||'-')}</b>`)+(k.crole?` <span class=\"hint\">${esc(k.crole)}</span>`:'')+(k.cdecide?' <span class=\"badge m-yes\">ผู้ตัดสินใจ</span>':''))"
         "+row('เบอร์โทร',`<b>${esc(k.phone||'-')}</b>`)+row('อีเมล',`<b>${esc(k.email||'-')}</b>`)+row('LINE',`<b>${esc(k.cline||'-')}</b>`)}"),
        ("function closeModal(){$('mscrim').classList.remove('open');",
                "function closeModal(){$('mscrim').classList.remove('open');$('msheet').classList.remove('wide');"),
        # เปิดจากหน้ารายละเอียดการจอง: แสดงหน้าลูกค้าคนนั้นทับหน้าจอ · กดกลับ = กลับหน้าการจองเดิม
        ("  if(a=t.closest('[data-back]')){S.promoPick=false;S.detail=null;",
         "  if(a=t.closest('[data-back]')&&S.fromBk){const P=S.fromBk;S.fromBk=null;document.body.removeAttribute('data-keep');Object.assign(S,P);S.edit=false;render();try{parent.postMessage({pbr:'custpageclosed'},'*')}catch(_){}return}\n"
         "  if(a=t.closest('[data-back]')){S.promoPick=false;S.detail=null;"),
        ("window.addEventListener('message',e=>{const d=e.data||{};if(d.pbr==='view'&&d.view){",
         "window.addEventListener('message',e=>{const d=e.data||{};if(d.pbr==='custpage'&&d.gid){if(!cuOf(d.gid)){try{parent.postMessage({pbr:'custpageclosed',miss:1},'*')}catch(_){}return}"
         "if(!S.fromBk)S.fromBk={view:S.view,sub:S.sub,detail:S.detail};document.body.setAttribute('data-keep','');closeModal();S.view='list';S.sub='cust';S.detail={kind:'c',id:d.gid,tab:'info'};S.edit=false;render();window.scrollTo(0,0);return}"
         "if(d.pbr==='view'&&d.view){")], 'cust-close')
    return _css(h, PROF_CSS)


# ---------- แม่บ้าน: รายชื่อ/โซน/ห้อง/LINE + งานทำความสะอาดบันทึกจริง + มอบหมายอัตโนมัติ (ต้องรัน 12_hk.sql) ----------
HK_JS = r"""
/* ---- บันทึกลงฐานข้อมูล ---- */
function ppHk(k,d){return fetch(top.location.origin+'/api/app?part=hk',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({k},d||{}))})
  .then(r=>r.json().catch(()=>({})).then(j=>{if(!r.ok)throw new Error(j.error||('รหัส '+r.status));try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}return j}))}
function hkFail(e){toast('⚠️ บันทึกไม่สำเร็จ: '+e.message)}
const ZN2=['ตึกใหม่','บ้านหลัง'];
const coversRoom=(x,room)=>{const z=(RMZ.find(r=>r.c===room)||{}).z;return x.rooms&&x.rooms.length?x.rooms.includes(room):(x.zones||[]).includes(z)};
function pickWho(room){const c=HKS.filter(x=>x.on&&coversRoom(x,room));if(!c.length)return '';
  const load=n=>TASKS.filter(t=>t.who===n&&t.st<3).length;return c.sort((a,b)=>load(a.n)-load(b.n)||(a.sort||0)-(b.sort||0))[0].n}
const DAYN=['อา','จ','อ','พ','พฤ','ศ','ส'],DAYO=[1,2,3,4,5,6,0];
const schedOf=x=>!Array.isArray(x.days)||x.days.includes(HK_DOW),effOn=x=>x.ovr==null?schedOf(x):x.ovr;
const daysTxt=x=>!Array.isArray(x.days)||x.days.length===7?'ทำงานทุกวัน':!x.days.length?'ยังไม่เลือกวันทำงาน':'ทำงาน '+DAYO.filter(d=>x.days.includes(d)).map(d=>DAYN[d]).join(' ');
const GEAR='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
const staffBody=x=>({id:x.id,name:x.n,days:Array.isArray(x.days)?x.days:null,ovr:x.ovr==null?null:x.ovr,zones:x.zones||[],rooms:x.rooms&&x.rooms.length?x.rooms:null,line_key:x.line||'',sort:x.sort||0});
let _hkSeeded=null;
function saveStaff(x,extra){if(_hkSeeded===null)_hkSeeded=HAS_STAFF;const go=()=>ppHk('staff_save',Object.assign(staffBody(x),extra||{}));
  if(_hkSeeded)return go();_hkSeeded=true;   // ครั้งแรก: บันทึกรายชื่อเริ่มต้นทั้งหมด
  return HKS.reduce((p,y)=>p.then(()=>ppHk('staff_save',Object.assign(staffBody(y),y===x?(extra||{}):{}))),Promise.resolve())}
/* ---- งานทำความสะอาด: สร้าง/อัปเดตในฐานข้อมูล ---- */
function taskSync(t,upd){
  const doUpd=()=>upd?ppHk('task_upd',Object.assign({id:t.dbid},upd)):Promise.resolve();
  if(t.dbid)return doUpd();
  return ppHk('task_new',{room:t.room,kind:t.kind,who:t.who||'',note:t.note||''}).then(j=>{t.dbid=j.id;if(!t.who&&j.who)t.who=j.who;return doUpd()})}
function lineName(k){const c=LCH.find(x=>x.k===k);return c?c.n:''}
/* ---- ป๊อปอัปรายชื่อแม่บ้าน ---- */
function hkModal(){
  let open=null,addErr='';
  const roomsOf=x=>RMZ.filter(r=>(x.zones||[]).includes(r.z));
  const card=(x,i)=>{const n=TASKS.filter(t=>t.who===x.n&&t.st<5).length,isO=open===x.id,sel=x.rooms&&x.rooms.length?x.rooms:null;
    const scope=!(x.zones||[]).length?'<span class="hkw">ยังไม่กำหนดโซน · ไม่รับงานอัตโนมัติ</span>':sel?`${sel.length} ห้อง: ${sel.join(', ')}`:`ทุกห้องใน${x.zones.join(' และ ')}`;
    const tday=x.ovr==null?'':`<span class="hkov">วันนี้${x.ovr?'มาทำงาน (นอกวันทำงาน)':'หยุด'} · พรุ่งนี้กลับตามวันทำงาน</span>`;
    return `<div class="hkc${isO?' open':''}"><div class="hkh"><button type="button" class="hkname" data-hko="${x.id}" aria-expanded="${isO}"><b>${esc(x.n)}</b>${n?` <small>(มีงาน ${n} ห้อง)</small>`:''}<span class="hks">${daysTxt(x)} · ${scope}${x.line?` · LINE: ${esc(lineName(x.line)||'ผูกแล้ว')}`:''}</span>${tday}</button>
      <label class="sw" title="${x.on?'ทำงานวันนี้':'หยุดวันนี้'}"><input type="checkbox" data-hkon="${i}" ${x.on?'checked':''}><i></i><span class="swl">${x.on?'ทำงาน':'หยุด'}</span></label>
      <button type="button" class="hkchev" data-hko="${x.id}" aria-expanded="${isO}" aria-label="ตั้งค่า ${esc(x.n)}">${GEAR}<span>ตั้งค่า</span></button></div>
     ${isO?`<div class="hkb">
       <div class="hkf"><span class="lb">วันทำงาน <small class="hint">แตะเพื่อเลือก/เอาออก · วันที่ไม่ได้เลือก = วันหยุด ระบบไม่มอบหมายงาน</small></span><div class="regchips hkdays">${DAYO.map(d=>`<button type="button" data-hkd="${d}" aria-pressed="${!Array.isArray(x.days)||x.days.includes(d)}">${DAYN[d]}</button>`).join('')}</div></div>
       <div class="hkf"><span class="lb">โซนที่รับผิดชอบ</span><div class="regchips">${ZN2.map(z=>`<button type="button" data-hkz="${z}" aria-pressed="${(x.zones||[]).includes(z)}">${z}</button>`).join('')}</div></div>
       ${(x.zones||[]).length?`<div class="hkf"><span class="lb">ห้องที่รับผิดชอบ <small class="hint">${sel?'เลือกเฉพาะห้อง':'ตอนนี้: ทุกห้องในโซน · แตะเพื่อเลือกเฉพาะห้อง'}</small></span>
         <div class="hkrooms">${roomsOf(x).map(r=>`<button type="button" data-hkr="${r.c}" aria-pressed="${!sel||sel.includes(r.c)}" class="${sel?'':'all'}">${r.c}</button>`).join('')}</div>
         ${sel?'<button type="button" class="linkbtn" data-hkall>ใช้ทุกห้องในโซน</button>':''}</div>`:''}
       <div class="hkf"><label class="lb" for="hkl_${x.id}">LINE ของแม่บ้าน</label><select id="hkl_${x.id}" data-hkline><option value="">— ยังไม่ผูก —</option>${LCH.map(c=>`<option value="${c.k}" ${x.line===c.k?'selected':''}>${esc(c.n||c.k)}</option>`).join('')}</select>
         <small class="hint">ให้แม่บ้านเพิ่มเพื่อน LINE โรงแรมแล้วส่งข้อความมา 1 ครั้ง ชื่อจะขึ้นในรายการนี้</small></div>
       <div class="hkf hkrow2"><label class="lb" for="hkn_${x.id}">ชื่อ</label><input id="hkn_${x.id}" data-hkname value="${esc(x.n)}"><button type="button" class="btn ghost sm danger" data-hkdel="${x.id}">ลบรายชื่อ</button></div>
     </div>`:''}</div>`};
  const draw=()=>openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">รายชื่อแม่บ้าน</div><div class="bkn">สวิตช์ = ทำงาน/หยุดเฉพาะวันนี้ · กดตั้งค่าเพื่อเลือกวันทำงาน โซน ห้อง และ LINE · เช็คเอาท์แล้วระบบมอบหมายงานให้ตามโซนอัตโนมัติ</div></div>
   <div class="sb"><div id="hkl">${HKS.map(card).join('')}</div>
    <div class="hkadd"><input id="hkNew" type="text" placeholder="พิมพ์ชื่อแม่บ้านใหม่" aria-label="ชื่อแม่บ้านใหม่"><button type="button" class="btn" id="hkAdd">เพิ่มรายชื่อ</button></div>${addErr?`<div class="err" role="alert">${esc(addErr)}</div>`:''}
    <div class="hkgrp"><label class="lb" for="hkGrp">กลุ่ม LINE แม่บ้าน (ส่งสรุปงาน)</label><input id="hkGrp" value="${esc(HK_GROUP)}" placeholder="เชิญบัญชี LINE โรงแรมเข้ากลุ่ม แล้วระบบจะใส่รหัสกลุ่มให้"><small class="hint">ใช้ในขั้นต่อไป: ส่งการ์ดงานให้แม่บ้านแต่ละคน และสรุปงานเข้ากลุ่ม</small></div></div>
   <div class="sf"><button class="btn" data-close>เสร็จสิ้น</button></div>`,()=>{
    $('msheet').classList.add('wide');
    const ms=$('msheet'),cur=()=>HKS.find(y=>y.id===open);
    const commit=(x,msg,extra)=>{syncHK();render();draw();saveStaff(x,extra).then(()=>msg&&toast(msg)).catch(hkFail)};
    ms.querySelectorAll('[data-hko]').forEach(b=>b.onclick=()=>{open=open===b.dataset.hko?null:b.dataset.hko;draw()});
    ms.querySelectorAll('[data-hkon]').forEach(c=>c.onchange=()=>{const x=HKS[+c.dataset.hkon];x.ovr=c.checked===schedOf(x)?null:c.checked;x.on=effOn(x);commit(x,`${x.n}: ${x.on?'ทำงานวันนี้':'หยุดวันนี้'}${x.ovr==null?'':' · พรุ่งนี้กลับตามวันทำงาน'}`)});
    ms.querySelectorAll('[data-hkd]').forEach(b=>b.onclick=()=>{const x=cur(),d=+b.dataset.hkd;let s=Array.isArray(x.days)?[...x.days]:[0,1,2,3,4,5,6];
      s=s.includes(d)?s.filter(v=>v!==d):[...s,d];x.days=s.length===7?null:s.sort();if(x.ovr===schedOf(x))x.ovr=null;x.on=effOn(x);commit(x,daysTxt(x))});
    ms.querySelectorAll('[data-hkz]').forEach(b=>b.onclick=()=>{const x=cur(),z=b.dataset.hkz;x.zones=(x.zones||[]).includes(z)?x.zones.filter(v=>v!==z):[...(x.zones||[]),z];
      if(x.rooms)x.rooms=x.rooms.filter(r=>x.zones.includes((RMZ.find(q=>q.c===r)||{}).z));commit(x)});
    ms.querySelectorAll('[data-hkr]').forEach(b=>b.onclick=()=>{const x=cur(),r=b.dataset.hkr;let s=x.rooms&&x.rooms.length?[...x.rooms]:roomsOf(x).map(q=>q.c);
      s=s.includes(r)?s.filter(v=>v!==r):[...s,r];x.rooms=s.length===roomsOf(x).length?null:s;commit(x)});
    const all=ms.querySelector('[data-hkall]');if(all)all.onclick=()=>{const x=cur();x.rooms=null;commit(x)};
    const ln=ms.querySelector('[data-hkline]');if(ln)ln.onchange=()=>{const x=cur();x.line=ln.value;commit(x,ln.value?`ผูก LINE ของ ${x.n} แล้ว`:'ยกเลิกการผูก LINE แล้ว')};
    const nm=ms.querySelector('[data-hkname]');if(nm)nm.onchange=()=>{const x=cur(),v=nm.value.trim(),old=x.n;if(!v||v===old){nm.value=old;return}
      if(HKS.some(y=>y!==x&&y.n===v)){toast('มีชื่อนี้แล้ว');nm.value=old;return}
      x.n=v;TASKS.forEach(t=>{if(t.who===old)t.who=v});commit(x,`เปลี่ยนชื่อเป็น ${v} แล้ว`,{old_name:old})};
    const del=ms.querySelector('[data-hkdel]');if(del)del.onclick=()=>{const x=cur(),pend=TASKS.filter(t=>t.who===x.n&&t.st<5);
      const others=HKS.filter(y=>y!==x&&y.on);
      openModal(`<div class="sh"><div class="rn">ลบรายชื่อ ${esc(x.n)}?</div><div class="bkn">เช่น แม่บ้านลาออก · ประวัติงานเดิมยังอยู่</div></div>
       <div class="sb">${pend.length?`<div class="fld"><label for="hkTo">มีงานค้าง ${pend.length} ห้อง (${pend.map(t=>t.room).join(', ')}) · โอนให้</label><select id="hkTo"><option value="">— ยังไม่มอบหมาย —</option>${others.map(y=>`<option>${esc(y.n)}</option>`).join('')}</select></div>`:'<p>ไม่มีงานค้าง</p>'}</div>
       <div class="sf"><button class="btn ghost" id="hkDelNo">ยกเลิก</button><button class="btn danger" id="hkDelOk">ลบรายชื่อ</button></div>`,()=>{
        $('hkDelNo').onclick=draw;
        $('hkDelOk').onclick=()=>{const to=$('hkTo')?$('hkTo').value:'';const go=()=>ppHk('staff_del',{id:x.id,to});
          ((_hkSeeded===null?HAS_STAFF:_hkSeeded)?go():saveStaff(x).then(go)).then(()=>{HKS.splice(HKS.indexOf(x),1);pend.forEach(t=>t.who=to);open=null;syncHK();render();draw();toast(`ลบ ${x.n} แล้ว`)}).catch(hkFail)}})};
    const add=()=>{const v=$('hkNew').value.trim();if(!v){addErr='กรุณาพิมพ์ชื่อ';return draw()}if(HKS.some(x=>x.n===v)){addErr='มีชื่อนี้แล้ว';return draw()}
      const x={id:'H'+Date.now().toString(36).toUpperCase(),n:v,on:true,zones:[],rooms:null,line:'',sort:HKS.length+1,days:null,ovr:null};HKS.push(x);addErr='';open=x.id;commit(x,`เพิ่ม ${v} แล้ว · เลือกโซนที่รับผิดชอบได้เลย`)};
    $('hkAdd').onclick=add;$('hkNew').onkeydown=e=>{if(e.key==='Enter')add()};
    $('hkGrp').onchange=e=>{HK_GROUP=e.target.value.trim();ppHk('group_set',{value:HK_GROUP}).then(()=>toast('บันทึกกลุ่ม LINE แล้ว')).catch(hkFail)};
  });
  draw();
}
"""

HK_PATCH = [
    # รายชื่อในรายการมอบหมาย = แม่บ้านที่ทำงานวันนี้ + ชื่อที่ถูกมอบหมายอยู่แล้ว
    ("const HK=[];function syncHK(){HK.length=0;HKS.filter(x=>x.on).forEach(x=>HK.push(x.n))}syncHK();",
     "const HK=[];function syncHK(){HK.length=0;HKS.filter(x=>x.on).forEach(x=>HK.push(x.n))}syncHK();"),
    # เริ่มทำ/ทำเสร็จ/ย้อนสถานะ
    ("  t.st++; if(t.st===2)t.t2=Date.now(); if(t.st===3)t.t3=Date.now();",
     "  t.st++; if(t.st===2)t.t2=Date.now(); if(t.st===3)t.t3=Date.now(); taskSync(t,{st:t.st}).catch(e=>{t.st--;renderClean();hkFail(e)});"),
    ("function back(id){const t=TASKS.find(x=>x.id==id); t.st--; if(t.st<3)t.t3=null; if(t.st<2)t.t2=null;",
     "function back(id){const t=TASKS.find(x=>x.id==id); t.st--; if(t.st<3)t.t3=null; if(t.st<2)t.t2=null; taskSync(t,{st:t.st}).catch(hkFail);"),
    # เปลี่ยนผู้รับผิดชอบ / หมายเหตุ
    ("const t=TASKS.find(x=>x.id==w.dataset.who);t.who=w.value;renderClean();return}",
     "const t=TASKS.find(x=>x.id==w.dataset.who);t.who=w.value;t.auto=false;renderClean();taskSync(t,{who:t.who}).catch(hkFail);return}\n  const nn=e.target.closest('[data-note]');if(nn){const t=TASKS.find(x=>x.id==nn.dataset.note);taskSync(t,{note:t.note}).catch(hkFail)}"),
    # ดึงงานจากเช็คเอาท์วันนี้ → มอบหมายตามโซน
    ("  add.forEach(r=>TASKS.push({id:++tid,room:r,kind:'out',who:'',st:1,t2:null,t3:null,note:''}));\n  renderClean(); toast(add.length?`สร้างงานใหม่ ${add.length} งานจากเช็คเอาท์วันนี้ (${add.join(', ')}) · กรุณามอบหมายแม่บ้าน`:'ไม่มีห้องเช็คเอาท์ใหม่ที่ยังไม่มีงาน')}",
     "  add.forEach(r=>{const t={id:++tid,room:r,kind:'out',who:pickWho(r),st:1,t2:null,t3:null,note:'',auto:true};TASKS.push(t);taskSync(t).then(renderClean).catch(hkFail)});\n  renderClean(); toast(add.length?`สร้างงานใหม่ ${add.length} งานจากเช็คเอาท์วันนี้ (${add.join(', ')}) · มอบหมายตามโซนให้แล้ว`:'ไม่มีห้องเช็คเอาท์ใหม่ที่ยังไม่มีงาน')}"),
    # เพิ่มงานเอง
    ("      TASKS.push({id:++tid,room,kind,who:$('aWho').value,st:1,t2:null,t3:null,note:$('aNote').value.trim()});closeModal();renderClean();toast(`เพิ่มงานห้อง ${room} แล้ว`)}})",
     "      const t={id:++tid,room,kind,who:$('aWho').value||pickWho(room),st:1,t2:null,t3:null,note:$('aNote').value.trim()};TASKS.push(t);closeModal();renderClean();taskSync(t).then(()=>{renderClean();toast(`เพิ่มงานห้อง ${room} แล้ว${t.who?' · '+t.who:''}`)}).catch(hkFail)}})"),
    # เช็คเอาท์จากหน้าแรก → งานเด้งพร้อมแม่บ้านที่รับผิดชอบ
    ("    const t={id:++tid,room:d.room,kind:'out',who:'',st:1,t2:null,t3:null,note:'สร้างอัตโนมัติจากเช็คเอาท์'+(d.guest?' · '+d.guest:''),fresh:true};\n    TASKS.push(t);",
     "    const t={id:++tid,room:d.room,kind:'out',who:pickWho(d.room),st:1,t2:null,t3:null,note:'สร้างอัตโนมัติจากเช็คเอาท์'+(d.guest?' · '+d.guest:''),fresh:true,auto:true};\n    TASKS.push(t);taskSync(t).then(()=>{if(S.tab==='clean')renderClean()}).catch(hkFail);"),
    # ยกเลิกการเช็คเอาท์ → ลบงานหลังเช็คเอาท์ที่ยังไม่เริ่ม (แม้ระบบมอบหมายแม่บ้านไปแล้ว)
    ("    const i=TASKS.findIndex(t=>t.room===d.room&&t.kind==='out'&&t.st===1&&!t.who);\n    if(i>=0){TASKS.splice(i,1);if(S.tab==='clean')renderClean()}",
     "    const i=TASKS.findIndex(t=>t.room===d.room&&t.kind==='out'&&t.st===1);\n    if(i>=0){TASKS.splice(i,1);if(S.tab==='clean')renderClean()}\n    ppHk('task_cancel_out',{room:d.room}).catch(()=>{});"),
    # แสดงว่าใครถูกมอบหมายอัตโนมัติ
    ("<div class=\"c-who\"><select data-who=\"${t.id}\"", "<div class=\"c-who\">${t.auto&&t.who?'<small class=\"autot\">ระบบมอบหมายตามโซน</small>':''}<select data-who=\"${t.id}\""),
]

HK_CSS = """
.hkc{border:1.5px solid var(--line);border-radius:16px;background:#fff;margin-bottom:.6rem;overflow:hidden}
.hkc.open{border-color:#D7C4EA;box-shadow:0 6px 18px rgba(46,31,43,.08)}
.hkh{display:flex;align-items:center;gap:.6rem;padding:.6rem .8rem}
.hkname{flex:1;min-width:0;border:0;background:none;text-align:left;font:inherit;cursor:pointer;display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .5rem}
.hkname b{font-size:1.05rem}.hkname small{color:var(--soft)}
.hks{flex-basis:100%;font-size:.8rem;color:var(--soft)}.hkw{color:#A3152D}
.swl{font-size:.85rem;min-width:2.6rem}
.hkchev{border:1.5px solid var(--line);background:#fff;border-radius:12px;min-height:2.5rem;padding:0 .8rem;cursor:pointer;color:var(--ink);display:inline-flex;align-items:center;gap:.35rem;font:inherit;font-weight:600;font-size:.9rem;flex:none}
.hkchev[aria-expanded="true"]{background:#F3EEF9;border-color:#D7C4EA;color:var(--purple)}
.hkov{flex-basis:100%;font-size:.78rem;color:#A3152D;font-weight:600}
.hkc .hkdays button{min-width:3.2rem;padding:.4rem .7rem}
.hkb{border-top:1.5px dashed var(--line);padding:.8rem .9rem;display:grid;gap:.8rem;background:#FCFAF7}
.hkf{display:grid;gap:.35rem}.hkf .lb{font-weight:700}
.hkf select,.hkf input,.hkgrp input{border:2px solid var(--line);border-radius:12px;padding:.5rem .7rem;min-height:2.7rem;font:inherit;background:#fff}
.hkc .regchips{display:flex;flex-wrap:wrap;gap:.45rem}
.hkc .regchips button{border:2px solid var(--line);background:#fff;border-radius:99px;padding:.4rem 1.1rem;font:inherit;font-weight:600;min-height:2.6rem;cursor:pointer}
.hkc .regchips button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:#fff}
.hkc .linkbtn{border:0;background:none;color:var(--purple);text-decoration:underline;font:inherit;font-weight:600;cursor:pointer;justify-self:start;padding:0}
.hkrooms{display:flex;flex-wrap:wrap;gap:.35rem}
.hkrooms button{border:1.5px solid var(--line);background:#fff;border-radius:10px;padding:.3rem .55rem;font:inherit;font-weight:600;min-width:3.2rem;cursor:pointer}
.hkrooms button[aria-pressed="true"]{background:var(--ink);color:#fff;border-color:var(--ink)}
.hkrooms button.all[aria-pressed="true"]{background:#EDE4F6;color:var(--purple);border-color:#D7C4EA}
.hkrow2{grid-template-columns:auto 1fr auto;align-items:center}
.hkgrp{margin-top:1rem;padding-top:.9rem;border-top:1.5px dashed var(--line);display:grid;gap:.35rem}
.autot{display:block;font-size:.72rem;color:#2E7D5B;margin-bottom:.15rem}
.sheet.wide{width:min(48rem,100%)!important}
"""


def hk(h):
    i = h.index('function hkModal(){')
    j = h.index("document.addEventListener('click',e=>{if(e.target.closest('[data-hkset]'))hkModal()});")
    h = h[:i] + HK_JS + h[j:]
    h = _r(h, HK_PATCH, 'hk')
    return _css(h, HK_CSS)


# ---------- การจองทั้งหมด: กดรายการ → หน้ารายละเอียดเต็มจอ + ปุ่มกลับ (แบบหน้าลูกค้า) ----------
BKPAGE_JS = r"""
/* หน้ารายละเอียดการจอง — ลำดับแบบระบบโรงแรมระดับสูง (OPERA / Mews):
   หัว (เลขยืนยัน · แขก · สถานะ) → ข้อควรรู้ → ช่วงเข้าพัก → แขก + รายละเอียดการจอง | บัญชีค่าใช้จ่าย + ใบกำกับภาษี */
const BKI={
 phone:'<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/>',
 line:'<path d="M12 4c5 0 9 3.1 9 7s-4 7-9 7c-.7 0-1.4-.1-2-.2L6 20v-3.5C4.2 15.2 3 13.2 3 11c0-3.9 4-7 9-7z"/>',
 mail:'<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3.5 6.5 12 13l8.5-6.5"/>',
 co:'<path d="M4 21V5.5A1.5 1.5 0 0 1 5.5 4h8A1.5 1.5 0 0 1 15 5.5V21M15 10h3.5A1.5 1.5 0 0 1 20 11.5V21M3 21h18M8 8h3M8 12h3M8 16h3"/>',
 bed:'<path d="M3 18V7M3 14h18v4M21 14v-2.5A2.5 2.5 0 0 0 18.5 9H11v5"/><circle cx="7" cy="11" r="2"/>',
 user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.2 8-6.2s8 2.2 8 6.2"/>',
 flag:'<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>'};
const bki=k=>`<svg class="bki" viewBox="0 0 24 24" aria-hidden="true">${BKI[k]}</svg>`;
/* เนื้อหารายละเอียดการจอง (ใช้ทั้งหน้าเต็มและป๊อปอัปจากหน้าแรก/ปฏิทิน) */
function bkHTML(b,v,H,co,X,modal){
  const {esc,fmt}=H;
  const tmp=document.createElement('div');tmp.innerHTML=bkBody(v,H);const secs=[...tmp.querySelectorAll('.sec')];
  const secOf=t=>secs.find(x=>{const h=x.querySelector('h3');return h&&h.textContent.includes(t)});
  const paySec=secOf('การชำระเงิน'),orgSec=secOf('ในนามบริษัท');
  if(paySec)paySec.querySelector('h3').remove();if(orgSec)orgSec.querySelector('h3').remove();
  const n=v.visits||1,TY=n>=3?['มาบ่อย','often']:n===2?['มาซ้ำ','rep']:['ลูกค้าใหม่','new'];
  const nm=v.org?(v.gname||'ยังไม่แจ้งชื่อ'):v.guest;
  const TH=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
  const thD=s=>{const [Y,M,D]=String(s).split('-').map(Number);return D+' '+TH[M-1]};
  const row=(k,val)=>`<div class="kr"><span>${k}</span><div>${val}</div></div>`;
  const ct=(ic,val)=>`<div class="ctl">${bki(ic)}<div>${val}</div></div>`;
  const pv=v.pay,X0=X||{};
  const due=(b.paid||b.cancelled||b.noshow?0:(X0.net||0))+(X0.dep==='unpaid'?pv.dep:0)+(pv.svcRemain||0);
  const tx=b.tax&&typeof b.tax==='object'?b.tax:null;
  const ini=String(nm).replace(/^คุณ\s*/,'').replace(/^[เแโใไ]/,'').slice(0,1);
  const dd=s=>{const t=String(s),k=t.indexOf(' ');return `<em>${t.slice(0,k)}</em> ${esc(t.slice(k+1))}`};
  return `<article class="bkpv${modal?' inm':''}" aria-label="รายละเอียดการจอง ${v.no}">
   <header class="bkhd">
    <div class="bkpt"><div class="lbl">หมายเลขการจอง</div><div class="bkno">${v.no}</div>
     <div class="bkwho">${esc(v.title)}<span class="dot">·</span>ห้อง ${v.room}</div></div>
    <div class="bkst">${v.badges}${modal?`<button type="button" class="x bkx" data-close aria-label="ปิด">${ico('x')}</button>`:''}</div></header>
   <section class="bkstay" aria-label="ช่วงเข้าพัก">
    <div class="sd"><span class="lbl">เช็คอิน</span><b>${dd(v.ci)}</b><small>${esc(v.ciTxt)}</small></div>
    <div class="sn"><i>${v.nights} คืน</i></div>
    <div class="sd r"><span class="lbl">เช็คเอาท์</span><b>${dd(v.co)}</b><small>&nbsp;</small></div>
    <div class="sxr">
     <div class="sx">${bki('bed')}<div><span class="lbl">ห้อง</span><b>${esc(v.roomHTML)}</b><small>${esc(v.roomType)}</small></div></div>
     <div class="sx">${bki('user')}<div><span class="lbl">ผู้เข้าพัก</span><b>${v.pax} ท่าน</b><small>${v.adults!=null?`ผู้ใหญ่ ${v.adults} · เด็ก ${v.kids||0}`:''}</small></div></div>
     <div class="sx">${bki('flag')}<div><span class="lbl">วัตถุประสงค์</span><b>${esc(v.purpose||'ไม่ระบุ')}</b><small>${b.worksite?esc(b.worksite):'&nbsp;'}</small></div></div></div>
   </section>
   <div class="bkgrid">
     <section class="bkc bkguest"><div class="hd"><h3>ข้อมูลผู้เข้าพัก</h3>${b.cid?`<button type="button" class="more" data-gmore="${esc(b.cid)}">ดูเพิ่ม ›</button>`:''}</div>
      <div class="gh2"><div class="gav" aria-hidden="true">${esc(ini)}</div><div class="gnm"><h4>${esc(nm)}</h4><small>เข้าพักมาแล้ว ${n} ครั้ง</small></div></div>
      <div class="gchips"><span class="hi ty-${TY[1]}">${TY[0]}</span><span class="hi ${v.mem?'ty-mem':'ty-no'}">${v.mem?'เป็นสมาชิก':'ไม่เป็นสมาชิก'}</span>${v.org||b.gco?'<span class="hi ty-co">ลูกค้าบริษัท</span>':'<span class="hi ty-no">ลูกค้าทั่วไป</span>'}${b.bdayIn?`<span class="hi ty-bd">🎂 วันเกิด ${thD(b.bdayIn)}</span>`:''}</div>
      ${v.org&&v.org.contact?ct('user','ผู้ติดต่อ: '+esc(v.org.contact)+(v.org.cphone?' · '+esc(v.org.cphone):'')):''}
      ${ct('phone',esc(v.phone||'-'))}${ct('line',v.lineOn&&v.line?esc(v.line)+' <span class="badge b3">ผูกแล้ว</span>':'<span class="muted">ยังไม่ผูก LINE</span>')}
      ${v.email?ct('mail',esc(v.email)):''}${b.gco?ct('co',esc(b.gco)):''}</section>
     <section class="bkc"><div class="hd"><h3>รายละเอียดการจอง</h3></div>
      <div class="sub">ห้องพักและแพ็กเกจ</div>
      ${row('ประเภทห้อง',esc(v.roomType))}${row('ราคาห้อง',fmt(pv.rate)+' บาท / คืน')}
      ${row('อาหารเช้า',pv.bf?'รับ · '+fmt(pv.bf)+' บาท':'<span class="muted">ไม่รับ</span>')}
      ${row('บริการเพิ่มเติม',pv.svc&&pv.svc.length?pv.svc.map(x=>esc(x.name)+' '+x.qty+' '+esc(x.unit||'')+' · '+fmt(x.qty*x.price)+' บาท').join('<br>'):'<span class="muted">ไม่มี</span>')}
      ${pv.disc?row('ส่วนลด',(pv.code?esc(pv.code)+' · ':'')+'−'+fmt(pv.disc)+' บาท'):''}
      <div class="sub">ที่มาของการจอง</div>
      ${row('ช่องทางจอง',esc(v.ch))}${v.madeAt?row('จองเมื่อ',v.madeAt)+row('จองล่วงหน้า',v.lead+' วัน'):''}${row('การเช็คอิน',esc(v.ciTxt))}${b.note?row('หมายเหตุ',esc(b.note)):''}
      ${orgSec?`<div class="sub">ในนามบริษัท</div>${orgSec.innerHTML}`:''}</section>
      <section class="bkc"><div class="hd"><h3>ใบกำกับภาษี</h3>${tx?'<span class="badge b3">ต้องการ</span>':'<span class="badge b6">ไม่ขอ</span>'}</div>
       ${tx?row('ประเภท',esc(tx.type||'-'))+row('ออกในนาม',esc(tx.name||'-'))+row('เลขผู้เสียภาษี',esc(tx.id||'-'))+(tx.branch||tx.hq?row('สาขา',esc(tx.branch||tx.hq)):'')+row('ที่อยู่',esc(tx.addr||'-'))
         :row('เอกสาร','ใบเสร็จรับเงิน')+row('ในนาม',esc(nm))}</section>
      <section class="bkc bkpay"><div class="hd"><h3>บัญชีค่าใช้จ่าย</h3></div>
       <div class="due ${due>0?'open':'ok'}"><span>${due>0?'ยอดค้างชำระ':'ชำระครบแล้ว'}</span><b>${fmt(due)}<small> บาท</small></b></div>
       ${paySec?paySec.innerHTML:''}
       <div class="docbtns"><button type="button" class="btn ghost" data-pdoc="rc" ${b.paid?'':'disabled'}>${PRI}พิมพ์ใบเสร็จ</button><button type="button" class="btn ghost" data-pdoc="tx" ${tx&&b.paid?'':'disabled'}>${PRI}พิมพ์ใบกำกับภาษี</button></div>
       ${!b.paid?'<p class="dochint">ยังไม่ได้รับชำระค่าห้อง จึงยังออกใบเสร็จไม่ได้</p>':!tx?'<p class="dochint">แขกไม่ได้ขอใบกำกับภาษี</p>':''}</section>
   </div>
  </article>`;
}
function bkWire(root,b,v,H,co,X,ret){
  const nm=v.org?(v.gname||'ยังไม่แจ้งชื่อ'):v.guest,tx=b.tax&&typeof b.tax==='object'?b.tax:null;
  root.querySelectorAll('[data-pdoc]').forEach(x=>x.onclick=()=>bkDoc(x.dataset.pdoc,b,v,H,nm,tx,ret));
  const gm=root.querySelector('[data-gmore]');if(gm)gm.onclick=()=>{try{parent.postMessage({pbr:'custpage',gid:gm.dataset.gmore},'*')}catch(_){}};
}
function bkPage(b,v,H,co,X){
  const P=$('pList');let pg=$('bkpg');
  if(!pg){pg=document.createElement('div');pg.id='bkpg';pg.setAttribute('data-keep','');P.prepend(pg)}
  P.classList.add('pg');
  pg.innerHTML=`<button type="button" class="back" data-bkback>${ico('left')}กลับรายการจอง</button>${bkHTML(b,v,H,co,X,false)}`;
  pg.querySelectorAll('[data-bkback]').forEach(x=>x.onclick=bkBack);
  bkWire(pg,b,v,H,co,X,null);
  try{scrollTo(0,0)}catch(_){}
}
/* ป๊อปอัป (หน้าแรก/ปฏิทิน/โมดูลอื่น): รูปแบบเดียวกับหน้าเต็ม + ปุ่มดำเนินการของหน้านั้นด้านล่าง */
function bkModal(b,v,H,co,X,ctx){
  const acts=ctx&&ctx.actions&&ctx.actions.length?ctx.actions.map(a=>`<button class="btn ${a.pri?'pri':'ghost'}" data-act="${a.id}">${H.esc(a.label)}</button>`).join(''):'';
  const coBtns=co?'<button class="btn ghost" id="dQt">ใบเสนอราคา</button><button class="btn ghost" id="dIv">ใบแจ้งหนี้รวม</button>':'';
  const reopen=()=>bkModal(b,v,H,co,X,ctx);
  openModal(`<div class="sb bkmsb">${bkHTML(b,v,H,co,X,true)}</div><div class="sf">${acts}${coBtns}<button class="btn ${acts?'ghost':'pri'}" data-close>ปิด</button></div>`,()=>{
    const m=$('msheet');m.classList.add('xl','bkm');
    m.querySelectorAll('[data-close]').forEach(x=>x.onclick=closeModal);
    m.querySelectorAll('[data-act]').forEach(x=>x.onclick=()=>{try{parent.postMessage({pbr:'bkaction',id:x.dataset.act,no:b.no},'*')}catch(e){}closeModal()});
    if($('dQt')){$('dQt').onclick=()=>docModal('quote',B.filter(x=>x.no===b.no));$('dIv').onclick=()=>docModal('invoice',B.filter(x=>x.no===b.no))}
    bkWire(m,b,v,H,co,X,reopen)},false);
}
const PRI='<svg class="bki" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 9V4h10v5M7 17H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"/><rect x="7" y="14" width="10" height="7" rx="1"/></svg>';
/* ใบเสร็จรับเงิน / ใบกำกับภาษีเต็มรูป — แสดงตัวอย่างแล้วสั่งพิมพ์ (หรือบันทึกเป็น PDF จากหน้าพิมพ์) */
function bkDoc(k,b,v,H,nm,tx,ret){
  const {esc,fmt}=H,pv=v.pay,isT=k==='tx',D=n=>fD(n,{day:'numeric',month:'short',year:'numeric'});
  const items=[[`ค่าห้องพัก ${v.roomType} ห้อง ${b.room} · ${D(b.start)} – ${D(b.start+b.nights)} (${b.nights} คืน × ${fmt(pv.rate)})`,pv.base]];
  if(pv.bf)items.push(['อาหารเช้า',pv.bf]);
  (pv.svc||[]).forEach(x=>items.push([`${x.name} ${x.qty} ${x.unit||''} × ${fmt(x.price)}`,x.qty*x.price]));
  if(pv.disc)items.push([`ส่วนลด${pv.code?' ('+pv.code+')':''}`,-pv.disc]);
  const tot=items.reduce((a,x)=>a+x[1],0),net=tot*100/107,vat=tot-net,no=(isT?'TX-':'RC-')+b.no;
  const to=isT?`<small>ผู้ซื้อ / ผู้รับบริการ</small><b>${esc(tx.name||nm)}</b><small>เลขประจำตัวผู้เสียภาษี ${esc(tx.id||'-')}${tx.branch||tx.hq?' · '+esc(tx.branch||tx.hq):''}</small><small>${esc(tx.addr||'')}</small>`
                :`<small>ได้รับเงินจาก</small><b>${esc(nm)}</b>${v.phone?`<small>โทร ${esc(v.phone)}</small>`:''}`;
  openModal(`<div class="sh"><button class="x" data-close aria-label="ปิด">${ico('x')}</button><div class="rn">${isT?'ใบกำกับภาษี':'ใบเสร็จรับเงิน'}</div><div class="bkn">${no} · ${esc(isT?tx.name||nm:nm)}</div></div>
   <div class="sb"><div class="sb2"><div class="docp" id="docp">
    <div class="dtop"><div><b class="dh">พบรักรีสอร์ท</b><small>อ.อุบลรัตน์ จ.ขอนแก่น</small>${isT?'<small>เลขประจำตัวผู้เสียภาษี (รอใส่เลขของโรงแรม) · สำนักงานใหญ่</small>':''}</div>
     <div class="dno"><b>${isT?'ใบกำกับภาษี / ใบเสร็จรับเงิน':'ใบเสร็จรับเงิน'}</b><small>เลขที่ ${no}</small><small>วันที่ ${D(TODAY)}</small><small>อ้างอิงการจอง ${b.no}</small></div></div>
    <div class="dto">${to}</div>
    <table class="dt"><thead><tr><th>รายการ</th><th style="text-align:right">จำนวนเงิน (บาท)</th></tr></thead><tbody>${items.map(([t,a])=>`<tr><td>${esc(t)}</td><td style="text-align:right">${a<0?'−':''}${fmt(Math.abs(a))}</td></tr>`).join('')}</tbody></table>
    <div class="dsum">${isT?`<div><span>มูลค่าสินค้า/บริการ (ก่อนภาษี)</span><b>${(Math.round(net*100)/100).toLocaleString('th-TH',{minimumFractionDigits:2})}</b></div><div><span>ภาษีมูลค่าเพิ่ม 7%</span><b>${(Math.round(vat*100)/100).toLocaleString('th-TH',{minimumFractionDigits:2})}</b></div>`:''}
     <div class="g"><span>${isT?'รวมทั้งสิ้น (รวมภาษีแล้ว)':'รับชำระทั้งสิ้น'}</span><b>${fmt(tot)}</b></div></div>
    <div class="dnote">ค่าประกันห้อง ${fmt(pv.dep)} บาท เป็นเงินมัดจำคืนได้ ไม่รวมในเอกสารนี้</div>
    <div class="dsig"><div><span></span><small>ผู้รับเงิน</small></div></div>
    <div class="dnote">ต้นแบบ: ตรวจรูปแบบและเลขผู้เสียภาษีของโรงแรมก่อนใช้จริง</div></div></div></div>
   <div class="sf"><button class="btn pri" id="docPrint">${PRI}พิมพ์ / บันทึก PDF</button></div>`,()=>{
    const m=$('msheet');m.classList.add('xl');m.querySelectorAll('[data-close]').forEach(x=>x.onclick=ret||closeModal);
    $('docPrint').onclick=()=>{try{window.print()}catch(e){toast('พิมพ์ไม่ได้ในหน้านี้')}}},false);
}
function bkBack(){const P=$('pList'),pg=$('bkpg');if(pg)pg.remove();if(P)P.classList.remove('pg');if(window.__bkFromHome){window.__bkFromHome=false;try{parent.postMessage({pbr:'bkfullback'},'*')}catch(_){}}}
window.addEventListener('message',e=>{const d=e.data||{};if(d.pbr!=='bkfull')return;const b=B.find(x=>x.no===d.no)||BC.find(x=>x.no===d.no);if(!b)return;
  try{closeModal()}catch(_){}S.view='list';renderAll();window.__bkFromHome=true;detail(b.id);
  const bk=document.querySelector('#bkpg .back');if(bk)bk.lastChild.textContent='กลับหน้าแรก'});
function detail(id,ctx){"""

BKPAGE_CSS = """
#pList.pg>*:not(#bkpg){display:none!important}
#bkpg{display:block}
.bkpv{--hair:#EADFD6;--gold:#A9843A;display:grid;gap:.7rem;font-size:.92rem}
#bkpg .back{border:0;background:none;display:inline-flex;align-items:center;gap:.35rem;font:inherit;font-weight:600;font-size:.92rem;color:var(--purple);padding:.2rem .1rem;min-height:2.3rem;margin-bottom:.15rem;cursor:pointer}
#bkpg .back .ic,#bkpg .back svg{width:1.1rem;height:1.1rem}
.bkpv .lbl{display:block;font-size:.7rem;letter-spacing:.05em;color:var(--soft);font-weight:600;line-height:1.5}
.bkhd{background:var(--grad);color:#fff;border-radius:20px;padding:.7rem 1.15rem;display:flex;align-items:center;justify-content:space-between;gap:.8rem;flex-wrap:wrap}
.bkhd .lbl{color:rgba(255,255,255,.78)}
.bkno{font-family:var(--serif);font-size:1.4rem;font-weight:700;line-height:1.2;letter-spacing:.02em}
.bkwho{font-size:.95rem;font-weight:600;line-height:1.5}.bkwho .dot{margin:0 .4rem;opacity:.7}
.bkst{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center;justify-content:flex-end;background:none!important;border:0!important;padding:0!important;box-shadow:none!important}
.bkst .badge{font-size:.9rem;padding:.32rem .9rem;font-weight:700;box-shadow:0 3px 10px rgba(40,10,40,.2)}
.bkst .bkx{position:static;margin-left:.3rem}
.hi{font-size:.74rem;font-weight:700;padding:.14rem .62rem;border-radius:99px;white-space:nowrap}
.ty-new{background:#E0F2E3;color:#1F6B2B}.ty-rep{background:#FFF0CF;color:#7A4A00}.ty-often{background:#F4E2F6;color:#7B2A8E}
.ty-mem{background:#EAE0F8;color:#51308C}.ty-co{background:#E3EEFB;color:#1D4E89}.ty-bd{background:#FFE7EF;color:#B0244F}.ty-no{background:#EFEAE5;color:#6E5A68}
.bkc,.bkstay{background:#FFFDFB;border:1px solid var(--hair);border-radius:18px;box-shadow:0 8px 22px -20px rgba(60,20,50,.35)}
.bkstay{padding:.75rem 1.2rem .7rem;display:grid;grid-template-columns:auto 1fr auto;gap:0 1.1rem;align-items:center}
.bkstay .sd.r{text-align:right}
.bkstay .sd{display:flex;flex-direction:column}
.bkstay .sd b{font-size:1rem;font-weight:600;line-height:1.3;white-space:nowrap}
.bkstay .sd b em{font-family:var(--serif);font-style:normal;font-size:1.7rem;font-weight:700;line-height:1.1}
.bkstay small{font-size:.74rem;color:var(--soft);white-space:nowrap}
.bkstay .sn{position:relative;height:1.8rem;display:grid;place-items:center}
.bkstay .sn::before{content:'';position:absolute;left:0;right:.2rem;top:50%;border-top:1px solid #D7C4EA}
.bkstay .sn::after{content:'';position:absolute;right:0;top:calc(50% - 4px);border:4px solid transparent;border-left:7px solid #C9B3E2}
.bkstay .sn i{position:relative;font-style:normal;font-weight:700;color:var(--purple);background:#FFFDFB;border:1px solid #D7C4EA;border-radius:99px;padding:.1rem .75rem;font-size:.85rem}
.bkstay .sxr{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--hair);margin-top:.55rem;padding-top:.6rem}
.bkstay .sx{display:flex;gap:.5rem;align-items:flex-start;padding:0 1rem;border-left:1px solid var(--hair);min-width:0}.bkstay .sx:first-child{padding-left:0;border-left:0}
.bkstay .sx b{display:block;font-size:.95rem;line-height:1.4;font-weight:600;white-space:nowrap}
.bki{width:1.05rem;height:1.05rem;fill:none;stroke:var(--purple);stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;flex:none;opacity:.85;margin-top:.15rem}
.bkgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:1fr;gap:.7rem;align-items:stretch}
.bkgrid>.bkc{display:flex;flex-direction:column}
.bkcol{display:grid;gap:.7rem;min-width:0}
.bkc{padding:.75rem 1rem .8rem;min-width:0}
.bkc .hd{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.35rem;padding-bottom:.4rem;border-bottom:1px solid var(--hair);min-height:2rem}
.bkc .hd h3{margin:0;font-size:.95rem;font-weight:700;color:var(--ink);display:flex;align-items:center;gap:.45rem}
.bkc .hd h3::before{content:'';width:.28rem;height:.95rem;border-radius:3px;background:var(--grad)}
.bkc .hd .badge{font-size:.72rem}
.bkc .more{border:0;background:none;font:inherit;font-weight:700;font-size:.86rem;color:var(--purple);cursor:pointer;padding:.2rem;min-height:2rem}
.bkc .sub{font-size:.7rem;letter-spacing:.05em;color:var(--gold);font-weight:700;margin:.5rem 0 0}
.bkc .sub:first-of-type{margin-top:0}
.gh2{display:flex;gap:.65rem;align-items:center;padding:.1rem 0 .45rem}
.gav{width:2.4rem;height:2.4rem;border-radius:50%;background:var(--grad);color:#fff;display:grid;place-items:center;font-size:1.05rem;font-weight:700;flex:none;box-shadow:0 0 0 2px #fff,0 0 0 3px #E4D3EE}
.gnm{min-width:0}.gnm h4{font-size:1.05rem;margin:0;line-height:1.45}.gnm small{color:var(--soft);font-size:.78rem}
.gchips{display:flex;flex-wrap:wrap;gap:.3rem;padding-bottom:.45rem}
.bkguest .gh2{padding:.35rem 0 .7rem}.bkguest .gchips{padding-bottom:.75rem;gap:.4rem}
.bkguest .ctl{padding:.68rem 0;font-size:.92rem}.bkguest .ctl .bki{margin-top:.2rem}
.ctl{display:flex;align-items:flex-start;gap:.55rem;padding:.32rem 0;border-top:1px dotted var(--hair);font-weight:600;font-size:.88rem;line-height:1.5}
.ctl>div{min-width:0;overflow-wrap:anywhere}.ctl .badge{font-size:.7rem}
.kr,.bkc .kv{display:grid;grid-template-columns:6.4rem 1fr;gap:.5rem;padding:.3rem 0;border-bottom:1px dotted var(--hair);font-size:.86rem;line-height:1.5}
.kr:last-child{border-bottom:0}.kr>span,.bkc .kv>span{color:var(--soft)}.kr>div{font-weight:600;min-width:0;overflow-wrap:anywhere}
.muted{color:var(--soft);font-weight:500}
.bkpay .due{display:flex;justify-content:space-between;align-items:center;border-radius:13px;padding:.5rem .8rem;margin-bottom:.3rem}
.bkpay .due.open{background:linear-gradient(135deg,#FFF1F3,#FDE6EA);color:#A3152D}.bkpay .due.ok{background:linear-gradient(135deg,#F1FAF4,#E6F4EC);color:#2E7D5B}
.bkpay .due span{font-weight:700;font-size:.82rem}.bkpay .due b{font-family:var(--serif);font-size:1.4rem;line-height:1.2}.bkpay .due b small{font-family:inherit;font-size:.8rem;font-weight:600}
.bkpay .prow{display:flex;align-items:center;gap:.4rem;padding:.3rem 0;border-bottom:1px dotted var(--hair);font-size:.86rem}
.bkpay .prow>span:first-child{flex:1;color:var(--soft)}.bkpay .prow .badge{flex:none;font-size:.68rem}
.bkpay .prow.t{border-bottom:0;border-top:1px solid var(--hair);margin-top:.15rem;padding-top:.45rem;font-weight:700}.bkpay .prow.t>span:first-child{color:var(--ink)}
.docbtns{display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-top:.55rem}
.docbtns .btn{display:inline-flex;align-items:center;justify-content:center;gap:.35rem;min-height:2.5rem;font-weight:700;font-size:.82rem;padding:0 .4rem}
.docbtns .btn:disabled{opacity:.45;cursor:not-allowed}
.dochint{margin:.35rem 0 0;font-size:.76rem;color:var(--soft)}
.dsig{display:flex;justify-content:flex-end;margin-top:2.2rem}.dsig>div{display:flex;flex-direction:column;align-items:center;gap:.3rem}.dsig span{width:12rem;border-bottom:1px solid #999}.dsig small{color:#666}
.sheet.bkm{width:min(68rem,100%)!important;display:flex!important;flex-direction:column!important;overflow:hidden!important}
.bkmsb{padding:.8rem!important;display:block!important;background:var(--paper);flex:1 1 auto;min-height:0;overflow:auto!important}
.sheet.bkm .sf{flex:none}
.bkpv.inm .bkhd{border-radius:16px}
.bkpv.inm .bkst .bkx{width:2.3rem;height:2.3rem;border-radius:50%;border:0;background:rgba(255,255,255,.25);color:#fff;display:grid;place-items:center;cursor:pointer}
@media print{#bkpg{display:none!important}}
@media (max-width:700px){.bkgrid{grid-template-columns:1fr;grid-auto-rows:auto}.bkstay .sxr{grid-template-columns:1fr}.bkstay .sx{border-left:0;padding:.3rem 0}}
"""


def bkpage(h):
    h = _r(h, [
        ("function detail(id,ctx){", BKPAGE_JS),
        ("  openModal(`<div class=\"sh\"><button class=\"x\" data-close aria-label=\"ปิด\">${ico('x')}</button>${bkHead(v,H)}</div>",
         "  if(!ctx&&S.view==='list'){bkPage(b,v,H,co,{dep,net});return}\n  if(window.bkModal){bkModal(b,v,H,co,{dep,net},ctx);return}\n  openModal(`<div class=\"sh\"><button class=\"x\" data-close aria-label=\"ปิด\">${ico('x')}</button>${bkHead(v,H)}</div>"),
        ("if(a=t.closest('[data-view]')){S.view=a.dataset.view;renderAll();return}",
         "if(a=t.closest('[data-view]')){bkBack();S.view=a.dataset.view;renderAll();return}"),
    ], 'book')
    return _css(h, BKPAGE_CSS)


# ---------- บันทึกการจองย้อนหลัง (เจ้าของเท่านั้น · ต้องรัน 14_backdate.sql) ----------
def bkback(h):
    h = _r(h, [
        ("    if(F.start<TODAY)p.push('วันเข้าพักเป็นวันที่ผ่านมาแล้ว');",
         "    if(F.back){if(F.start+F.nights>TODAY)p.push('บันทึกย้อนหลัง: วันเช็คเอาท์ต้องไม่เกินวันนี้')}else if(F.start<TODAY)p.push('วันเข้าพักเป็นวันที่ผ่านมาแล้ว');"),
        ("const t0=dt(TODAY), canPrev=CAL.y", "const t0=dt(TODAY), canPrev=F.back||CAL.y"),
        ("const day=first+d, past=day<TODAY,", "const day=first+d, past=F.back?day>TODAY:day<TODAY,"),
        ("     <div class=\"kbar\"><button type=\"button\" class=\"kctl\" id=\"ctlDate\"",
         "     ${PP_OWNER?`<label class=\"kback ${F.back?'on':''}\"><input type=\"checkbox\" id=\"fBack\" ${F.back?'checked':''}><span><b>บันทึกการจองย้อนหลัง</b><small>สำหรับใส่ข้อมูลลูกค้าเก่า · บันทึกเป็นเข้าพักและเช็คเอาท์แล้ว จ่ายครบ (เลือกเงินสด/โอนในขั้นชำระเงิน) · ไม่เก็บค่าประกันห้อง · เจ้าของเท่านั้น</small></span></label>`:''}\n"
         "     <div class=\"kbar\"><button type=\"button\" class=\"kctl\" id=\"ctlDate\""),
        ("    $('roomList').onchange=e=>{if(e.target.id==='fBf'){F.bf=e.target.checked;refresh()}};",
         "    $('roomList').onchange=e=>{if(e.target.id==='fBf'){F.bf=e.target.checked;refresh()}};\n"
         "    if($('fBack'))$('fBack').onchange=e=>{F.back=e.target.checked;e.target.closest('.kback').classList.toggle('on',F.back);"
         "if(F.back){if(F.start+F.nights>TODAY){F.start=TODAY-1;F.nights=1}F.pay='now'}else if(F.start<TODAY){F.start=TODAY;F.nights=1}"
         "try{const d=dt(F.start);CAL.y=d.getUTCFullYear();CAL.m=d.getUTCMonth();CAL.pending=false}catch(_){}F.checked=true;recheck();refresh();"
         "toast(F.back?'โหมดบันทึกย้อนหลัง: เลือกวันเข้าพักที่ผ่านมาแล้วได้':'ปิดโหมดบันทึกย้อนหลัง')};"),
        ("ppSave('book',{guest:", "ppSave('book',{backdate:!!F.back,guest:"),
        ("pay:F.mode==='co'?(F.payer==='self'?'later':F.pay):F.pay,", "pay:F.back?'now':(F.mode==='co'?(F.payer==='self'?'later':F.pay):F.pay),"),
    ], 'book-back')
    return _css(h, """
.kback{display:flex;gap:.7rem;align-items:flex-start;border:1.5px dashed #D9C6A0;background:#FFFBF2;border-radius:14px;padding:.6rem .85rem;margin-bottom:.7rem;cursor:pointer}
.kback.on{border-style:solid;border-color:#B08A3E;background:#FFF4DC}
.kback input{width:1.3rem;height:1.3rem;margin-top:.15rem;accent-color:#B08A3E;flex:none}
.kback b{display:block;color:#6E4F12}.kback small{display:block;color:#8A6A2A;font-size:.8rem;line-height:1.5}
""")


# ---------- ป๊อปอัปการจองในหน้าแรก: ย่อจากหน้ารายละเอียดการจอง (ข้อมูลหลัก) ให้ดูได้ในจอเดียว ----------
HOMEPOP_JS = r"""
const HPI={phone:'<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/>',
 line:'<path d="M12 4c5 0 9 3.1 9 7s-4 7-9 7c-.7 0-1.4-.1-2-.2L6 20v-3.5C4.2 15.2 3 13.2 3 11c0-3.9 4-7 9-7z"/>',
 mail:'<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3.5 6.5 12 13l8.5-6.5"/>',
 co:'<path d="M4 21V5.5A1.5 1.5 0 0 1 5.5 4h8A1.5 1.5 0 0 1 15 5.5V21M15 10h3.5A1.5 1.5 0 0 1 20 11.5V21M3 21h18M8 8h3M8 12h3M8 16h3"/>',
 bed:'<path d="M3 18V7M3 14h18v4M21 14v-2.5A2.5 2.5 0 0 0 18.5 9H11v5"/><circle cx="7" cy="11" r="2"/>',
 user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.2 8-6.2s8 2.2 8 6.2"/>',
 flag:'<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>'};
const hpi=k=>`<svg class="bki" viewBox="0 0 24 24" aria-hidden="true">${HPI[k]}</svg>`;
function homePopHTML(v,H,b,due){
  const {esc,fmt}=H,pv=v.pay;
  const tmp=document.createElement('div');tmp.innerHTML=bkBody(v,H);
  const paySec=[...tmp.querySelectorAll('.sec')].find(x=>{const h=x.querySelector('h3');return h&&h.textContent.includes('การชำระเงิน')});
  if(paySec)paySec.querySelector('h3').remove();
  const n=v.visits||1,TY=n>=3?['มาบ่อย','often']:n===2?['มาซ้ำ','rep']:['ลูกค้าใหม่','new'];
  const nm=v.org?(v.gname||'ยังไม่แจ้งชื่อ'):v.guest;
  const row=(k,val)=>`<div class="kr"><span>${k}</span><div>${val}</div></div>`;
  const ct=(ic,val)=>`<div class="ctl">${hpi(ic)}<div>${val}</div></div>`;
  const dd=s=>{const t=String(s),k=t.indexOf(' ');return `<em>${t.slice(0,k)}</em> ${esc(t.slice(k+1))}`};
  const taxOn=v.tax&&v.tax!=='ไม่ต้องการ',X=(typeof BKX!=='undefined'&&BKX[v.no])||{},coName=(v.org&&v.org.name)||X.co||'';
  const TH=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'],bd=X.bd?(+X.bd.slice(8,10))+' '+TH[+X.bd.slice(5,7)-1]:'';
  return `<article class="bkpv hpv">
   <header class="bkhd"><div class="bkpt"><div class="lbl">หมายเลขการจอง</div><div class="bkno">${v.no}</div>
     <div class="bkwho">${esc(v.title)}<span class="dot">·</span>ห้อง <span id="mRoom">${v.room}</span></div></div>
    <div class="bkst">${bd?`<span class="badge hbd" title="วันเกิดของผู้เข้าพักอยู่ในช่วงเข้าพัก">🎂 วันเกิด ${bd}</span>`:''}${v.badges}<button type="button" class="x bkx" id="closeX" aria-label="ปิด">${ico('x')}</button></div></header>
   <div class="hmrow"><button type="button" class="hmore" data-bkfull="${esc(v.no)}">ดูเพิ่มเติม ›</button></div>
   <section class="bkstay">
    <div class="sd"><span class="lbl">เช็คอิน</span><b>${dd(v.ci)}</b><small>${esc(v.ciTxt)}</small></div>
    <div class="sn"><i>${v.nights} คืน</i></div>
    <div class="sd"><span class="lbl">เช็คเอาท์</span><b>${dd(v.co)}</b><small>&nbsp;</small></div>
    <div class="sx">${hpi('bed')}<div><span class="lbl">ห้อง</span><b>${v.roomHTML}</b><small>${esc(v.roomType)}</small></div></div>
    <div class="sx">${hpi('user')}<div><span class="lbl">ผู้เข้าพัก</span><b>${v.pax} ท่าน</b><small>${v.adults!=null?`ผู้ใหญ่ ${v.adults} · เด็ก ${v.kids||0}`:''}</small></div></div>
    <div class="sx">${hpi('flag')}<div><span class="lbl">วัตถุประสงค์</span><b>${esc(v.purpose||'ไม่ระบุ')}</b><small>&nbsp;</small></div></div>
   </section>
   <div class="hgrid">
    <section class="bkc bkguest"><div class="hd"><h3>ข้อมูลผู้เข้าพัก</h3>${v.regBtn?'<button type="button" class="more" id="mReg">สมัครสมาชิก ›</button>':''}</div>
     <div class="gnm"><h4>${esc(nm)}</h4><small>เข้าพักมาแล้ว ${n} ครั้ง</small></div>
     <div class="gchips"><span class="hi ty-${TY[1]}">${TY[0]}</span><span class="hi ${v.mem?'ty-mem':'ty-no'}">${v.mem?'เป็นสมาชิก':'ไม่เป็นสมาชิก'}</span><span class="hi ${coName||v.grp==='ลูกค้าบริษัท'?'ty-co':'ty-no'}">${coName||v.grp==='ลูกค้าบริษัท'?'ลูกค้าบริษัท':'ลูกค้าทั่วไป'}</span></div>
     ${v.org&&v.org.contact?ct('user','ผู้ติดต่อ: '+esc(v.org.contact)):''}
     ${ct('phone',esc(v.phone||'-'))}${ct('line',v.lineOn&&v.line?esc(v.line)+' <span class="badge b3">ผูกแล้ว</span>':'<span class="muted">ยังไม่ผูก LINE</span>')}
     ${coName?ct('co',esc(coName)):''}</section>
    <section class="bkc"><div class="hd"><h3>รายละเอียดการจอง</h3></div>
     ${row('ประเภทห้อง',esc(v.roomType))}${row('ราคาห้อง',fmt(pv.rate)+' บาท / คืน')}
     ${row('อาหารเช้า',pv.bf?'รับ · '+fmt(pv.bf)+' บาท':'<span class="muted">ไม่รับ</span>')}
     ${row('บริการเพิ่มเติม',pv.svc&&pv.svc.length?pv.svc.map(x=>esc(x.name)+' '+x.qty+' '+esc(x.unit||'')).join(', '):'<span class="muted">ไม่มี</span>')}
     ${row('ช่องทางจอง',esc(v.ch))}${row('ใบกำกับภาษี',taxOn?'<span class="badge b3">ต้องการ</span>':'<span class="muted">ไม่ขอ</span>')}
     ${v.note?row('หมายเหตุ',esc(v.note)):''}</section>
    <section class="bkc bkpay"><div class="hd"><h3>บัญชีค่าใช้จ่าย</h3></div>
     <div class="due ${due>0?'open':'ok'}"><span>${due>0?'ยอดค้างชำระ':'ชำระครบแล้ว'}</span><b>${fmt(due)}<small> บาท</small></b></div>
     ${paySec?paySec.innerHTML:''}</section>
   </div>
  </article>`;
}
"""

HOMEPOP_CSS = """
.sheet.hpop{width:min(68rem,100%)!important;display:flex!important;flex-direction:column!important;overflow:hidden!important}
.sheet.hpop .sb{padding:.8rem!important;display:block!important;overflow:auto;flex:1 1 auto;min-height:0;background:var(--paper)}
.sheet.hpop .sf{flex:none}
.hpv{--hair:#EADFD6;--gold:#A9843A;display:grid;gap:.6rem;font-size:.9rem;text-align:left}
.hpv .lbl{display:block;font-size:.68rem;letter-spacing:.05em;color:var(--soft);font-weight:600;line-height:1.5}
.hpv .bkhd{background:var(--grad);color:#fff;border-radius:16px;padding:.6rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:.8rem;flex-wrap:wrap}
.hpv .bkhd .lbl{color:rgba(255,255,255,.78)}
.hpv .bkno{font-family:var(--serif);font-size:1.3rem;font-weight:700;line-height:1.2}
.hpv .bkwho{font-size:.92rem;font-weight:600;line-height:1.5}.hpv .bkwho .dot{margin:0 .4rem;opacity:.7}
.hpv .bkst{display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;justify-content:flex-end}
.hpv .bkst .badge{font-size:.86rem;padding:.3rem .85rem;font-weight:700;box-shadow:0 3px 10px rgba(40,10,40,.2)}
.hpv .bkx{position:static!important;width:2.2rem;height:2.2rem;border-radius:50%;border:0;background:rgba(255,255,255,.25);color:#fff;display:grid;place-items:center;cursor:pointer;margin-left:.2rem}
.hpv .bkc,.hpv .bkstay{background:#FFFDFB;border:1px solid var(--hair);border-radius:16px}
.hpv .bkstay{position:relative;padding:.6rem 1rem .55rem;display:grid;grid-template-columns:auto minmax(3.5rem,8rem) auto repeat(3,minmax(0,1fr));gap:0 .9rem;align-items:center}
.hpv .hmrow{display:flex;justify-content:flex-end;margin:-.35rem 0 -.45rem}
.hpv .hmore{border:0;background:none;font:inherit;font-size:.8rem;font-weight:700;color:var(--purple);cursor:pointer;padding:.15rem .2rem;min-height:1.6rem}
.hpv .hbd{background:#FFE7EF!important;color:#B0244F!important}
.hpv .sd{display:flex;flex-direction:column}.hpv .sd.r{text-align:right}
.hpv .sd b{font-size:.95rem;font-weight:600;line-height:1.3;white-space:nowrap}
.hpv .sd b em{font-family:var(--serif);font-style:normal;font-size:1.5rem;font-weight:700;line-height:1.1}
.hpv .bkstay small{font-size:.72rem;color:var(--soft)}
.hpv .sn{position:relative;height:1.7rem;display:grid;place-items:center}
.hpv .sn::before{content:'';position:absolute;left:0;right:.2rem;top:50%;border-top:1px solid #D7C4EA}
.hpv .sn::after{content:'';position:absolute;right:0;top:calc(50% - 4px);border:4px solid transparent;border-left:7px solid #C9B3E2}
.hpv .sn i{position:relative;font-style:normal;font-weight:700;color:var(--purple);background:#FFFDFB;border:1px solid #D7C4EA;border-radius:99px;padding:.08rem .7rem;font-size:.82rem}
.hpv .sxr{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--hair);margin-top:.45rem;padding-top:.45rem}
.hpv .sx{display:flex;gap:.45rem;align-items:flex-start;padding-left:.9rem;border-left:1px solid var(--hair);min-width:0}
.hpv .sx b{display:block;font-size:.9rem;line-height:1.4;font-weight:600}
.hpv .bki{width:1rem;height:1rem;fill:none;stroke:var(--purple);stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;flex:none;opacity:.85;margin-top:.15rem}
.hgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem;align-items:stretch}
.hpv .bkc{padding:.65rem .9rem .7rem;min-width:0}
.hpv .hd{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.3rem;padding-bottom:.35rem;border-bottom:1px solid var(--hair);min-height:1.9rem}
.hpv .hd h3{margin:0;font-size:.9rem;font-weight:700;color:var(--ink);display:flex;align-items:center;gap:.4rem}
.hpv .hd h3::before{content:'';width:.26rem;height:.9rem;border-radius:3px;background:var(--grad)}
.hpv .more{border:0;background:none;font:inherit;font-weight:700;font-size:.8rem;color:var(--purple);cursor:pointer;padding:.15rem;min-height:1.9rem}
.hpv .gnm h4{font-size:1rem;margin:.1rem 0 0;line-height:1.45}.hpv .gnm small{color:var(--soft);font-size:.75rem}
.hpv .gchips{display:flex;flex-wrap:wrap;gap:.3rem;padding:.35rem 0 .4rem}
.hpv .hi{font-size:.7rem;font-weight:700;padding:.12rem .55rem;border-radius:99px;white-space:nowrap}
.hpv .ty-new{background:#E0F2E3;color:#1F6B2B}.hpv .ty-rep{background:#FFF0CF;color:#7A4A00}.hpv .ty-often{background:#F4E2F6;color:#7B2A8E}
.hpv .ty-mem{background:#EAE0F8;color:#51308C}.hpv .ty-co{background:#E3EEFB;color:#1D4E89}.hpv .ty-no{background:#EFEAE5;color:#6E5A68}
.hpv .ctl{display:flex;align-items:flex-start;gap:.5rem;padding:.38rem 0;border-top:1px dotted var(--hair);font-weight:600;font-size:.86rem;line-height:1.5}
.hpv .ctl>div{min-width:0;overflow-wrap:anywhere}.hpv .ctl .badge{font-size:.68rem}
.hpv .kr{display:grid;grid-template-columns:6.2rem 1fr;gap:.45rem;padding:.27rem 0;border-bottom:1px dotted var(--hair);font-size:.84rem;line-height:1.5}
.hpv .kr:last-child{border-bottom:0}.hpv .kr>span{color:var(--soft)}.hpv .kr>div{font-weight:600;min-width:0;overflow-wrap:anywhere}
.hpv .kr .badge{font-size:.68rem}
.hpv .muted{color:var(--soft);font-weight:500}
.hpv .bkpay .due{display:flex;justify-content:space-between;align-items:center;border-radius:12px;padding:.45rem .75rem;margin-bottom:.25rem}
.hpv .bkpay .due.open{background:linear-gradient(135deg,#FFF1F3,#FDE6EA);color:#A3152D}.hpv .bkpay .due.ok{background:linear-gradient(135deg,#F1FAF4,#E6F4EC);color:#2E7D5B}
.hpv .bkpay .due span{font-weight:700;font-size:.8rem}.hpv .bkpay .due b{font-family:var(--serif);font-size:1.3rem;line-height:1.2}.hpv .bkpay .due b small{font-family:inherit;font-size:.78rem;font-weight:600}
.hpv .bkpay .prow{display:flex;align-items:center;gap:.35rem;padding:.27rem 0;border-bottom:1px dotted var(--hair);font-size:.82rem;flex-wrap:wrap}
.hpv .bkpay .prow>span:first-child{flex:1;color:var(--soft)}.hpv .bkpay .prow .badge{flex:none;font-size:.66rem}
.hpv .bkpay .prow.t{border-bottom:0;border-top:1px solid var(--hair);margin-top:.15rem;padding-top:.4rem;font-weight:700}.hpv .bkpay .prow.t>span:first-child{color:var(--ink)}
@media (max-width:900px){.hgrid{grid-template-columns:1fr 1fr}.hgrid>.bkpay{grid-column:1/-1}}
"""


def homepop(h):
    i = h.index("function renderSheet(){")
    h = h[:i] + HOMEPOP_JS + h[i:]
    h = _r(h, [
        ("""  $('sheet').innerHTML=`
    <div class="sh">
      <button class="x" id="closeX" aria-label="ปิด">${ico('x')}</button>
      ${bkHead(vv,HH)}
    </div>
    <div class="sb"><div class="sb2">${bkBody(vv,HH)}
    </div></div>
    <div class="sf">${foot}</div>`;
  $('sheet').className='sheet xl';""",
         """  $('sheet').innerHTML=`<div class="sb">${homePopHTML(vv,HH,b,outTot)}</div>
    <div class="sf">${foot}</div>`;
  $('sheet').className='sheet xl hpop';
  {const bf=$('sheet').querySelector('[data-bkfull]');if(bf)bf.onclick=()=>{try{parent.postMessage({pbr:'bkfull',no:bf.dataset.bkfull},'*')}catch(_){}}}"""),
    ], 'home-pop')
    return _css(h, HOMEPOP_CSS)


# ---------- เมนูการเงินบันทึกจริง (ต้องรัน 15_fin.sql) ----------
# เก็บ "ส่วนที่เมนูการเงินเป็นเจ้าของ" เป็นสถานะชุดเดียว: บริการเพิ่มเติม/รับชำระบริการ/เครดิต/ใบเรียกเก็บอื่นๆ (SV)/
# รายการรับ-จ่ายที่พนักงานเพิ่ม/ยกเลิกรายการ/เปิด-ปิดกะ/ปิดยอด/บัญชีธนาคาร · ค่าห้องที่รับในเมนูนี้ → pp_act pay (ทุกเมนูเห็น)
FIN_JS = r"""
/* ============ บันทึกจริง: สถานะเมนูการเงิน ============ */
const PPF_SES=Date.now().toString(36);
const ppfBig=v=>typeof v==='string'&&v.length>350000?'sample':v;
function ppFinSnap(){
  const bills={},sv=[];
  BILLS.forEach(b=>{
    if(!b.room){sv.push(Object.assign({},b,{fresh:false,pays0:(b.pays0||[]).map(p=>Object.assign({},p,{slip:ppfBig(p.slip)})),pays:undefined}));return}
    const items=b.items||[], svc=(b.pays0||[]).filter(p=>p.tag==='svc').map(p=>Object.assign({},p,{slip:ppfBig(p.slip)}));
    if(items.length||svc.length||b.credit||b.qrAcct)bills[b.no+'|'+b.room]={items,svc,credit:b.credit||null,qrAcct:b.qrAcct||null};
  });
  return {v:1,bills,sv,
    txns:TXNS.filter(t=>!t.auto||t.close).map(t=>Object.assign({},t,{photo:ppfBig(t.photo)})),
    shifts:SHIFTS,shiftLog:SHIFT_LOG,vars:VARS,closed:[...CLOSED_DAYS],
    hf:{actual:HF.actual,lastDrop:HF.lastDrop,note:HF.note,openCnt:HF.openCnt,openWho:HF.openWho},banks:BANKS};
}
let ppfLast='',ppfT=null,ppfBusy=false;
function ppFinSave(){clearTimeout(ppfT);ppfT=setTimeout(()=>{
  let j;try{j=JSON.stringify(ppFinSnap())}catch(e){return}
  if(j===ppfLast||ppfBusy)return; ppfBusy=true;
  fetch(top.location.origin+'/api/app?part=fin',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:j})
   .then(r=>r.json().catch(()=>({})).then(x=>{if(!r.ok)throw new Error(x.error||('รหัส '+r.status));ppfLast=j;try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}}))
   .catch(e=>toast('⚠️ บันทึกเมนูการเงินไม่สำเร็จ: '+e.message)).finally(()=>{ppfBusy=false})},700)}
function ppFinRestore(st){
  if(!st||!st.v)return;
  Object.entries(st.bills||{}).forEach(([k,x])=>{const [no,room]=k.split('|');const b=BILLS.find(y=>y.no===no&&y.room===room);if(!b)return;
    const have=new Set((b.items||[]).map(i=>i.id)),add=(x.items||[]).filter(i=>!have.has(i.id));
    b.items=(b.items||[]).concat(add);b.total+=add.reduce((a,i)=>a+i.qty*i.price,0);
    const ps=new Set((b.pays0||[]).map(p=>p.fid).filter(Boolean)),sp=(x.svc||[]).filter(p=>!p.fid||!ps.has(p.fid));
    b.pays0=(b.pays0||[]).concat(sp);b.pays=(b.pays||[]).concat(sp);b.paid=Math.min(b.total,b.pays.reduce((a,p)=>a+p.amt,0));
    if(x.credit)b.credit=x.credit;if(x.qrAcct)b.qrAcct=x.qrAcct;rebuildTxns(b)});
  (st.sv||[]).forEach(x=>{if(BILLS.some(b=>b.no===x.no&&!b.room))return;const b=Object.assign({},x,{pays:(x.pays0||[]).slice()});BILLS.push(b);rebuildTxns(b);
    const n=+String(b.no).split('-').pop();if(n>=_sv)_sv=n});
  (st.txns||[]).forEach(t=>{if(!TXNS.some(y=>y.id===t.id))TXNS.push(t)});
  Object.assign(SHIFTS,st.shifts||{});(st.shiftLog||[]).forEach(x=>SHIFT_LOG.push(x));(st.vars||[]).forEach(x=>VARS.push(x));
  (st.closed||[]).forEach(d=>CLOSED_DAYS.add(+d));
  const hf=st.hf||{};['actual','lastDrop','note','openCnt','openWho'].forEach(k=>Object.assign(HF[k],hf[k]||{}));
  if(Array.isArray(st.banks)&&st.banks.length)BANKS=st.banks;
}
try{ppFinRestore(FIN_STATE)}catch(e){console.error(e)}
try{ppfLast=JSON.stringify(ppFinSnap())}catch(e){}
/* ค่าห้องที่รับในเมนูการเงิน → บันทึกลงการจอง (หน้าแรก/การจองเห็นด้วย) */
function ppFinRoomPay(no,m,amt){return fetch(top.location.origin+'/api/app?part=act',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({k:'pay',no,m,room_amt:amt})}).then(r=>r.json().catch(()=>({})).then(x=>{if(!r.ok)throw new Error(x.error||('รหัส '+r.status))})).catch(e=>toast('⚠️ บันทึกค่าห้องไม่สำเร็จ: '+e.message))}
"""


def finsave(h):
    h = _r(h, [
        # id ของรายการที่พนักงานเพิ่มไม่ซ้ำข้ามการโหลด
        ("function pushTxn(o){const x=Object.assign({id:'t'+(txnSeq++),auto:false,photo:null},o); if(!x.id) x.id='t'+(txnSeq++); TXNS.push(x)}",
         "function pushTxn(o){const x=Object.assign({id:'t'+(txnSeq++)+(o&&o.auto?'':'_'+PPF_SES),auto:false,photo:null},o); if(!x.id) x.id='t'+(txnSeq++)+'_'+PPF_SES; TXNS.push(x)}"),
        ("/* ============ init ============ */\nrenderBill();", FIN_JS + "\n/* ============ init ============ */\nrenderBill();"),
        # บันทึกทุกครั้งที่หน้าจอเปลี่ยน (เฉพาะส่วนที่เมนูการเงินเป็นเจ้าของ · ไม่ส่งซ้ำถ้าไม่เปลี่ยน)
        ("function renderTxn(){", "function renderTxn(){try{ppFinSave()}catch(_){}"),
        ("function renderBill(){", "function renderBill(){try{ppFinSave()}catch(_){}"),
        ("function renderHf(){", "function renderHf(){try{ppFinSave()}catch(_){}"),
        # ค่าห้องที่รับในเมนูการเงิน
        ("  if(b.room&&roomPay>0) try{parent.postMessage({pbr:'finpay',",
         "  if(b.room&&roomPay>0) ppFinRoomPay(b.no,PY.m,roomPay);\n  if(b.room&&roomPay>0) try{parent.postMessage({pbr:'finpay',"),
    ], 'fin-save')
    return h


# ---------- เมนูที่เหลือบันทึกจริง (ต้องรัน 16_modstate.sql) ----------
# แต่ละเมนูเก็บ "ส่วนที่ผู้ใช้แก้" เป็นสถานะชุดเดียว · บันทึกอัตโนมัติทุกครั้งที่หน้าจอเปลี่ยน · โหลดกลับตอนเปิดหน้า
PPM_HELPER = r"""
const PPM_BIG=(k,v)=>typeof v==='string'&&v.length>350000?'':v;
function ppmSaver(k,snap){let last=null,t=null,busy=false;
  try{last=JSON.stringify(snap(),PPM_BIG)}catch(_){}
  return ()=>{clearTimeout(t);t=setTimeout(()=>{let j;try{j=JSON.stringify(snap(),PPM_BIG)}catch(_){return}
    if(j===last||busy)return;busy=true;
    fetch(top.location.origin+'/api/app?part=mod',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{"k":'+JSON.stringify(k)+',"data":'+j+'}'})
     .then(r=>r.json().catch(()=>({})).then(x=>{if(!r.ok)throw new Error(x.error||('รหัส '+r.status));last=j;try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}}))
     .catch(e=>{try{toast('⚠️ บันทึกไม่สำเร็จ: '+e.message)}catch(_){}}).finally(()=>{busy=false})},700)}}
const ppArr=(a,v)=>{if(Array.isArray(v))a.splice(0,a.length,...v)};
const ppObj=(o,v)=>{if(v&&typeof v==='object')Object.assign(o,v)};
"""

MODSPEC = {
    'hk': dict(funcs=['render', 'renderRepair'], js=r"""
const __st=PPM_STATE.hk;
if(__st){ppArr(FOUND,__st.found);ppArr(LOST,__st.lost);if(Array.isArray(__st.repairs))REPAIRS=__st.repairs;
  try{fid=Math.max(fid,...FOUND.map(x=>+x.id||0));lid=Math.max(lid,...LOST.map(x=>+x.id||0));rid=Math.max(rid,...REPAIRS.map(x=>+String(x.id).replace(/\D/g,'')||0))}catch(_){}
  try{render()}catch(e){console.error(e)}}
window.__ppm=ppmSaver('hk',()=>({found:FOUND,lost:LOST,repairs:REPAIRS}));
"""),
    'crmtool': dict(funcs=['render', 'renderLb'], js=r"""
const __st=PPM_STATE.crmtool||{},__lb0=LB.map(x=>x.id),__ln0=LN.map(x=>x.id);
let __lbGone=__st.lbGone||[],__lnGone=__st.lnGone||[];
if(PPM_STATE.crmtool){ppObj(LS,__st.ls);ppArr(MS,__st.ms);ppArr(GONE,__st.gone);ppArr(CAMPS,__st.camps);ppArr(EXTRA_CO,__st.extra);
  (__st.ds||[]).forEach(d=>{const i=DS.findIndex(x=>x.id===d.id);if(i>=0)DS[i]=d;else DS.push(d)});
  LB=LB.filter(x=>!__lbGone.includes(x.id));LN=LN.filter(x=>!__lnGone.includes(x.id));
  CL.forEach(c=>{const p=(__st.clp||{})[c.id];if(Array.isArray(p))c.promos=p});
  try{render()}catch(e){console.error(e)}}
window.__ppm=ppmSaver('crmtool',()=>{__lbGone=[...new Set(__lbGone.concat(__lb0.filter(id=>!LB.some(x=>x.id===id))))];
  __lnGone=[...new Set(__lnGone.concat(__ln0.filter(id=>!LN.some(x=>x.id===id))))];
  return {ls:LS,ms:MS,ds:DS,lbGone:__lbGone,lnGone:__lnGone,gone:GONE,camps:CAMPS,extra:EXTRA_CO,clp:Object.fromEntries(CL.filter(c=>c.promos&&c.promos.length).map(c=>[c.id,c.promos]))}});
"""),
    'cust': dict(funcs=['render', 'renderSTP'], js=r"""
const __st=PPM_STATE.cust;
if(__st){CO.forEach(k=>{const p=(__st.cop||{})[k.id];if(Array.isArray(p))k.promos=p})}
if(PPM_STATE.stp)STP.confirmed=!!PPM_STATE.stp.confirmed;
if(__st||PPM_STATE.stp){try{render()}catch(e){console.error(e)}}
const __a=ppmSaver('cust',()=>({cop:Object.fromEntries(CO.filter(k=>k.promos&&k.promos.length).map(k=>[k.id,k.promos]))})),__b=ppmSaver('stp',()=>({confirmed:!!STP.confirmed}));
window.__ppm=()=>{__a();__b()};
"""),
    'crm': dict(funcs=['renderSTP'], js=r"""
if(PPM_STATE.stp){STP.confirmed=!!PPM_STATE.stp.confirmed;try{renderSTP()}catch(_){}}
window.__ppm=ppmSaver('stp',()=>({confirmed:!!STP.confirmed}));
"""),
    'mkt': dict(funcs=['renderResults', 'renderGV', 'renderKitchen', 'renderDetail', 'updateKBadge'], js=r"""
const __st=PPM_STATE.mkt;
if(__st){if(Array.isArray(__st.campaigns))campaigns=__st.campaigns;if(Array.isArray(__st.plans))plans=__st.plans;ppObj(GV,__st.gv);
  (__st.segs||[]).forEach(g=>{if(!segments.some(x=>x.id===g.id))segments.push(g)});
  [renderResults,renderGV,renderFeed,updateKBadge].forEach(f=>{try{f()}catch(_){}})}
if(PPM_STATE.stp&&typeof STP==='object')STP.confirmed=!!PPM_STATE.stp.confirmed;
window.__ppm=ppmSaver('mkt',()=>({campaigns,plans,gv:GV,segs:segments.filter(x=>x.custom)}));
"""),
}


def modsave(h, key):
    import ctx, json as _j
    sp = MODSPEC[key]
    st = (ctx.MOCK or {}).get('mod_state') or {}
    for f in sp['funcs']:
        h = _r(h, [('function %s(){' % f, 'function %s(){try{window.__ppm&&window.__ppm()}catch(_){}' % f)], 'mod-' + key)
    data = _j.dumps(st, ensure_ascii=False).replace('</', '<\\/')
    k = h.rindex('</script>')
    return h[:k] + '\n/* ---- บันทึกจริง ---- */\nconst PPM_STATE=' + data + ';\n' + PPM_HELPER + '\ntry{\n' + sp['js'] + '\n}catch(e){console.error(e)}\n' + h[k:]


# ---------- การตลาด: ปุ่มไมค์ (ยังจำลอง) → ปุ่มส่งข้อความ ----------
SEND_SVG = ('<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5.5 11.5 12 5l6.5 6.5"/></svg>')


def mktsend(h):
    h = _r(h, [
        ('<button class="mic" id="micBtn" aria-label="สั่งด้วยเสียง">🎙</button>', '<button class="mic" id="micBtn" aria-label="ส่งให้ AI">' + SEND_SVG + '</button>'),
        ('<button class="mic" id="kmic" aria-label="สั่งด้วยเสียง">🎙</button>', '<button class="mic" id="kmic" aria-label="ส่งให้ AI">' + SEND_SVG + '</button>'),
        ("$('#micBtn').onclick=()=>toast('ในระบบจริงกดค้างเพื่อพูดสั่งงานได้');",
         "$('#micBtn').onclick=()=>{const i=$('#aiIn');if(!i.value.trim()){i.focus();toast('พิมพ์สิ่งที่อยากให้ AI ปรับก่อน แล้วกดส่ง');return}i.onkeydown({key:'Enter',target:i})};"),
        ("if(q('#kmic')){toast('ในระบบจริงกดค้างเพื่อพูดสั่งงานได้');return}",
         "if(q('#kmic')){const i=$('#kaiIn');if(!i||!i.value.trim()){i&&i.focus();toast('พิมพ์สิ่งที่อยากให้ AI ปรับก่อน แล้วกดส่ง');return}i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return}"),
    ], 'mkt-send')
    return _css(h, ".mic{display:grid;place-items:center;cursor:pointer;transition:transform .15s}.mic:active{transform:scale(.92)}")
