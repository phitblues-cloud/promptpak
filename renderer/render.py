# -*- coding: utf-8 -*-
"""สร้างแอป PROMPT PAK (หน้าจอ v196 เดิมทุกอย่าง) จากข้อมูลจริง"""
import importlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ctx

ORDER = ['book', 'home', 'cust', 'hk', 'fin', 'linechat', 'rep', 'crm', 'crmtool', 'mkt']
_BASE = None
_BASE_MOCK = None


def base_html():
    global _BASE
    if _BASE is None:
        _BASE = open(os.path.join(HERE, 'base.html'), encoding='utf-8').read()
    return _BASE


def base_mock():
    global _BASE_MOCK
    if _BASE_MOCK is None:
        _BASE_MOCK = json.load(open(os.path.join(HERE, 'base_mock.json'), encoding='utf-8'))
    return _BASE_MOCK


def _load(name):
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


def split_shell(s):
    i = s.index('const MODS=') + 11
    M, end = json.JSONDecoder().raw_decode(s[i:])
    return s[:i], M, s[i + end:]


def modules(mock, now, only=None):
    """คืน dict ชื่อโมดูล -> HTML ของโมดูล (ใส่ข้อมูลจริงแล้ว)"""
    ctx.MOCK, ctx.NOW = mock, now
    _load('nb'); _load('patch_all'); _load('p_cust'); _load('p_crmtool')
    _, M, _ = split_shell(base_html())
    for k in (only or ORDER):
        M[k] = _load('p_' + k).patch(M[k])
    import realtime
    realtime.apply(M, now[:10])
    return {k: M[k] for k in (only or ORDER)} if only else M


def app(mock, now, head_extra='', post_extra=''):
    """คืน HTML ทั้งแอป"""
    M = modules(mock, now)
    pre, _, post = split_shell(base_html())
    pre = pre.replace('<html lang="th">\n<head>', '<html lang="th">\n<head>' + head_extra, 1)
    if post_extra:
        k = post.rindex('</script>')
        post = post[:k] + post_extra + post[k:]
    return pre + json.dumps(M, ensure_ascii=False).replace('</', '<\\/') + post
