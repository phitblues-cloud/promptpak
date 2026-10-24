# -*- coding: utf-8 -*-
"""ข้อมูลห้องจริงของพบรักรีสอร์ท (ยืนยันโดยเจ้าของ 24 ต.ค. 2569) + ตารางแปลงรหัสห้องเก่า -> ใหม่

ใช้: python3 tools/rooms_2569.py   (แปลง renderer/base_mock.json + สร้าง supabase/03_rooms_2569.sql)
รันซ้ำได้: ถ้าแปลงแล้ว จะไม่เปลี่ยนอะไรเพิ่ม
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'renderer'))
from roomcodes import T_SINGLE_IDS, T_TWIN_IDS, T_FAMILY_IDS, OLD2NEW, remap_text  # noqa: E402

BASE_AMEN = ['แอร์', 'น้ำอุ่น', 'ทีวี', 'ตู้เย็น', 'กาต้มน้ำ', 'WiFi']
TOWER_AMEN = BASE_AMEN + ['ระเบียง', 'โต๊ะทำงาน', 'ไดร์เป่าผม']

# (รหัส, โซน, ชั้น, ประเภท, รายละเอียดเตียง, ราคา, พักได้)
_T_SINGLE = ('ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2)
_T_TWIN = ('ตึกใหม่', 'เตียงคู่', 'เตียงสองชั้น (ชั้นบนเตียงเดี่ยว + ชั้นล่างเตียงเดี่ยว)', 700, 2)
_T_FAMILY = ('ตึกใหม่', 'ห้องครอบครัว', 'เตียงสองชั้น (ชั้นล่างเตียงใหญ่ 2 คน + ชั้นบนเตียงเดี่ยว 1 คน)', 800, 3)
_H_SINGLE = ('บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2)
_H_TWIN = ('บ้านหลัง', 'เตียงคู่', 'เตียงเดี่ยว 2 เตียง วางแยกกัน', 500, 2)

def _room(rid, spec):
    zone, typ, bed, rate, mx = spec
    floor = 2 if rid.startswith('B') else 1
    return {'room_id': rid, 'zone': zone, 'building': zone, 'floor': floor, 'room_type': typ, 'bed': bed,
            'rack_rate': rate, 'max_guests': mx, 'amenities': TOWER_AMEN if zone == 'ตึกใหม่' else BASE_AMEN}


ROOMS = sorted([_room(i, _T_SINGLE) for i in T_SINGLE_IDS] + [_room(i, _T_TWIN) for i in T_TWIN_IDS]
               + [_room(i, _T_FAMILY) for i in T_FAMILY_IDS], key=lambda r: r['room_id']) \
    + [_room('C%02d' % i, _H_SINGLE) for i in range(1, 13)] + [_room('C%02d' % i, _H_TWIN) for i in range(13, 16)]
ROOMBY = {r['room_id']: r for r in ROOMS}

def _walk(o):
    if isinstance(o, dict):
        return {k: _walk(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_walk(v) for v in o]
    if isinstance(o, str):
        return remap_text(o)
    return o


def convert_mock(m):
    m = _walk(m)
    m['rooms'] = [dict(r) for r in ROOMS]
    m['hotel']['rooms_total'] = len(ROOMS)
    # ปรับราคาการจองตัวอย่างให้ตรงราคาห้องใหม่ (คงส่วนลดเดิม) แล้วปรับยอดเงินที่ผูกกับการจองนั้นตาม
    delta = {}
    for b in m['bookings']:
        r = ROOMBY[b['room_id']]
        d = r['rack_rate'] - b['rack_rate']
        if d:
            old_total = b['room_total']
            b['rate'] += d
            b['room_total'] = b['rate'] * b['nights']
            delta[b['booking_id']] = (old_total, b['room_total'])
        b['zone'], b['room_type'], b['rack_rate'] = r['zone'], r['room_type'], r['rack_rate']
    for p in m['payments']:
        if p['booking_id'] in delta and (p['type'].startswith('ค่าห้อง') or p['type'].startswith('คืนเงินยกเลิก')):
            o, n = delta[p['booking_id']]
            p['amount'] = round(p['amount'] * n / o) if o else p['amount']
    for t in m['tax_invoices']:
        add = sum(delta[b][1] - delta[b][0] for b in t['booking_ids'] if b in delta)
        if add:
            t['total'] += add
            t['amount_before_vat'] = round(t['total'] / 1.07, 2)
            t['vat'] = round(t['total'] - t['amount_before_vat'], 2)
    for x in m['receivables']:
        if x['booking_id'] in delta:
            x['amount'] += delta[x['booking_id']][1] - delta[x['booking_id']][0]
    for h in m['housekeeping_at_ref']:
        h['zone'] = ROOMBY[h['room_id']]['zone']
    return m


def q(v):
    return 'null' if v is None else "'" + str(v).replace("'", "''") + "'"


def room_sql_rows():
    return ',\n'.join('  (%s, %s, %s, %s, %d, %d, %d)' % (q(r['room_id']), q(r['zone']), q(r['room_type']), q(r['bed']),
                                                          r['rack_rate'], r['max_guests'], r['floor']) for r in ROOMS)


def migration_sql():
    pairs = ',\n'.join('  (%s, %s)' % (q(o), q(n)) for o, n in OLD2NEW.items())
    return f"""-- ---------- ห้องจริง 2569: รหัส/โซน/ประเภทใหม่ (รันซ้ำได้) ----------
