-- PROMPT PAK · ไม่มาตามนัด = ยกเลิกอัตโนมัติ / ลืมเช็คเอาท์ = ห้องยังไม่ว่าง (25 ต.ค. 2569)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;
-- ---------- กฎวันจริง (25 ต.ค. 2569) ----------
-- 1) เลยวันเข้าพัก (ถึง 06:00 วันถัดไป) แล้วไม่ได้เช็คอิน -> ยกเลิก (ไม่มาตามนัด) ห้องว่างให้ขายต่อ
-- 2) แขกที่เช็คอินแล้วแต่ยังไม่กดเช็คเอาท์ ถือว่ายังอยู่ในห้อง (AI จองห้องนั้นวันนี้ไม่ได้)
-- ใช้กับการจองจริง และข้อมูลตัวอย่างที่เข้าพักตั้งแต่ 25 ต.ค. 2569 (วันเริ่มใช้งานจริง)
create or replace function pp_checked_in(p_no text) returns boolean language sql stable as $$
  select exists (select 1 from ops o where o.booking_no = p_no and o.kind = 'checkin' and not o.undone)
      or exists (select 1 from bookings b where b.booking_no = p_no and b.created_by = 'seed' and b.check_in < date '2026-10-25')
$$;

create or replace function pp_noshow() returns int language plpgsql as $$
declare n int;
begin
  with x as (
    update bookings b set status = 'ยกเลิก'
    where b.status <> 'ยกเลิก' and (b.created_by <> 'seed' or b.check_in >= date '2026-10-25')
      and b.check_in < ((now() at time zone 'Asia/Bangkok') - interval '6 hours')::date
      and not pp_checked_in(b.booking_no)
    returning b.booking_no)
  insert into ops (role, kind, booking_no, data)
  select 'system', 'cancel', booking_no, '{"why": "ไม่มาตามนัด (ระบบยกเลิกอัตโนมัติเมื่อเลยวันเข้าพัก)", "noshow": true}'::jsonb from x;
  get diagnostics n = row_count;
  return n;
end $$;

create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not r.closed and not exists (
      select 1 from bookings b
      where b.room_id = r.id and b.status <> 'ยกเลิก'
        and daterange(b.check_in, b.check_out, '[)') && daterange(p_check_in, p_check_out, '[)'))
      and not exists (   -- แขกที่เช็คอินแล้วแต่ยังไม่กดเช็คเอาท์ (เลยวันออก) ยังอยู่ในห้อง
        select 1 from bookings b2
        where b2.room_id = r.id and b2.status <> 'ยกเลิก' and b2.check_out <= pp_today() and p_check_in <= pp_today()
          and b2.check_out >= date '2026-10-25' and pp_checked_in(b2.booking_no)
          and not exists (select 1 from ops ox where ox.booking_no = b2.booking_no and ox.kind = 'checkout' and not ox.undone))
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
        and (not v_ground or rm.floor = 1) and not rm.closed
        and not exists (
          select 1 from bookings b where b.room_id = rm.id and b.status <> 'ยกเลิก'
            and daterange(b.check_in, b.check_out, '[)') && daterange(v_in, v_out, '[)'))
        and not exists (
          select 1 from bookings b2
          where b2.room_id = rm.id and b2.status <> 'ยกเลิก' and b2.check_out <= pp_today() and v_in <= pp_today()
            and b2.check_out >= date '2026-10-25' and pp_checked_in(b2.booking_no)
            and not exists (select 1 from ops ox where ox.booking_no = b2.booking_no and ox.kind = 'checkout' and not ox.undone))
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
           where n.nspname = 'public' and p.proname in ('pp_noshow', 'pp_checked_in', 'pp_availability', 'pp_book') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
commit;
