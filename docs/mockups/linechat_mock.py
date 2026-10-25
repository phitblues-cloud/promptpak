D = '/tmp/claude-0/-home-claude/537c4068-9ce5-5d35-b8d8-eec2c8cc48dc/scratchpad/mock/'
h = open(D + 'lc_before.html').read()


def R(old, new):
    global h
    assert h.count(old) == 1, old[:80]
    h = h.replace(old, new)


# 1) หัวแชท: ชื่อใหญ่ขึ้น · บรรทัด 2 ชื่อจริง + LINE · บรรทัด 3 บริษัท · ย้ายป้ายสมาชิก/กลุ่มลูกค้าไปแผงขวา · ป้ายเรื่องไปไว้กับ AI สรุป
R("""<div class="th-h"><div>${nmH}<small>${c.real&&c.real!==c.name?esc(c.real)+' · ':''}LINE: ${esc(c.line)}</small></div><div class="tags"><span class="grp ${grp[1]}">${esc(grp[0])}</span>${warnIc(warnLv(c,a),'2.1rem')}<button type="button" class="btn ghost sm pinfo" data-act="pop" aria-label="เปิดแผงเครื่องมือ">เครื่องมือ</button></div><div class="gtags"><span class="tg">${memOf(c)?'เป็นสมาชิก':'ไม่ได้เป็นสมาชิก'}</span><span class="tg">${SEG[c.seg]}</span>${c.co?`<span class="tg tg-co">🏢 ${esc(c.co)}</span>`:''}</div></div>""",
  """<div class="th-h"><div>${nmH}<small>${c.real&&c.real!==c.name?esc(c.real)+' · ':''}LINE: ${esc(c.line)}</small>${c.co?`<small class="coline">🏢 ${esc(c.co)}</small>`:''}</div><div class="tags"><span class="tg">${memOf(c)?'เป็นสมาชิก':'ไม่ได้เป็นสมาชิก'}</span><span class="tg">${SEG[c.seg]}</span>${warnIc(warnLv(c,a),'2.1rem')}<button type="button" class="btn ghost sm pinfo" data-act="pop" aria-label="เปิดแผงเครื่องมือ">เครื่องมือ</button></div></div>""")
# 2) AI สรุป: กล่องเล็ก 2 บรรทัด กดเพื่ออ่านทั้งหมด + ป้ายเรื่อง
R("""<div class="aisum"><h3>✦ AI สรุป</h3><p>${esc(a.sum)}</p></div>""",
  """<button type="button" class="aisum2" onclick="this.classList.toggle('open')" title="กดเพื่ออ่านทั้งหมด"><span class="aih"><b>✦ AI สรุป</b><span class="grp ${grp[1]}">${esc(grp[0])}</span></span><span class="ait">${esc(a.sum)}</span></button>""")
# 3) แผงขวา: สถานะการเข้าพักไปอยู่ขวา ใต้ "ดูเพิ่มเติม" · ป้ายสมาชิก/กลุ่มลูกค้าอยู่ใต้ห้อง
R("""<div class="statbox"><div class="sr1"><span class="bs ${bs[1]}">${bs[0]}</span>${bd.unpaid?'<span class="tg tg-red">ยังไม่ชำระ</span>':''}<button type="button" class="more" data-act="more">ดูเพิ่มเติม ›</button></div>${(()=>{const p=bparts(c),pu=purpOf(c);return p?`<div class="sr2"><div class="rmw"><span class="rmb">${esc(p[0])}</span><span class="rmr">${esc(p[1])}</span></div>${pu?`<div class="purp">${esc(pu)}</div>`:''}</div>`:''})()}""",
  """<div class="statbox"><div class="sr1x"><div>${(()=>{const p=bparts(c),pu=purpOf(c);return p?`<div class="rmw"><span class="rmb">${esc(p[0])}</span><span class="rmr">${esc(p[1])}</span></div>${pu?`<div class="purp">${esc(pu)}</div>`:''}`:'<div class="purp">ยังไม่มีการจอง</div>'})()}</div><div class="srr"><button type="button" class="more" data-act="more">ดูเพิ่มเติม ›</button><span class="bs ${bs[1]}">${bs[0]}</span>${bd.unpaid?'<span class="tg tg-red">ยังไม่ชำระ</span>':''}</div></div>""")
