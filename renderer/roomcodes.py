# -*- coding: utf-8 -*-
"""รหัสห้องเก่า (ก่อน 24 ต.ค. 2569) -> รหัสห้องจริง
ตึกใหม่: A01–A08 ชั้น 1, B01–B08 ชั้น 2 · บ้านหลัง: C01–C15 (ชั้นเดียว)"""
import re

T_SINGLE_IDS = ['A02', 'A03', 'A06', 'A07', 'A08', 'B01', 'B02', 'B03', 'B06', 'B07', 'B08']
T_TWIN_IDS = ['A01', 'B04', 'B05']
T_FAMILY_IDS = ['A04', 'A05']

# จับคู่ตามประเภทในต้นแบบ v196: ตึก 1–11 เตียงเดี่ยว, 12–14 เตียงคู่, 15–16 ราคา 800 / บ้าน 1–12 เดี่ยว, 13–15 คู่
OLD2NEW = {'A%03d' % i: new for i, new in enumerate(T_SINGLE_IDS + T_TWIN_IDS + T_FAMILY_IDS, 1)}
OLD2NEW.update({'B%03d' % i: 'C%02d' % i for i in range(1, 16)})

OLD_RE = re.compile(r'(?<![A-Za-z0-9#])([AB]0\d\d)(?![0-9A-Za-z])')


def remap_text(s):
    return OLD_RE.sub(lambda m: OLD2NEW.get(m.group(1), m.group(1)), s)


def new_code(c):
    return OLD2NEW.get(c, c)
