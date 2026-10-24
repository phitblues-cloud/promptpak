# -*- coding: utf-8 -*-
"""หลังบ้านของหน้าจอ v196: ล็อกอินด้วย PIN, ส่งแอปพร้อมข้อมูลจริง, ส่งโมดูลที่ข้อมูลเปลี่ยน"""
import datetime, json, os
import render, overlay, session
from db import rpc, DbError

REFRESH = ['home', 'book', 'linechat', 'hk', 'fin', 'cust', 'rep']   # โมดูลที่โหลดใหม่เมื่อมีการจอง/แชทใหม่


def now_bkk():
    if os.environ.get('PP_NOW'):
        return os.environ['PP_NOW']
    t = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    return t.strftime('%Y-%m-%dT%H:%M')


# ---------- แก้หน้าล็อกอินเดิม: แตะบัตรแล้วใส่ PIN ----------
PIN_JS = r"""
async function enter(k,pin){
  const a=ACC[k];
  if(pin===undefined){
    box.innerHTML=`${saved.length?'<button class="lnk" id="bk" style="margin-bottom:.8rem">‹ กลับไปบัญชีล่าสุด</button>':''}
    <div class="${a.cls}" style="display:flex;align-items:center;gap:.9rem;margin-bottom:1.1rem"><span class="av" style="margin:0">${a.ini}</span>
      <div><h2 style="margin:0">${esc(a.name)}</h2><span class="role">${a.role}</span></div></div>
    <form id="pf" novalidate>
      <label class="field"><span>PIN</span><input type="password" id="pin" inputmode="numeric" autocomplete="current-password" maxlength="12"></label>
      <div class="err" id="er" hidden></div>
      <button class="cut full" type="submit">เข้าสู่ระบบ</button>
    </form>`;
    if(document.getElementById('bk'))document.getElementById('bk').onclick=cards;
    const pi=document.getElementById('pin');setTimeout(()=>pi.focus(),50);
    document.getElementById('pf').onsubmit=e=>{e.preventDefault();if(!pi.value.trim()){const er=document.getElementById('er');er.textContent='กรุณาใส่ PIN';er.hidden=false;return}enter(k,pi.value.trim())};
    return;
  }
  box.innerHTML=`<div class="loading"><div class="${a.cls}"><div class="av" style="margin:0 auto;width:84px;height:84px">${a.ini}</div></div>
   <h2 style="margin-top:1rem">กำลังเข้าสู่ระบบ</h2><p class="sub">${esc(a.name)}</p><div class="spin" aria-hidden="true"></div></div>`;
  const top=window.parent!==window?window.parent:window;
  let r,msg='PIN ไม่ถูกต้อง';
  try{r=await fetch(top.location.origin+'/api/app?part=pin',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({role:k,pin})});
    if(r.status===429)msg='ใส่ PIN ผิดหลายครั้ง กรุณารอ 15 นาที';
    else if(r.status!==401&&!r.ok){let t='';try{t=(await r.json()).error||''}catch(_){}msg='ระบบขัดข้อง (รหัส '+r.status+') '+t}}catch(_){msg='เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง'}
  if(r&&r.ok){top.location.reload();return}
  enter(k);const er=document.getElementById('er');er.textContent=msg;er.hidden=false;
}
"""


def patch_login(post):
    i = post.index('const LOGIN=') + len('const LOGIN=')
    L, end = json.JSONDecoder().raw_decode(post[i:])
    a = L.index('function enter(k){')
    b = L.index("document.getElementById('v1').onclick")
    L = L[:a] + PIN_JS + '\n' + L[b:]
    old = "if(document.getElementById('rem').checked&&!saved.includes(k))saved.push(k);\n    enter(k)};"
    assert old in L, 'login form'
    L = L.replace(old, "if(document.getElementById('rem').checked&&!saved.includes(k))saved.push(k);\n    enter(k,p.value)};")
    L = L.replace('<span>รหัสผ่าน</span>', '<span>รหัสผ่าน (PIN)</span>')
    return post[:i] + json.dumps(L, ensure_ascii=False).replace('</', '<\\/') + post[i + end:]


