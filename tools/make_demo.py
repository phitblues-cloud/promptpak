# -*- coding: utf-8 -*-
"""สร้าง public/demo.html = แอปหน้าตาล่าสุด + ข้อมูลสมมติ (ชุดตัวอย่างใน seed) ไม่ต่อฐานข้อมูล/เซิร์ฟเวอร์ ใช้สแกน QR ให้คนทดลองกด
ใช้: LOCAL_PG=postgresql://postgres@/ppdemo?host=/tmp&port=5433 python3 tools/make_demo.py [2026-10-25T10:00]  (ก่อนรัน: psql ... -f tools/demo_tweak.sql)
(ฐาน ppdemo = รัน supabase/01_schema.sql + 02_seed.sql บนฐานเปล่า)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'renderer'))
os.environ.setdefault('APP_SECRET', 'demo')
now = sys.argv[1] if len(sys.argv) > 1 else '2026-10-25T10:00'
os.environ['PP_NOW'] = now
import web

h = web.page('owner')
# นาฬิกาเสมือน: หยุดเวลาไว้ที่ "now" (วัน/เวลาในทุกหน้าตรงกับข้อมูลตัวอย่าง ไม่ว่าคนสแกนเมื่อไร) แต่เวลายังเดินต่อจากนั้น
import json, render
y, mo, d = int(now[:4]), int(now[5:7]), int(now[8:10]); hh, mi = int(now[11:13]), int(now[14:16])
DATE_OVR = ("<script>(function(){var D=Date,off=0,w=window;for(var i=0;i<6;i++){try{if(w.__VOFF!=null){off=w.__VOFF;break}}catch(e){}"
            "if(w.parent===w)break;w=w.parent}"
            "class VD extends D{constructor(...a){if(a.length===0)super(D.now()+off);else super(...a)}static now(){return D.now()+off}}"
            "window.Date=VD})();</script>")
pre, M, post = render.split_shell(h)
for k in M:
    M[k] = M[k].replace('<head>', '<head>' + DATE_OVR, 1)
pre = pre.replace('<html lang="th">\n<head>', '<html lang="th">\n<head><script>window.__VOFF=new Date(%d,%d,%d,%d,%d,0).getTime()-Date.now();</script>' % (y, mo - 1, d, hh, mi), 1)
h = pre + json.dumps(M, ensure_ascii=False).replace('</', '<\\/') + post
# ปิดการดึงข้อมูลใหม่จากเซิร์ฟเวอร์ (เดโมไม่มีหลังบ้าน)
for a, b in [("async function poll(){if(busy||document.hidden)return;", "async function poll(){return;"),
             ("window.showLogin=async function(){try{await fetch('/api/app?part=logout',{method:'POST'})}catch(_){}location.reload()};", "window.showLogin=function(){location.reload()};")]:
    assert h.count(a) == 1, a[:50]
    h = h.replace(a, b)
SHIM = r"""<meta name="robots" content="noindex"><script>
/* เดโม: ไม่มีหลังบ้านจริง · คำสั่งบันทึกทุกอย่างตอบว่า "สำเร็จ" ในเครื่องนี้เท่านั้น ข้อมูลไม่ถูกเก็บ รีเฟรชแล้วกลับเป็นเดิม */
(function(){var rf=window.fetch.bind(window);
 window.fetch=function(u,o){var s=String(u&&u.url||u);if(s.indexOf('/api/')<0)return rf(u,o);
  var J=function(b,st){return Promise.resolve(new Response(JSON.stringify(b),{status:st||200,headers:{'Content-Type':'application/json'}}))};
  if(/part=idocr/.test(s))return J({error:'เดโมยังไม่เปิดอ่านบัตรอัตโนมัติ · กรอกเองได้'});
  if(/part=idimg/.test(s))return J({img:''});
  if(/\/api\/(insight|news|plan|summary)/.test(s))return J({error:'เดโมไม่ได้เชื่อม AI จริง'},503);
  return J({ok:true,demo:true})}})();
</script>"""
h = h.replace('<html lang="th">\n<head>', '<html lang="th">\n<head>' + SHIM, 1)
out = os.path.join(HERE, '..', 'public', 'demo.html')
open(out, 'w', encoding='utf-8').write(h)
print('wrote', out, len(h))
