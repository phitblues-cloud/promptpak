# -*- coding: utf-8 -*-
"""ทำให้ปุ่มหน้าเคาน์เตอร์ในหน้าจอ v196 บันทึกลงฐานข้อมูลจริง (หน้าตาเดิมทุกอย่าง)

แต่ละปุ่มยังทำงานในหน้าจอเหมือนเดิม และเรียก ppSave(ชนิด, ข้อมูล) เพิ่ม -> POST /api/app?part=act -> pp_act()
ถ้าบันทึกไม่สำเร็จ จะแจ้งเตือนและโหลดหน้าจอใหม่จากฐานข้อมูล (ไม่ให้หน้าจอแสดงสิ่งที่ไม่ได้บันทึก)
"""

HELPER = r"""<script>
/* PROMPT PAK: บันทึกลงฐานข้อมูลจริง */
window.__ppOps=[];
function ppDay(n){return new Date(n*864e5).toISOString().slice(0,10)}
function ppIso(o){const d=new Date();d.setDate(d.getDate()+o);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function ppSave(k,d){
  const body=JSON.stringify(Object.assign({k},d||{}));
  return fetch(top.location.origin+'/api/app?part=act',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body})
   .then(r=>r.json().catch(()=>({})).then(j=>{if(!r.ok)throw new Error(j.error||('รหัส '+r.status));
     if(k!=='undo'&&j.id)window.__ppOps.push(j.id);try{parent.postMessage({pbr:'pp-saved'},'*')}catch(_){}return j}))
   .catch(e=>{const msg='⚠️ บันทึกไม่สำเร็จ: '+e.message+' · หน้าจอจะโหลดข้อมูลจริงใหม่';
     try{toast(msg)}catch(_){console.error(msg)}
     setTimeout(()=>{try{parent.postMessage({pbr:'pp-reload'},'*')}catch(_){}},2500)});
}
function ppUndoAll(){const ids=window.__ppOps.splice(0).reverse();ids.reduce((p,id)=>p.then(()=>ppSave('undo',{id})),Promise.resolve())}
</script>"""

HOME = [
    # มัดจำ (รับ)
    ("on('mDepC',()=>{snap(b); b.dep='held'; b.depM='cash';",
     "on('mDepC',()=>{snap(b); ppSave('dep_in',{no:b.bk,m:'cash',amt:DEP}); b.dep='held'; b.depM='cash';"),
    ("on('mDepT',()=>{snap(b); b.dep='held'; b.depM='transfer';",
     "on('mDepT',()=>{snap(b); ppSave('dep_in',{no:b.bk,m:'transfer',amt:DEP}); b.dep='held'; b.depM='transfer';"),
    # ตั้งเครดิตบริษัท
    ("b.credit={days,po:(b.org&&b.org.po)||''};if(wasPre0)b.stage='key';",
     "ppSave('credit',{no:b.bk,days}); b.credit={days,po:(b.org&&b.org.po)||''};if(wasPre0)b.stage='key';"),
    # รับชำระค่าพักต่อ
    ("b.pm=(b.pm||[]).concat([{m,amt:due,slip,at,tag:'ext'}]); b.extraDue=0;",
     "ppSave('pay',{no:b.bk,m,ext_amt:due}); b.pm=(b.pm||[]).concat([{m,amt:due,slip,at,tag:'ext'}]); b.extraDue=0;"),
    # รับชำระเงิน (ค่าห้อง / มัดจำ / ค่าพักต่อค้าง)
    ("const wasPre=['arrive','paying'].includes(b.stage);",
     "ppSave('pay',{no:b.bk,m,room_amt:has('room')?total:0,dep:has('dep')?DEP:0,ext_amt:has('ext')?(b.extraDue||0):0});\n"
     "      const wasPre=['arrive','paying'].includes(b.stage);"),
    # เช็คอินเสร็จ (ส่งคีย์การ์ด)
    ("$('fDone').onclick=()=>{ snap(b); b.stage='stay';",
     "$('fDone').onclick=()=>{ snap(b); ppSave('checkin',{no:b.bk}); b.stage='stay';"),
    # เช็คเอาท์ (ขั้นตอนปกติ)
    ("$('fDone').onclick=()=>{ snap(b); b.stage='outdone';",
     "$('fDone').onclick=()=>{ snap(b); ppSave('checkout',{no:b.bk}); b.stage='outdone';"),
    # ยกเลิกการจอง
    ("$('cGo').onclick=()=>{ snap(b); b.cancelled=true;",
     "$('cGo').onclick=()=>{ snap(b); ppSave('cancel',{no:b.bk,refund:ref,why:x.reason==='อื่นๆ'?(x.why||'อื่นๆ'):x.reason}); b.cancelled=true;"),
    # จองพักต่อ (ห้องเดิม / ย้ายห้อง)
    ("const go=paidNow=>{\n      snap(b);",
     "const go=paidNow=>{\n      snap(b); ppSave('extend',{no:b.bk,move_now:plan[0].room!==b.id&&plan[0].from===0,"
     "segs:plan.map(s=>({room:s.room,from:ppIso(s.from),n:s.n,rate:s.rate}))});"),
    # เช็คเอาท์ (ก่อนกำหนด / ตามกำหนด)
    ("x.force=false; snap(b); if(mode==='early'){",
     "x.force=false; snap(b); if(mode!=='post')ppSave('checkout',mode==='early'?{no:b.bk,nights:paidN,refund:b.paid?refRoom:0}:{no:b.bk}); if(mode==='early'){"),
    # คืนเงินประกัน
    ("A.dfull=()=>{c.depDone=true;",
     "A.dfull=()=>{ppSave('dep_out',{no:b.bk,amt:DEP,ded:0,m:x.rm||b.depM||'cash'});c.depDone=true;"),
    ("A.ddo=()=>{const ded=x.dm==='full'?0:x.dm==='none'?DEP:Math.max(0,Math.min(DEP,+x.amt||0));",
     "A.ddo=()=>{const ded=x.dm==='full'?0:x.dm==='none'?DEP:Math.max(0,Math.min(DEP,+x.amt||0));"
     "ppSave('dep_out',{no:b.bk,amt:DEP-ded,ded,m:x.rm||b.depM||'cash'});"),
    # ย้อนกลับ = ยกเลิกสิ่งที่บันทึกไปในขั้นตอนนั้น
    ("if(!lastSnap) return; const b=find(lastSnap.id);", "if(!lastSnap) return; ppUndoAll(); const b=find(lastSnap.id);"),
    ("function snap(b){ if(!lastSnap||lastSnap.id!==b.id||lastSnap.keep!==true){ lastSnap=",
     "function snap(b){ if(!lastSnap||lastSnap.id!==b.id||lastSnap.keep!==true){ window.__ppOps=[]; lastSnap="),
    ("if(step==='pay' && b.stage==='paying' && !(lastSnap&&lastSnap.id===id)) lastSnap=",
     "if(step==='pay' && b.stage==='paying' && !(lastSnap&&lastSnap.id===id)) window.__ppOps=[], lastSnap="),
    # ห้องที่เช็คเอาท์วันนี้แต่ยังไม่คืนเงินประกัน
    ("co:b.stage==='outdone'?{key:true,room:'ok',reason:'',note:'',depDone:true,ded:0,dedWhy:''}:null",
     "co:b.stage==='outdone'?{key:true,room:'ok',reason:'',note:'',depDone:(e.dep||'held')!=='held',ded:0,dedWhy:''}:null"),
]

