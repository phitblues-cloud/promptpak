# -*- coding: utf-8 -*-
"""สิทธิ์เข้าใช้งาน: PIN เจ้าของ / PIN พนักงาน -> คุกกี้ลงลายเซ็น (HMAC) อายุ 12 ชั่วโมง"""
import hashlib, hmac, os, time

COOKIE = 'pp_sess'
TTL = 12 * 3600
NAMES = {'owner': 'เจ้าของรีสอร์ท', 'staff': 'พนักงานต้อนรับ'}


def _secret():
    s = (os.environ.get('APP_SECRET') or '').strip()
    if not s:
        raise RuntimeError('ยังไม่ได้ตั้งค่า APP_SECRET')
    return s.encode()


def sign(role):
    exp = int(time.time()) + TTL
    msg = f'{role}.{exp}'
    sig = hmac.new(_secret(), msg.encode(), hashlib.sha256).hexdigest()
    return f'{msg}.{sig}'


def verify(value):
    try:
        role, exp, sig = (value or '').split('.')
        good = hmac.new(_secret(), f'{role}.{exp}'.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, good) and int(exp) > time.time() and role in NAMES:
            return role
    except Exception:
        pass
    return None


THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')


def norm_pin(v):
    """ตัดช่องว่าง และแปลงเลขไทยเป็นเลขอารบิก"""
    return ''.join(str(v or '').translate(THAI_DIGITS).split())


def check_pin(role, pin):
    want = norm_pin(os.environ.get('OWNER_PIN' if role == 'owner' else 'STAFF_PIN'))
    return bool(want) and hmac.compare_digest(norm_pin(pin), want)


def cookie_header(value, max_age):
    secure = '' if os.environ.get('LOCAL_DEV') else '; Secure'
    return f'{COOKIE}={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{secure}'


def from_cookie_header(raw):
    for part in (raw or '').split(';'):
        k, _, v = part.strip().partition('=')
        if k == COOKIE:
            return verify(v)
    return None