-- โซนตึกใหม่ 16 ห้อง (A = ชั้น 1, B = ชั้น 2) · โซนบ้านหลัง 15 ห้อง (C01–C15 ชั้นเดียว)
alter table rooms drop constraint if exists rooms_zone_check;
alter table rooms add column if not exists floor int not null default 1;

insert into rooms (id, zone, room_type, bed, rate, max_guests, floor) values
{room_sql_rows()}
on conflict (id) do update set zone = excluded.zone, room_type = excluded.room_type, bed = excluded.bed,
  rate = excluded.rate, max_guests = excluded.max_guests, floor = excluded.floor, active = true;

-- ย้ายการจองทุกรายการ (รวมการจองจริงจาก LINE) จากรหัสเก่าไปรหัสใหม่ แล้วลบห้องรหัสเก่า
update bookings b set room_id = m.new_id
from (values
{pairs}
) as m(old_id, new_id)
where b.room_id = m.old_id;
delete from rooms where id ~ '^[AB]0[0-9][0-9]$';
alter table rooms add constraint rooms_zone_check check (zone in ('ตึกใหม่', 'บ้านหลัง'));

-- ห้องว่างแยกตามโซน + ประเภท (นับห้องชั้น 1 ที่ว่างด้วย)
create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not exists (
      select 1 from bookings b
      where b.room_id = r.id and b.status <> 'ยกเลิก'
        and daterange(b.check_in, b.check_out, '[)') && daterange(p_check_in, p_check_out, '[)'))
  )
  select jsonb_build_object(
    'check_in', p_check_in, 'check_out', p_check_out, 'nights', p_check_out - p_check_in,
    'types', coalesce((
      select jsonb_agg(jsonb_build_object(
        'zone', t.zone, 'room_type', t.room_type, 'rate', t.rate, 'max_guests', t.max_guests,
        'bed', t.bed, 'total_rooms', t.total,
        'free_rooms', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type),
        'free_ground_floor', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type and f.floor = 1))
        order by t.zone desc, t.rate, t.room_type)
      from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) total
            from rooms where active group by zone, room_type) t), '[]'::jsonb))
$$;

-- จองห้อง (ทำทั้งหมดหรือไม่ทำเลย)
-- p = {{guest_name, phone, company, line_user_id, check_in, check_out, created_by, note, prefer_ground_floor,
--      items:[{{zone, room_type, count}}]}}
-- prefer_ground_floor = true -> จัดเฉพาะห้องชั้น 1 ถ้าไม่พอจะไม่จอง (ให้พนักงานดูแลต่อ)
create or replace function pp_book(p jsonb) returns jsonb language plpgsql as $$
declare
  v_in date := (p->>'check_in')::date;
  v_out date := (p->>'check_out')::date;
  v_by text := coalesce(p->>'created_by', 'staff');
  v_name text := nullif(trim(p->>'guest_name'), '');
  v_phone text := nullif(regexp_replace(coalesce(p->>'phone', ''), '[^0-9+]', '', 'g'), '');
  v_ground boolean := coalesce((p->>'prefer_ground_floor')::boolean, false);
  v_guest uuid; v_group text; v_no text; v_total_rooms int := 0; v_zone text;
  it jsonb; r record; v_cnt int; v_got int; out_rows jsonb := '[]'::jsonb;
