-- PROMPT PAK · ปุ่มหน้าเคาน์เตอร์บันทึกลงฐานข้อมูลจริง (25 ต.ค. 2569)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้ ไม่ลบข้อมูล)
begin;

-- ---------- บันทึกการทำงานหน้าเคาน์เตอร์ (เช็คอิน รับเงิน มัดจำ เช็คเอาท์ ฯลฯ) ----------
create table if not exists ops (
  id         bigserial primary key,
  at         timestamptz not null default now(),
  role       text,                                 -- owner / staff
  kind       text not null,                        -- book, pay, dep_in, dep_out, checkin, checkout, credit, cancel, extend, room
  booking_no text,
  data       jsonb not null default '{}'::jsonb,
  undone     boolean not null default false,
  undo_info  jsonb
);
create index if not exists ops_booking on ops (booking_no);
alter table ops enable row level security;

-- ห้องปิดซ่อม (ยังอยู่ในระบบ แต่ไม่เปิดขาย)
alter table rooms add column if not exists closed boolean not null default false;

-- ห้องว่าง: ไม่นับห้องที่ปิด
create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not r.closed and not exists (
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

-- AI จองไม่ได้ในห้องที่ปิด
-- จองห้อง (ทำทั้งหมดหรือไม่ทำเลย)
-- p = {guest_name, phone, company, line_user_id, check_in, check_out, created_by, note, prefer_ground_floor,
--      items:[{zone, room_type, count}]}
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
        and (not v_ground or rm.floor = 1) and not rm.closed
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

create or replace function pp_room_closed(p_room text) returns boolean language sql stable as $$
  select coalesce((select closed from rooms where id = p_room), false)
$$;

-- วันที่จาก JSON (YYYY-MM-DD)
create or replace function pp_d(v text) returns date language sql immutable as $$ select v::date $$;

-- ---------- ปุ่มในหน้าจอ -> ฐานข้อมูล ----------
-- p = {k: ชนิด, no: เลขการจอง, ...}
create or replace function pp_act(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  v_no text := nullif(p->>'no', '');
  b bookings; r record; s jsonb; o ops;
  v_id bigint; v_group text; v_nos jsonb := '[]'::jsonb; v_new text; v_in date; v_out date;
  v_undo jsonb := '{}'::jsonb; v_cnt int;
begin
  if k is null then raise exception 'ไม่ระบุชนิดการบันทึก'; end if;

  if k = 'undo' then
    select * into o from ops where id = (p->>'id')::bigint and not undone;
    if o.id is null then return jsonb_build_object('ok', true, 'skip', true); end if;
    if o.kind = 'cancel' then
      update bookings set status = 'ยืนยันแล้ว' where booking_no = o.booking_no;
    elsif o.kind in ('extend', 'checkout') and o.undo_info ? 'prev_out' then
      update ops set undone = true where at = o.at and data->>'move' = 'true'
        and (booking_no = o.booking_no or booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]'))));
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update bookings set check_out = pp_d(o.undo_info->>'prev_out') where booking_no = o.booking_no;
    elsif o.kind = 'extend' then
      update ops set undone = true where at = o.at and data->>'move' = 'true'
        and (booking_no = o.booking_no or booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]'))));
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    elsif o.kind = 'room' then
      update rooms set closed = (o.undo_info->>'prev_closed')::boolean where id = o.data->>'room';
    elsif o.kind = 'book' then
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update ops set undone = true where kind = 'pay' and booking_no in
        (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    end if;
    update ops set undone = true where id = o.id;
    return jsonb_build_object('ok', true, 'undone', o.id);
  end if;

  if k = 'book' then
    -- พนักงานจองเอง: เลือกห้องเอง {guest, phone, company, check_in, check_out, rooms:[{room}], channel, note, paid, m}
    v_in := pp_d(p->>'check_in'); v_out := pp_d(p->>'check_out');
    if nullif(trim(p->>'guest'), '') is null then raise exception 'ต้องมีชื่อผู้เข้าพัก'; end if;
    if v_out <= v_in then raise exception 'วันออกต้องหลังวันเข้าพัก'; end if;
    v_cnt := jsonb_array_length(coalesce(p->'rooms', '[]'));
    if v_cnt < 1 then raise exception 'ต้องเลือกห้องอย่างน้อย 1 ห้อง'; end if;
    v_group := case when v_cnt > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;
    for s in select * from jsonb_array_elements(p->'rooms') loop
      select * into r from rooms where id = s->>'room' and active;
      if r.id is null then raise exception 'ไม่มีห้อง %', s->>'room'; end if;
      v_new := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_name, phone, company, room_id, check_in, check_out, rate,
                            created_by, channel, note)
      values (v_new, v_group, coalesce(nullif(trim(s->>'guest'), ''), trim(p->>'guest')), nullif(p->>'phone', ''),
              nullif(p->>'company', ''), r.id, v_in, v_out, coalesce((s->>'rate')::int, r.rate),
              'staff', coalesce(nullif(p->>'channel', ''), 'Walk-in'), nullif(p->>'note', ''));
      v_nos := v_nos || to_jsonb(v_new);
      if coalesce((p->>'paid')::boolean, false) then
        insert into ops (role, kind, booking_no, data) values (p_role, 'pay', v_new,
          jsonb_build_object('m', coalesce(p->>'m', 'cash'), 'room_amt', coalesce((s->>'rate')::int, r.rate) * (v_out - v_in)));
      end if;
    end loop;
    v_undo := jsonb_build_object('new_nos', v_nos);
    v_no := v_nos->>0;

  elsif k = 'cancel' then
    update bookings set status = 'ยกเลิก' where booking_no = v_no and status <> 'ยกเลิก';

  elsif k = 'extend' then
    -- พักต่อ {no, segs:[{room, from: YYYY-MM-DD, n, rate}]}
    select * into b from bookings where booking_no = v_no;
    if b.id is null then raise exception 'ไม่พบการจอง %', v_no; end if;
    v_undo := jsonb_build_object('prev_out', b.check_out);
    for s in select * from jsonb_array_elements(p->'segs') loop
      v_in := pp_d(s->>'from'); v_out := v_in + (s->>'n')::int;
      if s->>'room' = b.room_id and v_in = (select check_out from bookings where id = b.id) then
        update bookings set check_out = v_out where id = b.id;
      else
        if pp_room_closed(s->>'room') then raise exception 'ห้อง % ปิดอยู่', s->>'room'; end if;
        v_new := pp_next_booking_no();
        insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id, check_in, check_out,
                              rate, created_by, channel, note)
        values (v_new, b.group_no, b.guest_id, b.guest_name, b.phone, b.company, s->>'room', v_in, v_out,
                coalesce((s->>'rate')::int, b.rate), 'staff', 'Walk-in', 'พักต่อจาก ' || v_no);
        v_nos := v_nos || to_jsonb(v_new);
      end if;
    end loop;
    v_undo := v_undo || jsonb_build_object('new_nos', v_nos);
    -- ย้ายห้องทันที: ห้องเดิมเช็คเอาท์ ห้องใหม่เข้าพักเลย
    if coalesce((p->>'move_now')::boolean, false) and jsonb_array_length(v_nos) > 0 then
      insert into ops (role, kind, booking_no, data) values
        (p_role, 'checkout', v_no, '{"move": true}'), (p_role, 'checkin', v_nos->>0, '{"move": true}');
    end if;

  elsif k = 'checkout' and p ? 'nights' then
    -- เช็คเอาท์ก่อนกำหนด: คิดเฉพาะคืนที่พักจริง ห้องว่างให้จองต่อได้
    select * into b from bookings where booking_no = v_no;
    if b.id is not null and b.check_in + (p->>'nights')::int < b.check_out then
      v_undo := jsonb_build_object('prev_out', b.check_out);
      update bookings set check_out = b.check_in + greatest(1, (p->>'nights')::int) where id = b.id;
    end if;

  elsif k = 'room' then
    -- เปิด/ปิดห้อง {room, open}
    select * into r from rooms where id = p->>'room';
    if r.id is null then raise exception 'ไม่มีห้อง %', p->>'room'; end if;
    v_undo := jsonb_build_object('prev_closed', r.closed);
    update rooms set closed = not coalesce((p->>'open')::boolean, true) where id = r.id;

  elsif k not in ('pay', 'dep_in', 'dep_out', 'checkin', 'checkout', 'credit') then
    raise exception 'ไม่รู้จักการบันทึกชนิด %', k;
  end if;

  if v_no is not null and k <> 'book' and not exists (select 1 from bookings where booking_no = v_no) then
    raise exception 'ไม่พบการจอง % ในฐานข้อมูล', v_no;
  end if;

  insert into ops (role, kind, booking_no, data, undo_info)
  values (p_role, k, v_no, p - 'k' - 'no', v_undo) returning id into v_id;
  return jsonb_build_object('ok', true, 'id', v_id, 'nos', v_nos);
end $$;

-- ค่าที่เปลี่ยนเมื่อข้อมูลเปลี่ยน (นับการบันทึกหน้าเคาน์เตอร์ด้วย)
create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed))
$$;

