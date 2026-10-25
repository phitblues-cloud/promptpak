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
@media (min-width:901px){.listcol,.thrcol,.pancol{height:calc(100vh - 6.4rem)!important}
#app{padding-bottom:.6rem!important}.listcol,.thrcol,.pancol{min-height:26rem!important}}
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
        ('const floor=7.9*parseFloat(', 'const floor=7.7*parseFloat('),
        # ความสูงหัวกล่องคงที่ทุกแชท ไม่ยืดหดตามเนื้อหา
        ('const H=Math.ceil(Math.max(rh(th),rh(sb),gH+rh(fz),floor));', 'const H=Math.ceil(Math.max(gH+rh(fz),floor));'),
    ], 'linechat')
    return _css(h, LC_CSS)


def apply(M):
    if 'cust' in M:
        M['cust'] = custprof(cust(M['cust']))
    if 'linechat' in M:
        M['linechat'] = chatsave(linechat(M['linechat']))
    return M


# ---------- หน้าแชท LINE: ปุ่มบันทึกจริง (ต้องรัน supabase/07_chat.sql) ----------
CHAT_HELPER = r"""
function ppChat(k,d){
  const body=JSON.stringify(Object.assign({k},d||{}));
  return fetch(top.location.origin+'/api/app?part=chat',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body})
   .then(r=>r.json().catch(()=>({})).then(j=>{if(!r.ok)throw new Error(j.error||('รหัส '+r.status));try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}return j}));
}
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
     """  if(!txt){toast('ส่งรูป/ไฟล์เข้า LINE ยังไม่รองรับ · พิมพ์ข้อความแทนได้');return}
  if(window.__ppSending)return;window.__ppSending=1;const sb=document.querySelector('[data-act="send"]');if(sb){sb.disabled=true;sb.textContent='กำลังส่ง…'}
  const hadFile=PEND.length;
  ppChat('send',{key:c.key,body:txt}).then(j=>{c.m.push(['s',txt,nowTm()]); PEND=[]; if($('#rt'))$('#rt').value=''; c.st='wait'; c.ago=0; c.read=true; render();
    toast((j.line==='sent'?'ส่งเข้า LINE แล้ว':'บันทึกแล้ว · แชทตัวอย่าง ไม่ได้ส่งเข้า LINE')+(hadFile?' · รูป/ไฟล์ยังไม่ได้ส่ง':''))})
   .catch(ppChatFail).finally(()=>{window.__ppSending=0;const b2=document.querySelector('[data-act="send"]');if(b2){b2.disabled=false;b2.textContent='ส่ง'}});"""),
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
  let h=`<button class="back" data-back>${ico('left')}กลับรายการลูกค้า</button>
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
   <div class="fld full"><label for="dno">เลข${DOCT[D.t]} *</label><input id="dno" ${D.t==='id'?'inputmode="numeric" maxlength="17" placeholder="X-XXXX-XXXXX-XX-X"':'maxlength="12" placeholder="เช่น AA1234567" style="text-transform:uppercase"'} value="${esc(D.t==='id'?nidFmt(D.no):D.no)}"><small class="hint" id="dnoh">${D.t==='id'?'ระบบตรวจหลักสุดท้ายให้อัตโนมัติ':'ตัวอักษรและตัวเลขตามหน้าหนังสือเดินทาง'}</small></div>
   <div class="fld full consent"><label class="ck"><input type="checkbox" id="dcon" ${D.consent?'checked':''}> <span>แจ้งลูกค้าแล้วว่าโรงแรมเก็บข้อมูลเพื่อทะเบียนผู้พักตามกฎหมาย และ<b>ลูกค้ายินยอมให้เก็บภาพบัตร</b></span></label>
    <small class="hint">ภาพบัตรไม่บังคับ · ดูได้เฉพาะเจ้าของ · ลบอัตโนมัติ 1 ปีหลังเข้าพักครั้งล่าสุด</small></div>
   <div class="fld full"><span class="lb">ภาพบัตร (ถ้ามี)</span>${D.img?`<div class="docprev"><img src="${D.img}" alt="ภาพบัตร"><button type="button" class="btn ghost sm" id="dimgx">ลบภาพ</button></div>`:
     `<label class="btn ghost docpick${D.consent?'':' off'}"><input type="file" id="dfile" accept="image/*" capture="environment" ${D.consent?'':'disabled'} hidden>${ico('plus')} ถ่ายรูป / เลือกรูปบัตร</label>${D.consent?'':'<small class="hint">ติ๊กยินยอมก่อนจึงแนบภาพได้</small>'}`}</div>`}
function docBind(D,redraw){
  const q=s=>$('msheet').querySelector(s);
  $('msheet').querySelectorAll('[data-dt]').forEach(b=>b.onclick=()=>{if(D.t!==b.dataset.dt){D.t=b.dataset.dt;D.no=''}redraw()});
  q('#dno').oninput=e=>{{const er=$('msheet').querySelector('.err');if(er)er.remove()}if(D.t==='id'){const d=e.target.value.replace(/\D/g,'').slice(0,13);D.no=d;e.target.value=d.length===13?nidFmt(d):d;
      const h=q('#dnoh');if(h){const er=d.length===13?docErr('id',d):'';h.textContent=er||(d.length===13?'✓ เลขถูกต้อง':'ระบบตรวจหลักสุดท้ายให้อัตโนมัติ');h.style.color=er?'#B3263E':(d.length===13?'#2E7D5B':'')}}
    else{D.no=e.target.value.toUpperCase().replace(/[^0-9A-Z]/g,'').slice(0,12)}};
  q('#dcon').onchange=e=>{D.consent=e.target.checked;if(!D.consent)D.img='';redraw()};
  if(q('#dfile'))q('#dfile').onchange=e=>{const f=e.target.files[0];if(!f)return;ppImg(f).then(u=>{D.img=u;redraw()}).catch(()=>toast('อ่านไฟล์ภาพไม่ได้'))};
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
  const STEPS=['ข้อมูลบริษัท','ใบกำกับภาษีและการชำระเงิน','ผู้ติดต่อ','ตรวจสอบและยืนยัน'],LAST=STEPS.length;
  let step=1,err='',busy=false;
  const inp=(id,lab,key,o={})=>`<div class="fld${o.full?' full':''}"><label for="${id}">${lab}</label><input id="${id}" data-kk="${key}" ${o.im?`inputmode="${o.im}"`:''} ${o.ml?`maxlength="${o.ml}"`:''} placeholder="${o.ph||''}" value="${esc(K[key]||'')}"></div>`;
  const chips=(key,list,lab,lb)=>`<div class="fld full"><span class="lb">${lab}</span><div class="regchips">${list.map(x=>`<button type="button" data-ckk="${key}" data-cv="${x}" aria-pressed="${K[key]===x}">${lb?lb(x):x}</button>`).join('')}</div></div>`;
  function body(){
    if(step===1) return inp('k1','ชื่อบริษัท / หน่วยงาน *','name',{ph:'เช่น บริษัท ตัวอย่าง จำกัด',full:true})+inp('k2','ชื่อย่อ (แสดงบนการ์ดหน้าแรก)','short',{ph:'เช่น ตัวอย่าง'})
      +'<div></div>'+chips('type',COTYPE,'ประเภทธุรกิจ *')+inp('k3','สถานที่ทำงานใกล้โรงแรม (ถ้ามี)','site',{ph:'เช่น โรงงาน/หน้างาน ต.โคกสูง อ.อุบลรัตน์',full:true})
      +'<small class="hint full" style="margin-top:-.5rem">ที่ที่พนักงานของบริษัทมาทำงานระหว่างพักกับเรา ซึ่งอาจไม่ใช่ที่อยู่ออกใบกำกับภาษี</small>';
    if(step===2) return inp('k4','เลขประจำตัวผู้เสียภาษี (13 หลัก) *','tax',{im:'numeric',ml:13,ph:'0105XXXXXXXXX'})+inp('k5','สำนักงานใหญ่ / สาขา','branch',{ph:'สำนักงานใหญ่ หรือ สาขาที่ 00001'})
      +inp('k6','ที่อยู่สำหรับออกใบกำกับภาษี *','addr',{ph:'เลขที่ ถนน ตำบล อำเภอ จังหวัด รหัสไปรษณีย์',full:true})
      +chips('pay',Object.keys(COPAY),'วิธีชำระค่าห้อง',x=>COPAY[x])+(K.pay==='credit'?inp('k7','เครดิต (วัน)','credit',{im:'numeric',ml:3,ph:'เช่น 30'}):'');
    if(step===3) return inp('k8','ชื่อผู้ติดต่อ *','cname',{ph:'เช่น คุณสมศักดิ์ ใจดี'})+inp('k9','ตำแหน่ง / บทบาท','crole',{ph:'เช่น ฝ่ายจัดซื้อ, ผู้จองห้องให้ทีม'})
      +inp('k10','เบอร์โทร *','cphone',{im:'tel',ph:'08X-XXX-XXXX'})+inp('k11','อีเมล (ส่งใบแจ้งหนี้)','cemail',{ph:'account@company.co.th'})+inp('k12','LINE','cline',{ph:'ชื่อ LINE หรือ ID'})
      +`<div class="fld"><span class="lb">&nbsp;</span><label class="ck" style="display:flex;gap:.5rem;align-items:center;min-height:3rem"><input type="checkbox" id="k13" ${K.cdecide?'checked':''} style="width:1.3rem;height:1.3rem;min-height:0;accent-color:var(--pink)"> เป็นผู้ตัดสินใจเลือกที่พัก</label></div>`;
    const kv=(a,b)=>`<div class="kvr"><span>${a}</span><div><b>${esc(b||'-')}</b></div></div>`;
    return `<div class="full regsum">${kv('ชื่อบริษัท',K.name)}${kv('ชื่อย่อ',K.short)}${kv('ประเภทธุรกิจ',K.type)}${kv('สถานที่ทำงานใกล้โรงแรม',K.site)}${kv('เลขผู้เสียภาษี',K.tax)}${kv('สำนักงานใหญ่ / สาขา',K.branch)}${kv('ที่อยู่ออกใบกำกับภาษี',K.addr)}
      ${kv('วิธีชำระ',K.pay?coPayTxt(K):'')}${kv('ผู้ติดต่อ',K.cname+(K.crole?' · '+K.crole:'')+(K.cdecide?' (ผู้ตัดสินใจ)':''))}${kv('เบอร์โทร',K.cphone)}${kv('อีเมล',K.cemail)}${kv('LINE',K.cline)}</div>`;
  }
  function vErr(){
    if(step===1){if(!K.name.trim())return 'กรุณากรอกชื่อบริษัท';if(!K.type)return 'กรุณาเลือกประเภทธุรกิจ';
      const n=strip(K.name).toLowerCase(),d=CO.find(x=>x.id!==k.id&&strip(x.name).toLowerCase()===n);if(d)return `${d.name} มีในระบบแล้ว`}
    if(step===2){if(K.tax.length!==13)return 'เลขผู้เสียภาษีต้องมี 13 หลัก';if(!thaiIdOk(K.tax))return 'เลขผู้เสียภาษีไม่ถูกต้อง กรุณาตรวจอีกครั้ง';
      const d=CO.find(x=>x.id!==k.id&&String(x.tax||'').replace(/\D/g,'')===K.tax);if(d)return `เลขผู้เสียภาษีนี้คือ ${d.name} ซึ่งมีในระบบแล้ว`;
      if(!K.addr.trim())return 'กรุณากรอกที่อยู่สำหรับออกใบกำกับภาษี';if(K.pay==='credit'&&!(+K.credit>0))return 'กรุณากรอกจำนวนวันเครดิต'}
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
    const d={name:K.name.trim(),short:K.short.trim(),type:K.type,site:K.site.trim(),tax:K.tax,branch:K.branch.trim()||'สำนักงานใหญ่',addr:K.addr.trim(),pay:K.pay,credit:K.pay==='credit'?String(+K.credit||0):'0',
      cname:K.cname.trim(),crole:K.crole.trim(),cphone:K.cphone.trim(),cemail:K.cemail.trim(),cline:K.cline.trim(),cdecide:K.cdecide?'1':'0'};
    ppCust('comp',{gid:cid,data:d}).then(()=>{
      const o=isNew?{id:cid,contact:null,promos:[]}:k;
      Object.assign(o,{name:d.name,short:d.short,type:d.type,site:d.site,tax:d.tax,hq:d.branch,addr:d.addr,pay:d.pay,credit:+d.credit,cname:d.cname,crole:d.crole,phone:d.cphone,email:d.cemail,cline:d.cline,cdecide:K.cdecide});
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
  const STEPS=['ข้อมูลส่วนตัวและบัตร','ติดต่อและที่อยู่','การเข้าพัก','ตรวจสอบและยืนยัน'],LAST=STEPS.length;
  let step=1,err='',busy=false;
  const nextNo=()=>pbm('M'+String(memSeq+1).padStart(3,'0'));
  const inp=(id,lab,k,o={})=>`<div class="fld${o.full?' full':''}"><label for="${id}">${lab}</label><input id="${id}" data-k="${k}" ${o.type?`type="${o.type}"`:''} ${o.im?`inputmode="${o.im}"`:''} placeholder="${o.ph||''}" value="${esc(R[k]||'')}"></div>`;
  const chips=(k,list,lab)=>`<div class="fld full"><span class="lb">${lab}</span><div class="regchips" role="group" aria-label="${lab}">${list.map(x=>`<button type="button" data-ck="${k}" data-cv="${x}" aria-pressed="${R[k]===x}">${x}</button>`).join('')}</div></div>`;
  const dupOf=()=>{const d=digits(R.phone);return d.length>=9?CU.find(x=>digits(x.phone)===d&&(!pre||x.id!==pre.id)):null};
  function body(){
    if(step===1) return inp('rg1','ชื่อ-สกุล *','name',{ph:'เช่น คุณสมชาย ใจดี',full:true})+chips('gender',GEN,'เพศ')+inp('rg3','วันเกิด (ถ้ามี)','bday',{type:'date'})
      +'<div class="full regsec">เอกสารยืนยันตัวตน</div>'+docFields(D)+(pre&&pre.doc&&!pre.doc.no?`<div class="full hint">ลูกค้ามีเอกสารในระบบแล้ว (${esc(pre.doc.mask)}) · กรอกเลขอีกครั้งเพื่อยืนยัน</div>`:'');
    if(step===2) return inp('rg4','เบอร์โทร *','phone',{type:'tel',im:'tel',ph:'08X-XXX-XXXX'})+inp('rg5','Line ID','line',{ph:'ชื่อ LINE หรือ ID'})
      +inp('rg6','ที่อยู่','addr',{ph:'บ้านเลขที่ หมู่ ตำบล อำเภอ',full:true})+inp('rg7','จังหวัด','prov',{ph:'เช่น ขอนแก่น'});
    if(step===3) return `<div class="fld full"><label for="rg8">บริษัท (ถ้ามี)</label><select id="rg8"><option value="">— ไม่มี —</option>${CO.map(x=>`<option value="${x.id}" ${x.id===R.company?'selected':''}>${esc(x.name)}</option>`).join('')}</select><small class="hint">บริษัทใหม่ เพิ่มได้ที่แท็บ "บริษัท" → ปุ่ม "เพิ่ม"</small></div>`
      +chips('purpose',PUR,'วัตถุประสงค์การเข้าพัก (ถ้ามี)')+inp('rg9','ความต้องการพิเศษ','special',{ph:'เช่น ไม่ทานเนื้อหมู ขอห้องชั้นล่าง',full:true});
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
      if(step===1)docBind(D,draw);
      if(step===3){const sc=$('rg8');if(sc)sc.onchange=()=>{R.company=sc.value}}
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
         "+row('เลขผู้เสียภาษี',`<b>${esc(k.tax||'-')}</b>`)+row('สำนักงานใหญ่ / สาขา',`<b>${esc(k.hq||'-')}</b>`)+row('ที่อยู่ออกใบกำกับภาษี',`<b>${esc(k.addr||'-')}</b>`)+row('วิธีชำระค่าห้อง',`<b>${esc(coPayTxt(k))}</b>`)"
         "+row('ผู้ติดต่อ',(ct?`<button class=\"linkbtn\" data-open=\"c:${ct.id}\">${esc(k.cname||ct.name)}</button>`:`<b>${esc(k.cname||'-')}</b>`)+(k.crole?` <span class=\"hint\">${esc(k.crole)}</span>`:'')+(k.cdecide?' <span class=\"badge m-yes\">ผู้ตัดสินใจ</span>':''))"
         "+row('เบอร์โทร',`<b>${esc(k.phone||'-')}</b>`)+row('อีเมล',`<b>${esc(k.email||'-')}</b>`)+row('LINE',`<b>${esc(k.cline||'-')}</b>`)}"),
        ("function closeModal(){$('mscrim').classList.remove('open');",
                "function closeModal(){$('mscrim').classList.remove('open');$('msheet').classList.remove('wide');")], 'cust-close')
    return _css(h, PROF_CSS)