begin
  if v_name is null then raise exception 'ต้องมีชื่อผู้จอง'; end if;
  if v_phone is null or length(v_phone) < 9 then raise exception 'ต้องมีเบอร์โทรที่ถูกต้อง'; end if;
  if v_in is null or v_out is null or v_out <= v_in then raise exception 'วันเข้าพัก/วันออกไม่ถูกต้อง'; end if;
  if v_in < pp_today() then raise exception 'วันเข้าพักต้องไม่ใช่วันที่ผ่านมาแล้ว'; end if;
  if v_out - v_in > 30 then raise exception 'จองได้ครั้งละไม่เกิน 30 คืน'; end if;
  select coalesce(sum((x->>'count')::int), 0) into v_total_rooms from jsonb_array_elements(p->'items') x;
  if v_total_rooms < 1 then raise exception 'ต้องระบุจำนวนห้องอย่างน้อย 1 ห้อง'; end if;
  -- ราวกันตกชั้นที่ 3: AI ยืนยันเองได้ไม่เกิน 4 ห้อง (5 ห้องขึ้นไปส่งพนักงาน)
  if v_by = 'ai' and v_total_rooms > 4 then raise exception 'จอง 5 ห้องขึ้นไปต้องให้พนักงานยืนยัน'; end if;

  if p->>'line_user_id' is not null then
    insert into guests (full_name, phone, company, line_user_id, line_display_name)
    values (v_name, v_phone, p->>'company', p->>'line_user_id', p->>'line_display_name')
    on conflict (line_user_id) do update
      set full_name = excluded.full_name, phone = excluded.phone,
          company = coalesce(excluded.company, guests.company)
    returning id into v_guest;
  end if;

  v_group := case when v_total_rooms > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;

  for it in select * from jsonb_array_elements(p->'items') loop
    v_cnt := (it->>'count')::int; v_got := 0; v_zone := nullif(it->>'zone', '');
    if v_cnt is null or v_cnt < 1 then continue; end if;
    if v_zone is null and (select count(distinct zone) from rooms where room_type = it->>'room_type' and active) > 1 then
      raise exception 'ประเภท % มีทั้งโซนตึกใหม่และโซนบ้านหลัง ต้องระบุโซน', it->>'room_type';
    end if;
    if not exists (select 1 from rooms where room_type = it->>'room_type' and (v_zone is null or zone = v_zone) and active) then
      raise exception 'ไม่มีห้องประเภท % ในโซน %', it->>'room_type', coalesce(v_zone, '-');
    end if;
    for r in
      select rm.* from rooms rm
      where rm.active and rm.room_type = it->>'room_type' and (v_zone is null or rm.zone = v_zone)
        and (not v_ground or rm.floor = 1)
        and not exists (
          select 1 from bookings b where b.room_id = rm.id and b.status <> 'ยกเลิก'
            and daterange(b.check_in, b.check_out, '[)') && daterange(v_in, v_out, '[)'))
      order by rm.id limit v_cnt
      for update
    loop
      v_no := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id,
                            check_in, check_out, rate, created_by, channel, note)
      values (v_no, v_group, v_guest, v_name, v_phone, p->>'company', r.id,
              v_in, v_out, r.rate, v_by, coalesce(p->>'channel', 'LINE OA'),
              nullif(concat_ws(' · ', case when v_ground then 'ขอห้องชั้นล่าง' end, p->>'note'), ''));
      out_rows := out_rows || jsonb_build_object('booking_no', v_no, 'room_id', r.id, 'zone', r.zone, 'floor', r.floor,
                    'room_type', r.room_type, 'rate', r.rate, 'room_total', r.rate * (v_out - v_in));
      v_got := v_got + 1;
    end loop;
    if v_got < v_cnt then
      if v_ground then
        raise exception 'ห้องชั้นล่าง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
      end if;
      raise exception 'ห้อง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'group_no', v_group, 'check_in', v_in, 'check_out', v_out,
    'nights', v_out - v_in, 'bookings', out_rows,
    'room_total', (select coalesce(sum((x->>'room_total')::int), 0) from jsonb_array_elements(out_rows) x),
    'deposit_total', 300 * jsonb_array_length(out_rows));
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_availability', 'pp_book') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
"""


if __name__ == '__main__':
    assert len(ROOMS) == 31 and len(set(OLD2NEW.values())) == 31
    p = ROOT / 'renderer' / 'base_mock.json'
    m = json.load(open(p, encoding='utf-8'))
    m = convert_mock(m)
    p.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
    sql = migration_sql()
    (ROOT / 'supabase' / '03_rooms_2569.sql').write_text(
        '-- PROMPT PAK · อัปเดตห้องจริง (24 ต.ค. 2569)\n'
        '-- วิธีใช้: Supabase > SQL Editor > วางทั้งไฟล์ > Run (รันซ้ำได้ ไม่ลบการจอง)\n'
        'begin;\n' + sql + 'commit;\n', encoding='utf-8')
    print('ok: base_mock.json + supabase/03_rooms_2569.sql')