# ---------- สคริปต์เสริมในแอป: เข้าสู่ระบบอัตโนมัติ + โหลดข้อมูลใหม่เมื่อมีการเปลี่ยนแปลง ----------
def app_script(role, stamp):
    return """
/* PROMPT PAK ระบบจริง */
(function(){
 const PP=%s;
 applyRole(PP.role,PP.name);
 window.showLogin=async function(){try{await fetch('/api/app?part=logout',{method:'POST'})}catch(_){}location.reload()};
 let ST=PP.stamp,busy=false;
 async function poll(){if(busy||document.hidden)return;busy=true;
  try{const r=await fetch('/api/app?part=mods&since='+encodeURIComponent(ST),{cache:'no-store'});
   if(r.status===401){location.reload();return}
   const d=await r.json();
   if(d.mods){ST=d.stamp;Object.assign(PEND,d.mods)}
   apply()}
  catch(_){}busy=false}
 /* โมดูลที่กำลังเปิดหน้าต่าง/กรอกข้อมูลอยู่ ยังไม่โหลดใหม่ รอจนปิดหน้าต่างก่อน (กันงานที่ทำค้างหาย) */
 const PEND={},LAST={};
 function busyFrame(k){const f=FR[k];if(!f)return false;
  try{const d=f.contentDocument;if(!d)return false;
   if(d.querySelector('[id$="scrim"].open,dialog[open]'))return true;
   const a=d.activeElement;if(a&&/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName))return true;
   return Date.now()-(LAST[k]||0)<8000}catch(_){return false}}
 function apply(){Object.keys(PEND).forEach(k=>{if(busyFrame(k))return;const h=PEND[k];delete PEND[k];MODS[k]=h;
   if(FR[k]){FR[k].srcdoc=h;FR[k].classList.remove('ovl')}})}
 Object.keys(FR).forEach(k=>{const f=FR[k];if(!f)return;const hook=()=>{try{const d=f.contentDocument;
   ['pointerdown','keydown','input'].forEach(e=>d.addEventListener(e,()=>{LAST[k]=Date.now()},true))}catch(_){}};
   f.addEventListener('load',hook);hook()});
 window.addEventListener('message',e=>{const d=e.data||{};
   if(d.pbr==='pp-saved')setTimeout(()=>{busy=false;poll()},400);
   if(d.pbr==='pp-reload'){ST='x';setTimeout(()=>{busy=false;poll()},400)}});
 setInterval(poll,10000);setInterval(apply,2000);document.addEventListener('visibilitychange',poll);
})();
""" % json.dumps({'role': role, 'name': session.NAMES[role], 'stamp': stamp}, ensure_ascii=False)


AI_HOOK = "if(window.__AISUM&&window.__AISUM.length){sumR.length=0;window.__AISUM.forEach(x=>sumR.push(x))}\n  const TR={bad:0,opp:1,info:2};"
AI_LOAD = ("<script>(function(){try{fetch(top.location.origin+'/api/summary',{method:'POST',credentials:'same-origin'})"
           ".then(r=>r.ok?r.json():null).then(d=>{if(d&&d.items&&d.items.length){window.__AISUM=d.items;try{ovDash()}catch(e){}}})"
           ".catch(()=>{})}catch(e){}})();</script>")


def patch_crm_ai(h):
    """กล่อง "สถานการณ์ลูกค้าตอนนี้" ในภาพรวมลูกค้า: แทนข้อความตัวอย่างด้วยผล AI จริง (หน้าตาเดิม)"""
    i = h.index('const OVP=') + len('const OVP=')
    O, end = json.JSONDecoder().raw_decode(h[i:])
    assert O.count('const TR={bad:0,opp:1,info:2};') == 1, 'crm-ai hook'
    O = O.replace('const TR={bad:0,opp:1,info:2};', AI_HOOK, 1)
    k = O.rindex('</body>')
    O = O[:k] + AI_LOAD + O[k:]
    return h[:i] + json.dumps(O, ensure_ascii=False).replace('</', '<\\/') + h[i + end:]