-- ข้อมูลทั้งหมดที่หน้าจอใช้
create or replace function pp_export() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'stamp', pp_stamp(),
    'bookings', coalesce((select jsonb_agg(to_jsonb(b) - 'id' order by b.booking_no) from bookings b), '[]'),
    'guests', coalesce((select jsonb_agg(to_jsonb(g)) from guests g), '[]'),
    'threads', coalesce((select jsonb_agg(jsonb_build_object('id', t.id, 'line_user_id', t.line_user_id,
        'display_name', t.display_name, 'needs_staff', t.needs_staff, 'is_seed', t.is_seed,
        'messages', (select coalesce(jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'at', created_at)
                       order by created_at, id), '[]') from chat_messages m where m.thread_id = t.id))
        order by t.id)
      from chat_threads t where not t.is_seed), '[]'),
    'ops', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'at', at, 'role', role, 'kind', kind,
        'no', booking_no, 'data', data) order by id) from ops where not undone), '[]'),
    'closed_rooms', coalesce((select jsonb_agg(id order by id) from rooms where closed), '[]'))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_availability', 'pp_book', 'pp_room_closed', 'pp_d', 'pp_act', 'pp_stamp', 'pp_export') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
grant all on table ops to service_role;
grant all on sequence ops_id_seq to service_role;

commit;
