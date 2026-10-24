import sys
sys.path.insert(0, '/home/claude/promptpak/renderer')
import render
D = '/tmp/claude-0/-home-claude/537c4068-9ce5-5d35-b8d8-eec2c8cc48dc/scratchpad/mock/'
M = render.modules(render.base_mock(), '2026-10-24T10:00', only=['cust'])
h = M['cust']
open(D + 'cust_before.html', 'w').write(h)

a = h.index('  h+=`<div class="fbar"><div class="fgrp"><span class="lb">จัดเรียงตาม</span>')
b = h.index("  h+='</div>';\n  if(isC){")
new = r"""  const mc=(v,t)=>`<button data-mem="${v}" aria-pressed="${S.f.member===v}">${t}</button>`;
  h+=`<div class="fbar2">${isC?`<div class="sortchips" role="group" aria-label="สถานะสมาชิก">${mc('all','ทั้งหมด')}${mc('yes','สมาชิก')}${mc('no','ไม่ใช่สมาชิก')}</div>`:''}`;
  if(isC) h+=`${sel('fType','type',[['all','กลุ่มลูกค้า: ทั้งหมด'],['new','ใหม่'],['gen','ทั่วไป'],['rep','มาซ้ำ'],['often','มาบ่อย'],['lost','หาย']])}
    ${sel('fPur','purpose',[['all','วัตถุประสงค์: ทั้งหมด'],['ทำงาน','ทำงาน'],['แวะพัก','แวะพัก'],['งานบุญ','งานบุญ'],['ราชการ/อบรม','ราชการ/อบรม']])}
    <button class="iconbtn" id="ruleBtn" title="เกณฑ์กลุ่มลูกค้า" aria-label="เกณฑ์กลุ่มลูกค้า">${ico('info')}</button>`;
  h+=`<label class="sortsel">เรียง<select data-sortsel>${(isC?[['recent','พักล่าสุด'],['old','เก่า-ใหม่'],['new','ใหม่-เก่า'],['name','ตัวอักษร ก–ฮ']]:[['name','ชื่อ ก–ฮ'],['spend','ยอดใช้จ่ายสูงสุด']]).map(([v,t])=>`<option value="${v}" ${S.sort===v?'selected':''}>${t}</option>`).join('')}</select></label>`;
  if(isC) h+=`<button class="linkbtn" id="resetF">ล้างตัวกรอง</button>`;
"""
h = h[:a] + new + h[b:]
css = (".fbar2{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;background:var(--card);border:1.5px solid var(--line);"
       "border-radius:20px;padding:.6rem .8rem;margin-bottom:.9rem}"
       ".fbar2 select{min-height:2.7rem;border:1.5px solid var(--line);border-radius:99px;padding:0 2rem 0 1rem;background-color:#fff;font:inherit;font-weight:600}"
       ".sortsel{display:flex;align-items:center;gap:.4rem;margin-left:auto;color:var(--soft);font-weight:600}"
       ".iconbtn{border:0;background:none;color:var(--purple);display:grid;place-items:center;width:2.4rem;height:2.4rem}")
h = h.replace('.fbar{display:flex;', css + '.fbar{display:flex;', 1)
h = h.replace("  else if(S.sort==='old') L.sort((a,b)=>a.c.added-b.c.added);",
              "  else if(S.sort==='recent') L.sort((a,b)=>(b.s.last??-1e9)-(a.s.last??-1e9));\n  else if(S.sort==='old') L.sort((a,b)=>a.c.added-b.c.added);")
h = h.replace("S={view:'list',sub:'cust',sort:'name',", "S={view:'list',sub:'cust',sort:'recent',")
h = h.replace("  if(a=t.closest('[data-sort]')){S.sort=a.dataset.sort;render();return}",
              "  if(a=t.closest('[data-sort]')){S.sort=a.dataset.sort;render();return}\n  if(a=t.closest('[data-mem]')){S.f.member=a.dataset.mem;render();return}")
# รหัสลูกค้าแบบใหม่ G0001 (ลำดับตามวันที่เข้าระบบ) + ปุ่มดูโปรไฟล์แบบลูกศร
# ง. ไม่แสดงรหัสลูกค้า · รหัสสมาชิก PBM-0001
h = h.replace('<div class="c-code num">${c.id}</div>', '', 1)
h = h.replace('<div>#</div><div>รหัสลูกค้า</div><div>ชื่อ-สกุล</div>', '<div>#</div><div>ชื่อ-สกุล</div>', 1)
h = h.replace("const memBadge=(c,s)=>c.memberNo?`<span class=\"badge m-yes\">เป็นสมาชิก</span>`", "const pbm=n=>'PBM-'+String(String(n).replace(/\\D/g,'')).padStart(4,'0');const memBadge=(c,s)=>c.memberNo?`<span class=\"badge m-yes\">สมาชิก · ${pbm(c.memberNo)}</span>`", 1)
h = h.replace('function filtered(){', "let GC=null;const gcode=c=>{if(!GC){GC={};[...CU].sort((a,b)=>a.added-b.added||a.id.localeCompare(b.id)).forEach((x,i)=>GC[x.id]='G'+String(i+1).padStart(4,'0'))}return GC[c.id]||c.id};\nfunction filtered(){", 1)
MAG = '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L20 20"/></svg>'
CHEV = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'
assert h.count("<span class=\"go\">${ico('eye')}</span>") == 1
h = h.replace("<span class=\"go\">${ico('eye')}</span>", '<span class="go2">' + MAG + 'ดูโปรไฟล์</span>')
h = h.replace('.fbar2{', '.go2{display:inline-flex;align-items:center;gap:.3rem;color:var(--soft);font-weight:600;font-size:.85rem;white-space:nowrap}.tr:hover .go2{color:var(--purple)}.tr:hover .go2 svg{transform:translateX(3px)}.go2 svg{transition:transform .15s}.fbar2{', 1)
h = h.replace('grid-template-columns:2.4rem 5rem 1.5fr 7.6rem 7.8rem 6.8rem 9.8rem 3rem', 'grid-template-columns:2.4rem 1.7fr 7.6rem 7.8rem 6.8rem 10.5rem 7.2rem')
open(D + 'cust_after.html', 'w').write(h)
print('ok')