def _daily():
    """กฎวันจริง: การจองที่เลยวันเข้าพักแล้วไม่เช็คอิน -> ยกเลิก (ข้ามได้ถ้ายังไม่ได้รัน 05_noshow.sql)"""
    try:
        rpc('pp_noshow')
    except Exception:
        pass


def _build(now):
    _daily()
    export = rpc('pp_export')
    return overlay.build(render.base_mock(), export, now), export['stamp']


def page(role):
    pre, M, post = render.split_shell(render.base_html())
    post = patch_login(post)
    if not role:   # ยังไม่เข้าสู่ระบบ: ส่งเฉพาะหน้าล็อกอิน ไม่มีข้อมูลลูกค้า
        return pre + '{}' + post
    now = now_bkk()
    mock, stamp = _build(now)
    M = render.modules(mock, now)
    M['crm'] = patch_crm_ai(M['crm'])
    k = post.rindex('</script>')
    post = post[:k] + app_script(role, stamp) + post[k:]
    return pre + json.dumps(M, ensure_ascii=False).replace('</', '<\\/') + post


def handle(method, query, cookie_header, body, ip):
    """คืน (status, headers dict, body str)"""
    part = (query.get('part') or [''])[0]
    role = session.from_cookie_header(cookie_header)
    J = {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'}
    try:
        if method == 'POST' and part == 'pin':
            data = json.loads(body or '{}')
            r = data.get('role') if data.get('role') in session.NAMES else 'staff'
            if rpc('pp_pin_locked', {'p_ip': ip}):
                return 429, J, json.dumps({'error': 'locked'})
            if session.check_pin(r, data.get('pin', '')):
                return 200, dict(J, **{'Set-Cookie': session.cookie_header(session.sign(r), session.TTL)}), '{"ok":true}'
            rpc('pp_pin_fail', {'p_ip': ip})
            return 401, J, json.dumps({'error': 'bad pin'})
        if part == 'diag':   # ตรวจส่วนล็อกอิน (ไม่เปิดเผยค่าลับ)
            out = {'python': 'ok'}
            try:
                out['db_pin_lock'] = 'ok (ล็อกอยู่)' if rpc('pp_pin_locked', {'p_ip': ip}) else 'ok (ไม่ล็อก)'
            except Exception as e:
                out['db_pin_lock'] = 'ผิดพลาด: ' + str(e)[:200]
            try:
                session.sign('owner'); out['app_secret'] = 'ok'
            except Exception as e:
                out['app_secret'] = 'ผิดพลาด: ' + str(e)
            out['owner_pin_set'] = bool(session.norm_pin(os.environ.get('OWNER_PIN')))
            return 200, J, json.dumps(out, ensure_ascii=False)
        if method == 'POST' and part == 'logout':
            return 200, dict(J, **{'Set-Cookie': session.cookie_header('', 0)}), '{"ok":true}'
        if method == 'POST' and part == 'act':   # ปุ่มในหน้าจอ -> บันทึกลงฐานข้อมูล
            if not role:
                return 401, J, json.dumps({'error': 'ต้องเข้าสู่ระบบใหม่'}, ensure_ascii=False)
            data = json.loads(body or '{}')
            if not isinstance(data, dict) or not data.get('k'):
                return 400, J, json.dumps({'error': 'ข้อมูลไม่ครบ'}, ensure_ascii=False)
            out = rpc('pp_act', {'p': data, 'p_role': role})
            return 200, J, json.dumps(out, ensure_ascii=False)
        if part == 'mods':
            if not role:
                return 401, J, '{}'
            since = (query.get('since') or [''])[0]
            _daily()
            stamp = rpc('pp_stamp')
            if stamp == since:
                return 200, J, json.dumps({'stamp': stamp})
            now = now_bkk()
            mock, stamp = _build(now)
            return 200, J, json.dumps({'stamp': stamp, 'mods': render.modules(mock, now, REFRESH)}, ensure_ascii=False)
        html = page(role)
        return 200, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}, html
    except DbError as e:
        return 500, J, json.dumps({'error': 'ฐานข้อมูล: ' + str(e)[:200]}, ensure_ascii=False)
    except Exception as e:
        return 500, J, json.dumps({'error': type(e).__name__ + ': ' + str(e)[:200]}, ensure_ascii=False)