css = """
.th-h h2{font-size:1.75rem!important;line-height:1.2}
.th-h .coline{margin-top:.15rem;color:#2E7D5B;font-weight:700}
.aisum2{display:block;width:calc(100% - 2.2rem);margin:.6rem 1.1rem 0;text-align:left;border:1.5px solid transparent;border-radius:14px;cursor:pointer;
  background:linear-gradient(#fff,#fff) padding-box,linear-gradient(110deg,#8B5CF6,#EC4899 60%,#FB923C) border-box;padding:.45rem .75rem;font:inherit;flex:none}
.aisum2 .aih{display:flex;align-items:center;gap:.5rem;font-size:.74rem}
.aisum2 .aih b{background:linear-gradient(90deg,#7C3AED,#DB2777);-webkit-background-clip:text;background-clip:text;color:transparent}
.aisum2 .aih .grp{font-size:.7rem;padding:.02rem .55rem}
.aisum2 .aih i{margin-left:auto;font-style:normal;color:var(--soft);font-weight:600}
.aisum2.open .aih i{visibility:hidden}
.aisum2 .ait{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:.9rem;line-height:1.45;color:#2A1F33;margin-top:.15rem}
.aisum2.open .ait{-webkit-line-clamp:unset}
.sr1x{display:flex;justify-content:space-between;align-items:flex-start;gap:.6rem}
.srr{display:flex;flex-direction:column;align-items:flex-end;gap:.3rem}
.srr .more{margin:0}
.gtags2{display:flex;flex-wrap:wrap;gap:.3rem}
.gtags2 .tg{font-size:.72rem;padding:.04rem .5rem}
"""
k = h.rindex('</style>')
h = h[:k] + css + h[k:]

# 4) รายการแชท: ปุ่มเรียง "ล่าสุด | ด่วน" (ล่าสุดเป็นค่าเริ่มต้น) · ปุ่มกรองเล็กลง · ตัวกรองประเภทเรื่อง · ป้ายเรื่องใหญ่ขึ้น
R("""<button type="button" data-sort="ai" aria-pressed="${S.sort==='ai'}">ด่วนก่อน</button><button type="button" data-sort="new" aria-pressed="${S.sort==='new'}">ล่าสุด</button>""",
  """<button type="button" data-sort="new" aria-pressed="${S.sort==='new'}">ล่าสุด</button><button type="button" data-sort="ai" aria-pressed="${S.sort==='ai'}">ด่วน</button>""")
R("const S={f:'all',tp:'all',q:'',sel:2,sort:'ai',", "const S={f:'all',tp:'all',q:'',sel:2,sort:'new',")
R("""<div class="fzone"><div class="flt" role="tablist" aria-label="สถานะ">${fl}</div></div>""",
  """<div class="fzone"><div class="flt" role="tablist" aria-label="สถานะ">${fl}</div><select class="tpsel" aria-label="ประเภทเรื่อง" onchange="S.tp=this.value;render()">${[['all','ทุกเรื่อง',all.length],...(nu?[['urg','ด่วน',nu]]:[]),...TOPICS.filter(t=>tc[t[0]]).map(t=>[t[0],t[1],tc[t[0]]])].map(([k,t,v])=>`<option value="${k}" ${S.tp===k?'selected':''}>${k==='all'?'ประเภทเรื่อง: ทุกเรื่อง':t} (${v})</option>`).join('')}</select></div>""")
css2 = """
.gbox .flt button,.flt button{padding:.05rem .55rem!important;font-size:.74rem!important;min-height:1.8rem!important}
.fzone{display:flex!important;flex-wrap:wrap;align-items:center;gap:.4rem}
.tpsel{min-height:1.8rem;border:1.5px solid var(--line);border-radius:99px;padding:0 1.6rem 0 .7rem;background-color:#fff;font:inherit;font-size:.74rem;font-weight:600;color:var(--ink);max-width:100%}
.tpc{font-size:.8rem!important;padding:.12rem .6rem!important;border-radius:8px!important}
.aisum2 .aih .grp{font-size:.85rem!important;padding:.12rem .7rem!important;font-weight:800}
"""
k = h.rindex('</style>')
h = h[:k] + css2 + h[k:]
open(D + 'lc_after.html', 'w').write(h)
print('ok')