HOME_FIX = [
    # บั๊กเดิมของต้นแบบ: ตัวแปร sum ทับฟังก์ชัน sum ทำให้ปุ่มเช็คเอาท์ (ก่อนกำหนด/ปกติ) เปิดหน้าต่างไม่ได้
    ("let sum='', refRoom=0, paidN=b.nights;", "let sumH='', refRoom=0, paidN=b.nights;"),
    ("      sum=`<div class=\"sub\" style=\"margin:.6rem 0 .3rem\">", "      sumH=`<div class=\"sub\" style=\"margin:.6rem 0 .3rem\">"),
    ("${head('out',title)}${sum}${dueBox}", "${head('out',title)}${sumH}${dueBox}"),
    # การจองใหม่จากโมดูลการจองบันทึกในฐานข้อมูลแล้ว: ไม่เพิ่มการ์ดซ้ำ
    ("if(nb.startOff!==0||NBK.has(nb.no))return;", "if(nb.startOff!==0||NBK.has(nb.no)||B.some(x=>x.bk===nb.no))return;"),
]

BOOK = [
    # พนักงานเพิ่มการจองเอง
    ("      try{\n        const billEntries=B.filter(b=>b.no===no)",
     "      ppSave('book',{guest:F.mode==='co'?F.co.name.trim():F.name.trim(),phone:F.phone.trim(),company:F.mode==='co'?F.co.name.trim():'',"
     "check_in:ppDay(F.start),check_out:ppDay(F.start+F.nights),rooms:B.filter(b=>b.no===no).map(b=>({room:b.room,rate:b.rate,guest:b.guest})),"
     "channel:F.ch,note:F.note.trim(),paid:F.pay==='now',m:F.payM}).then(j=>{if(j&&j.nos){"
     "B.filter(b=>b.no===no).forEach((b,i)=>{if(j.nos[i])b.no=j.nos[i]});try{renderAll()}catch(_){}}});\n"
     "      try{\n        const billEntries=B.filter(b=>b.no===no)"),
    # เปิด/ปิดห้อง
    ("if(a=t.closest('[data-troom]')){const r=roomOf(a.dataset.troom);r.open=!r.open;",
     "if(a=t.closest('[data-troom]')){const r=roomOf(a.dataset.troom);r.open=!r.open;ppSave('room',{room:r.code,open:r.open});"),
    # โหลดใหม่จากฐานข้อมูลแล้ว: ล้างรายการจองใหม่ที่ค้างอยู่ในตัวกลาง (กันการ์ดซ้ำหน้าแรก)
    ("pubOcc();\n", "pubOcc();\ntry{pub('newbk',{list:[]})}catch(_){}\n"),
    ("if(ed){Object.assign(ed,{zone:z,type:t,rate:R.rate,max:R.max,open:R.open});",
     "if(ed){if(ed.open!==R.open)ppSave('room',{room:c,open:R.open});Object.assign(ed,{zone:z,type:t,rate:R.rate,max:R.max,open:R.open});"),
]


def _patch(h, pairs, name):
    for old, new in pairs:
        assert h.count(old) == 1, (name, h.count(old), old[:70])
        h = h.replace(old, new)
    i = h.index('<script>')
    return h[:i] + HELPER + h[i:]


def apply(M):
    if 'home' in M:
        M['home'] = _patch(M['home'], HOME + HOME_FIX, 'home')
    if 'book' in M:
        M['book'] = _patch(M['book'], BOOK, 'book')
    return M
