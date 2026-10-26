# -*- coding: utf-8 -*-
"""หลังบ้านของหน้าจอ v196: ล็อกอินด้วย PIN, ส่งแอปพร้อมข้อมูลจริง, ส่งโมดูลที่ข้อมูลเปลี่ยน"""
import datetime, json, os, re, urllib.request, urllib.error
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
   if(d.querySelector('[id$="scrim"].open,dialog[open],[data-keep]'))return true;
   const a=d.activeElement;if(a&&/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName))return true;
   return Date.now()-(LAST[k]||0)<8000}catch(_){return false}}
 function apply(){Object.keys(PEND).forEach(k=>{if(busyFrame(k))return;const h=PEND[k];delete PEND[k];MODS[k]=h;
   if(FR[k]){FR[k].srcdoc=h;FR[k].classList.remove('ovl')}})}
 Object.keys(FR).forEach(k=>{const f=FR[k];if(!f)return;const hook=()=>{try{const d=f.contentDocument;
   ['pointerdown','keydown','input'].forEach(e=>d.addEventListener(e,()=>{LAST[k]=Date.now()},true))}catch(_){}};
   f.addEventListener('load',hook);hook()});
 window.addEventListener('message',e=>{const d=e.data||{};
   if(d.pbr==='custpage'&&FR.cust){FR.cust.classList.add('ovl');FR.cust.contentWindow.postMessage(d,'*')}
   if(d.pbr==='custpageclosed'&&FR.cust){FR.cust.classList.remove('ovl');if(d.miss)try{FR.book.contentWindow.postMessage({pbr:'toast',msg:'ไม่พบข้อมูลลูกค้าคนนี้ในเมนูลูกค้า'},'*')}catch(_){}}
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


def upload_media(raw, ctype, ext):
    """เก็บรูป/ไฟล์ไว้ที่ Supabase Storage (ถัง chat · สาธารณะ เพราะ LINE ต้องดึงจากลิงก์) คืนลิงก์"""
    url = (os.environ.get('SUPABASE_URL') or '').strip().rstrip('/')
    key = (os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or '').strip()
    if os.environ.get('LOCAL_PG') or not url or not key:   # เครื่องทดสอบ
        import base64
        return 'data:%s;base64,%s' % (ctype, base64.b64encode(raw).decode()) if len(raw) < 400000 else None
    import secrets
    path = '%s/%s.%s' % (datetime.date.today().isoformat(), secrets.token_hex(12), ext)
    headers = {'apikey': key, 'Content-Type': ctype, 'x-upsert': 'true'}
    if not key.startswith('sb_'):
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(url + '/storage/v1/object/chat/' + path, data=raw, headers=headers, method='POST')
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except urllib.error.HTTPError as e:
        raise ValueError('อัปโหลดไฟล์ไม่สำเร็จ (%s) · รัน supabase/11_media.sql แล้วหรือยัง' % e.code)
    return url + '/storage/v1/object/public/chat/' + path


def media_msgs(media, text):
    """แปลงสื่อจากหน้าจอ → ข้อความ LINE + ข้อมูลแนบที่เก็บในแชท"""
    import base64
    t = media.get('type')
    if t == 'sticker':
        pkg, sid = str(media.get('pkg') or ''), str(media.get('sid') or '')
        if not (pkg.isdigit() and sid.isdigit()):
            raise ValueError('สติกเกอร์ไม่ถูกต้อง')
        return [{'type': 'sticker', 'packageId': pkg, 'stickerId': sid}], {'type': 'sticker', 'pkg': pkg, 'sid': sid}
    d = str(media.get('data') or '')
    m = re.match(r'^data:([\w/+.-]+);base64,(.+)$', d, re.S)
    if not m:
        raise ValueError('ไฟล์ไม่ถูกต้อง')
    ctype, raw = m.group(1), base64.b64decode(m.group(2))
    if len(raw) > 3 * 1048576:
        raise ValueError('ไฟล์ใหญ่เกิน 3 MB')
    if t == 'image':
        if ctype not in ('image/jpeg', 'image/png'):
            raise ValueError('รูปต้องเป็น JPG หรือ PNG')
        u = upload_media(raw, ctype, 'jpg' if ctype == 'image/jpeg' else 'png')
        if not u:
            raise ValueError('เก็บรูปไม่สำเร็จ')
        return [{'type': 'image', 'originalContentUrl': u, 'previewImageUrl': u}], {'type': 'image', 'url': u}
    if t == 'file':
        name = re.sub(r'[^\w.\- ก-๙]', '_', str(media.get('name') or 'file'))[:80]
        ext = (name.rsplit('.', 1)[-1] if '.' in name else 'bin')[:8]
        u = upload_media(raw, ctype or 'application/octet-stream', ext)
        if not u:
            raise ValueError('เก็บไฟล์ไม่สำเร็จ')
        # LINE ไม่ให้บัญชีทางการส่งไฟล์โดยตรง → ส่งเป็นลิงก์ให้ลูกค้ากดเปิด
        return [{'type': 'text', 'text': '📎 %s\n%s' % (name, u)}], {'type': 'file', 'url': u, 'name': name, 'size': len(raw)}
    raise ValueError('ไม่รู้จักชนิดไฟล์')


def line_push(to, text):
    """ส่งข้อความหาลูกค้าทาง LINE (push · นับโควตาข้อความรายเดือนของ LINE OA) คืนข้อความผิดพลาด หรือ None ถ้าสำเร็จ
    text = ข้อความ หรือรายการข้อความ LINE (รูป/สติกเกอร์)"""
    msgs = text if isinstance(text, list) else [{'type': 'text', 'text': text}]
    if os.environ.get('LOCAL_DEV'):   # เครื่องทดสอบ: ไม่ส่งจริง
        LINE_OUTBOX.append({'to': to, 'messages': msgs})
        return None
    token = (os.environ.get('LINE_CHANNEL_ACCESS_TOKEN') or '').strip()
    if not token:
        return 'ยังไม่ได้ตั้งค่า LINE_CHANNEL_ACCESS_TOKEN'
    req = urllib.request.Request('https://api.line.me/v2/bot/message/push', method='POST',
                                 data=json.dumps({'to': to, 'messages': msgs}).encode(),
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return None
    except urllib.error.HTTPError as e:
        msg = e.read().decode('utf-8', 'replace')[:200]
        if e.code == 429:
            return 'โควตาข้อความ LINE เดือนนี้หมดหรือส่งถี่เกินไป'
        return f'{e.code} {msg}'
    except Exception as e:
        return type(e).__name__


LINE_OUTBOX = []

OCR_PROMPT = (
    'ภาพนี้คือบัตรประจำตัวประชาชนไทยหรือหนังสือเดินทาง ที่พนักงานโรงแรมถ่ายเพื่อลงทะเบียนผู้พัก (ลูกค้ายินยอมแล้ว) '
    'อ่านข้อมูลแล้วตอบเป็น JSON อย่างเดียว ไม่มีข้อความอื่น ตามรูปแบบนี้: '
    '{"doc_type":"id หรือ passport","doc_no":"เลขบัตร 13 หลัก หรือเลขหนังสือเดินทาง ไม่มีขีด","title":"นาย/นาง/นางสาว/Mr./Ms. ฯลฯ",'
    '"first_name":"ชื่อภาษาไทย (ถ้าไม่มีใช้ภาษาอังกฤษ)","last_name":"นามสกุล","gender":"ชาย หรือ หญิง หรือ ว่าง",'
    '"birth_date":"YYYY-MM-DD เป็น ค.ศ. (แปลง พ.ศ. ลบ 543)","address":"ที่อยู่ตามบัตร ไม่รวมจังหวัด","province":"จังหวัด ไม่มีคำว่า จ."} '
    'ช่องที่อ่านไม่ออกหรือไม่มีให้ใส่ "" ห้ามเดา · ถ้าไม่ใช่บัตรหรือหนังสือเดินทาง ให้ตอบ {"error":"ไม่ใช่ภาพบัตร"}')


def id_ocr(img):
    """อ่านข้อมูลจากภาพบัตรด้วย Claude (ภาพไม่ถูกเก็บที่ผู้ให้บริการ AI นอกเหนือการประมวลผลคำขอนี้)"""
    mt = img.split(';', 1)[0][5:] if img.startswith('data:') else ''
    if mt not in ('image/jpeg', 'image/png', 'image/webp') or ',' not in img:
        return {'error': 'ไฟล์ภาพไม่ถูกต้อง'}
    if os.environ.get('PP_FAKE_OCR'):   # ทดสอบในเครื่อง
        return _ocr_clean(json.loads(os.environ['PP_FAKE_OCR']))
    key = (os.environ.get('ANTHROPIC_API_KEY') or '').strip()
    if not key:
        return {'error': 'ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY'}
    model = (os.environ.get('ANTHROPIC_MODEL') or '').strip() or 'claude-sonnet-5-5'
    body = {'model': model, 'max_tokens': 600, 'messages': [{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': mt, 'data': img.split(',', 1)[1]}},
        {'type': 'text', 'text': OCR_PROMPT}]}]}
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', method='POST', data=json.dumps(body).encode(),
                                 headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    try:
        out = json.loads(urllib.request.urlopen(req, timeout=25).read())
        txt = ''.join(c.get('text', '') for c in out.get('content', []) if c.get('type') == 'text')
        i, j = txt.find('{'), txt.rfind('}')
        d = json.loads(txt[i:j + 1])
    except Exception as e:
        return {'error': 'อ่านบัตรไม่สำเร็จ (' + type(e).__name__ + ')'}
    return _ocr_clean(d)


def _ocr_clean(d):
    if d.get('error'):
        return {'error': str(d['error'])[:100]}
    r = {k: str(d.get(k) or '').strip()[:200] for k in ('doc_type', 'doc_no', 'title', 'first_name', 'last_name', 'gender', 'birth_date', 'address', 'province')}
    r['doc_type'] = 'passport' if r['doc_type'] == 'passport' else 'id'
    r['doc_no'] = ''.join(ch for ch in r['doc_no'] if ch.isalnum()).upper()
    if r['gender'] not in ('ชาย', 'หญิง'):
        r['gender'] = 'ชาย' if r['title'] in ('นาย', 'Mr.', 'MR.', 'Mr', 'ด.ช.') else ('หญิง' if r['title'] in ('นาง', 'นางสาว', 'น.ส.', 'Mrs.', 'Ms.', 'Miss', 'ด.ญ.') else '')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', r['birth_date']):
        r['birth_date'] = ''
    r['id_ok'] = r['doc_type'] != 'id' or thai_id_ok(r['doc_no'])
    return r


def _daily():
    """กฎวันจริง: การจองที่เลยวันเข้าพักแล้วไม่เช็คอิน -> ยกเลิก (ข้ามได้ถ้ายังไม่ได้รัน 05_noshow.sql)"""
    try:
        rpc('pp_noshow')
    except Exception:
        pass


def _build(now, role='owner'):
    _daily()
    export = rpc('pp_export')
    try:   # สถานะแชท (ข้ามได้ถ้ายังไม่ได้รัน 07_chat.sql)
        export['chat_state'] = rpc('pp_chat_state') or {}
    except Exception:
        export['chat_state'] = {}
    try:   # ข้อมูลลูกค้าที่แก้ในโมดูลลูกค้า (ข้ามได้ถ้ายังไม่ได้รัน 08_cust.sql)
        export['cust_state'] = rpc('pp_cust_state') or {}
    except Exception:
        export['cust_state'] = {}
    try:   # แม่บ้าน/งานทำความสะอาด (ข้ามได้ถ้ายังไม่ได้รัน 12_hk.sql)
        export['hk_state'] = rpc('pp_hk_state')
    except Exception:
        export['hk_state'] = None
    try:   # บริษัทที่เพิ่มใหม่ (ข้ามได้ถ้ายังไม่ได้รัน 10_company.sql)
        export['comp_state'] = rpc('pp_comp_state') or {}
    except Exception:
        export['comp_state'] = {}
    try:   # เลขบัตร/หนังสือเดินทาง (ข้ามได้ถ้ายังไม่ได้รัน 09_idcard.sql)
        export['cust_ids'] = rpc('pp_cust_ids') or {}
    except Exception:
        export['cust_ids'] = {}
    m = overlay.build(render.base_mock(), export, now)
    m['_role'] = role   # พนักงานเห็นเลขบัตรแบบปิดบางส่วน
    _purge_ids(m, now)
    return m, export['stamp']


def _purge_ids(m, now):
    """ลบภาพบัตรที่เก็บเกิน 1 ปี ของลูกค้าที่ไม่ได้เข้าพักภายใน 1 ปี"""
    if not any(v.get('img') for v in (m.get('cust_ids') or {}).values()):
        return
    cut = (datetime.date.fromisoformat(now[:10]) - datetime.timedelta(days=365)).isoformat()
    keep = sorted({b['guest_id'] for b in m['bookings']
                   if b['booking_status'] not in ('ยกเลิก', 'ไม่มาตามนัด') and b['checkout_date'] >= cut})
    try:
        rpc('pp_id_purge', {'p_keep': keep})
    except Exception:
        pass


def thai_id_ok(d):
    if len(d) != 13 or not d.isdigit():
        return False
    s = sum(int(d[i]) * (13 - i) for i in range(12))
    return (11 - s % 11) % 10 == int(d[12])


def page(role):
    pre, M, post = render.split_shell(render.base_html())
    post = patch_login(post)
    if not role:   # ยังไม่เข้าสู่ระบบ: ส่งเฉพาะหน้าล็อกอิน ไม่มีข้อมูลลูกค้า
        return pre + '{}' + post
    now = now_bkk()
    mock, stamp = _build(now, role)
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
            if data['k'] in ('checkout', 'checkout2'):   # เช็คเอาท์ → งานทำความสะอาด (มอบหมายแม่บ้านอัตโนมัติ)
                for no in [data.get('no')] + list((out or {}).get('nos') or []):
                    if no:
                        try:
                            rpc('pp_hk', {'p': {'k': 'task_from_booking', 'no': no}, 'p_role': role})
                        except Exception:
                            pass
            return 200, J, json.dumps(out, ensure_ascii=False)
        if method == 'POST' and part == 'hk':   # แม่บ้าน/งานทำความสะอาด
            if not role:
                return 401, J, json.dumps({'error': 'ต้องเข้าสู่ระบบใหม่'}, ensure_ascii=False)
            data = json.loads(body or '{}')
            if not isinstance(data, dict) or not data.get('k'):
                return 400, J, json.dumps({'error': 'ข้อมูลไม่ครบ'}, ensure_ascii=False)
            return 200, J, json.dumps(rpc('pp_hk', {'p': data, 'p_role': role}), ensure_ascii=False)
        if method == 'POST' and part == 'chat':   # ปุ่มในหน้าแชท LINE -> บันทึกจริง (และส่งเข้า LINE ถ้าเป็นแชทจริง)
            if not role:
                return 401, J, json.dumps({'error': 'ต้องเข้าสู่ระบบใหม่'}, ensure_ascii=False)
            data = json.loads(body or '{}')
            if not isinstance(data, dict) or not data.get('k') or not data.get('key'):
                return 400, J, json.dumps({'error': 'ข้อมูลไม่ครบ'}, ensure_ascii=False)
            line = None
            if data['k'] == 'send':
                text = str(data.get('body') or '').strip()[:4900]
                if not text:
                    return 400, J, json.dumps({'error': 'ข้อความว่าง'}, ensure_ascii=False)
                data['body'] = text
                media = data.pop('media', None)
                msgs = [{'type': 'text', 'text': text}]
                if isinstance(media, dict):   # รูป / สติกเกอร์ / ไฟล์
                    try:
                        msgs, data['meta'] = media_msgs(media, text)
                    except ValueError as e:
                        return 400, J, json.dumps({'error': str(e)}, ensure_ascii=False)
                to = rpc('pp_chat_target', {'p_key': str(data['key'])})
                if to:
                    err = line_push(to, msgs)
                    if err:
                        return 502, J, json.dumps({'error': 'ส่งเข้า LINE ไม่สำเร็จ: ' + err}, ensure_ascii=False)
                    line = 'sent'
                else:
                    line = 'sample'
                data['line'] = line
            rpc('pp_chat', {'p': data, 'p_role': role})
            return 200, J, json.dumps({'ok': True, 'line': line})
        if method == 'POST' and part == 'cust':   # ปุ่มในโมดูลลูกค้าและสมาชิก -> บันทึกจริง
            if not role:
                return 401, J, json.dumps({'error': 'ต้องเข้าสู่ระบบใหม่'}, ensure_ascii=False)
            data = json.loads(body or '{}')
            if not isinstance(data, dict) or not data.get('k') or not data.get('gid'):
                return 400, J, json.dumps({'error': 'ข้อมูลไม่ครบ'}, ensure_ascii=False)
            if data['k'] == 'comp':   # เพิ่ม/แก้ไขข้อมูลบริษัท (gid = รหัสบริษัท)
                d = data.get('data') or {}
                if 'tax' in d:
                    tax = ''.join(ch for ch in str(d.get('tax', '')) if ch.isdigit())
                    if tax and not thai_id_ok(tax):
                        return 400, J, json.dumps({'error': 'เลขผู้เสียภาษีไม่ถูกต้อง (ตรวจหลักสุดท้ายไม่ผ่าน)'}, ensure_ascii=False)
                    d['tax'] = tax
                return 200, J, json.dumps(rpc('pp_comp', {'p': {'cid': data['gid'], 'data': d}, 'p_role': role}), ensure_ascii=False)
            if data['k'] == 'idcard':   # เลขบัตร/หนังสือเดินทาง + ภาพบัตร (เมื่อยินยอม)
                if data.get('doc_type', 'id') == 'id' and not thai_id_ok(''.join(ch for ch in str(data.get('doc_no', '')) if ch.isdigit())):
                    return 400, J, json.dumps({'error': 'เลขบัตรประชาชนไม่ถูกต้อง (ตรวจหลักสุดท้ายไม่ผ่าน)'}, ensure_ascii=False)
                if role != 'owner' and 'img' in data and not data.get('img'):
                    data.pop('img')   # ลบภาพบัตรได้เฉพาะเจ้าของ
                return 200, J, json.dumps(rpc('pp_cust_id', {'p': data, 'p_role': role}), ensure_ascii=False)
            out = rpc('pp_cust', {'p': data, 'p_role': role})
            return 200, J, json.dumps(out, ensure_ascii=False)
        if method == 'POST' and part == 'idocr':   # อ่านข้อมูลจากภาพบัตร (ลูกค้ายินยอมแล้ว)
            if not role:
                return 401, J, json.dumps({'error': 'ต้องเข้าสู่ระบบใหม่'}, ensure_ascii=False)
            img = (json.loads(body or '{}') or {}).get('img') or ''
            if len(img) > 700000:
                return 400, J, json.dumps({'error': 'ภาพใหญ่เกินไป'}, ensure_ascii=False)
            return 200, J, json.dumps(id_ocr(img), ensure_ascii=False)
        if part == 'idimg':   # ดูภาพบัตร: เฉพาะเจ้าของ
            if role != 'owner':
                return 403, J, json.dumps({'error': 'เฉพาะเจ้าของเท่านั้น'}, ensure_ascii=False)
            gid = (query.get('gid') or [''])[0]
            return 200, J, json.dumps({'img': rpc('pp_cust_id_img', {'p_gid': gid})})
        if part == 'mods':
            if not role:
                return 401, J, '{}'
            since = (query.get('since') or [''])[0]
            _daily()
            stamp = rpc('pp_stamp')
            if stamp == since:
                return 200, J, json.dumps({'stamp': stamp})
            now = now_bkk()
            mock, stamp = _build(now, role)
            return 200, J, json.dumps({'stamp': stamp, 'mods': render.modules(mock, now, REFRESH)}, ensure_ascii=False)
        html = page(role)
        return 200, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}, html
    except DbError as e:
        return 500, J, json.dumps({'error': 'ฐานข้อมูล: ' + str(e)[:200]}, ensure_ascii=False)
    except Exception as e:
        return 500, J, json.dumps({'error': type(e).__name__ + ': ' + str(e)[:200]}, ensure_ascii=False)
