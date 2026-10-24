# -*- coding: utf-8 -*-
import json, sys, importlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, 'live131_base.html')       # = v193 ที่เผยแพร่ล่าสุด (ไม่แก้ไฟล์นี้)
OUT = os.path.join(HERE, 'pobrak-app-single-file.html')

def R(s, a, b, cnt=1, tag=''):
    n = s.count(a)
    assert n == cnt, f'[{tag}] expected {cnt} got {n} for: {a[:90]!r}'
    return s.replace(a, b)

def J(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

DATE_OVR = ("<script>(function(){var D=Date,off=0,w=window;for(var i=0;i<6;i++){try{if(w.__VOFF!=null){off=w.__VOFF;break}}catch(e){}"
            "if(w.parent===w)break;w=w.parent}"
            "class VD extends D{constructor(...a){if(a.length===0)super(D.now()+off);else super(...a)}static now(){return D.now()+off}}"
            "window.Date=VD})();</script>")

def main(mods=None):
    s = open(SRC).read()
    i = s.index('const MODS=') + 11
    M, end = json.JSONDecoder().raw_decode(s[i:])
    pre, post = s[:i], s[i + end:]
    names = mods or ['book', 'home', 'cust', 'hk', 'fin', 'linechat', 'rep', 'crm', 'crmtool', 'mkt']
    for k in names:
        try:
            mod = importlib.import_module('p_' + k)
        except ModuleNotFoundError as e:
            if e.name == 'p_' + k:
                print('skip', k); continue
            raise
        importlib.reload(mod)
        M[k] = mod.patch(M[k])
        print('patched', k, len(M[k]))
    # วันที่เสมือน
    for k in M:
        M[k] = M[k].replace('<head>', '<head>' + DATE_OVR, 1)
    # shell
    pre = R(pre, '<html lang="th">\n<head>', '<html lang="th">\n<head><script>window.__VOFF=new Date(2026,9,24,10,0,0).getTime()-Date.now();</script>', 1, 'shell-head')
    out = pre + json.dumps(M, ensure_ascii=False).replace('</', '<\\/') + post
    open(OUT, 'w').write(out)
    print('wrote', OUT, len(out))

if __name__ == '__main__':
    main(sys.argv[1:] or None)
