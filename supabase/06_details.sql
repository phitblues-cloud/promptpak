-- PROMPT PAK · บันทึกรายละเอียดการจองครบ (คน/อาหารเช้า/ส่วนลด/บริษัท/เครดิต) + ตั้งค่าราคา/ประเภทห้อง/เพิ่มห้องบันทึกจริง
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;
-- ---------- รายละเอียดการจองครบ + ตั้งค่าห้องบันทึกจริง (25 ต.ค. 2569) ----------
alter table bookings add column if not exists details jsonb;

create or replace function pp_act(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  v_no text := nullif(p->>'no', '');
  b bookings; r record; s jsonb; o ops;
  v_id bigint; v_group text; v_nos jsonb := '[]'::jsonb; v_new text; v_in date; v_out date;
  v_undo jsonb := '{}'::jsonb; v_cnt int; v_net int;
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
    elsif o.kind = 'roomtype' then
      update rooms rr set room_type = x->>'type', rate = (x->>'rate')::int
      from jsonb_array_elements(coalesce(o.undo_info->'rooms', '[]')) x where rr.id = x->>'id';
    elsif o.kind = 'roomset' then
      if o.undo_info ? 'prev' then
        update rooms set zone = o.undo_info->'prev'->>'zone', room_type = o.undo_info->'prev'->>'room_type',
          rate = (o.undo_info->'prev'->>'rate')::int, max_guests = (o.undo_info->'prev'->>'max_guests')::int,
          closed = (o.undo_info->'prev'->>'closed')::boolean where id = o.data->>'room';
      else
        update rooms set active = false where id = upper(o.data->>'room');
      end if;
    elsif o.kind = 'book' then
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update ops set undone = true where kind in ('pay', 'credit') and booking_no in
        (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    end if;
    update ops set undone = true where id = o.id;
    return jsonb_build_object('ok', true, 'undone', o.id);
  end if;

  if k = 'book' then
    -- พนักงานจองเอง {guest, phone, company, check_in, check_out, channel, note, pay: now|later|dep|credit, m, cred_days,
    --               details:{adults, kids, purpose, email, code, co:{name,tax,addr,hq}, tax:{...}, payer, po},
    --               rooms:[{room, rate, guest, bf, disc, pax}]}
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
      v_net := coalesce((s->>'rate')::int, r.rate) * (v_out - v_in) + coalesce((s->>'bf')::int, 0) - coalesce((s->>'disc')::int, 0);
      insert into bookings (booking_no, group_no, guest_name, phone, company, room_id, check_in, check_out, rate,
                            created_by, channel, note, details)
      values (v_new, v_group, coalesce(nullif(trim(s->>'guest'), ''), trim(p->>'guest')), nullif(p->>'phone', ''),
              nullif(p->>'company', ''), r.id, v_in, v_out, coalesce((s->>'rate')::int, r.rate),
              'staff', coalesce(nullif(p->>'channel', ''), 'Walk-in'), nullif(p->>'note', ''),
              coalesce(p->'details', '{}'::jsonb) || jsonb_build_object('bf', coalesce((s->>'bf')::int, 0),
                'disc', coalesce((s->>'disc')::int, 0), 'pax', coalesce((s->>'pax')::int, 1), 'pay', coalesce(p->>'pay', 'later'),
                'cred_days', coalesce((p->>'cred_days')::int, 30)));
      v_nos := v_nos || to_jsonb(v_new);
      if coalesce(p->>'pay', case when coalesce((p->>'paid')::boolean, false) then 'now' end) = 'now' then
        insert into ops (role, kind, booking_no, data) values (p_role, 'pay', v_new,
          jsonb_build_object('m', coalesce(p->>'m', 'cash'), 'room_amt', v_net));
      elsif p->>'pay' = 'dep' then        -- บริษัทจ่ายมัดจำ 30% ที่เหลือชำระภายหลัง
        insert into ops (role, kind, booking_no, data) values (p_role, 'pay', v_new,
          jsonb_build_object('m', coalesce(p->>'m', 'transfer'), 'room_amt', round(v_net * 0.3)::int, 'partial', true));
      elsif p->>'pay' = 'credit' then
        insert into ops (role, kind, booking_no, data) values (p_role, 'credit', v_new,
          jsonb_build_object('days', coalesce((p->>'cred_days')::int, 30)));
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

  elsif k = 'roomtype' then
    -- ตั้งค่าประเภทห้อง (ทั้งกลุ่ม) {zone, type, new_type, rate}
    if nullif(trim(p->>'new_type'), '') is null then raise exception 'ต้องมีชื่อประเภทห้อง'; end if;
    if coalesce((p->>'rate')::int, 0) <= 0 then raise exception 'ราคาต้องมากกว่า 0'; end if;
    v_undo := jsonb_build_object('rooms', (select jsonb_agg(jsonb_build_object('id', id, 'type', room_type, 'rate', rate))
                                           from rooms where zone = p->>'zone' and room_type = p->>'type'));
    update rooms set room_type = trim(p->>'new_type'), rate = (p->>'rate')::int
    where zone = p->>'zone' and room_type = p->>'type';
    get diagnostics v_cnt = row_count;
    if v_cnt = 0 then raise exception 'ไม่พบประเภทห้อง % ในโซน %', p->>'type', p->>'zone'; end if;

  elsif k = 'roomset' then
    -- เพิ่มห้อง / แก้ห้องรายตัว {room, zone, type, rate, max, open}
    if nullif(trim(p->>'room'), '') is null then raise exception 'ต้องมีรหัสห้อง'; end if;
    v_undo := coalesce((select jsonb_build_object('prev', to_jsonb(rr)) from rooms rr where id = p->>'room'), '{"new": true}'::jsonb);
    insert into rooms (id, zone, room_type, bed, rate, max_guests, floor, closed)
    values (upper(trim(p->>'room')), p->>'zone', trim(p->>'type'),
            coalesce(nullif(trim(p->>'bed'), ''), (select bed from rooms where zone = p->>'zone' and room_type = trim(p->>'type') limit 1)),
            (p->>'rate')::int, coalesce((p->>'max')::int, 2),
            case when upper(p->>'room') like 'B%' then 2 else 1 end, not coalesce((p->>'open')::boolean, true))
    on conflict (id) do update set zone = excluded.zone, room_type = excluded.room_type, rate = excluded.rate,
      max_guests = excluded.max_guests, closed = excluded.closed, active = true,
      bed = coalesce(excluded.bed, rooms.bed);

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

create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed),
    (select md5(string_agg(id || room_type || rate || max_guests || active::text, ',' order by id)) from rooms))
$$;

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
    'closed_rooms', coalesce((select jsonb_agg(id order by id) from rooms where closed), '[]'),
    'rooms', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'zone', zone, 'room_type', room_type, 'bed', bed,
        'rate', rate, 'max_guests', max_guests, 'floor', floor, 'closed', closed) order by id) from rooms where active), '[]'))
$$;

-- ประเภทห้องปัจจุบัน (ให้ AI ใช้ราคา/ชื่อล่าสุดที่เจ้าของตั้ง)
create or replace function pp_room_types() returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(jsonb_build_object('zone', zone, 'room_type', room_type, 'rate', rate, 'max_guests', max_guests,
    'bed', bed, 'rooms', n, 'ground_floor', g) order by zone desc, rate, room_type), '[]')
  from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) n,
               count(*) filter (where floor = 1) g
        from rooms where active and not closed group by zone, room_type) t
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_act', 'pp_stamp', 'pp_export', 'pp_room_types') loop
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
