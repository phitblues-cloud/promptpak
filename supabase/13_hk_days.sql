-- PROMPT PAK · แม่บ้าน: วันทำงานประจำสัปดาห์ + สวิตช์ "ทำงาน/หยุด" ใช้เฉพาะวันนี้
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้) · ต้องรัน 12_hk.sql ก่อน
begin;

alter table hk_staff add column if not exists days jsonb;      -- วันทำงาน [0..6] (0 = อาทิตย์) · null = ทุกวัน
alter table hk_staff add column if not exists ovr_day date;    -- วันที่กดสวิตช์ ทำงาน/หยุด (มีผลเฉพาะวันนั้น)
alter table hk_staff add column if not exists ovr_on boolean;

-- ตามตาราง: วันนี้เป็นวันทำงานไหม
create or replace function pp_hk_sched(p_days jsonb) returns boolean language sql stable as $$
  select case when p_days is null or jsonb_typeof(p_days) <> 'array' then true
              else p_days @> to_jsonb(extract(dow from pp_today())::int) end
$$;

-- ทำงานวันนี้จริง: ถ้ากดสวิตช์วันนี้ ใช้ค่าที่กด · ไม่งั้นใช้ตามวันทำงาน
create or replace function pp_hk_on(s hk_staff) returns boolean language sql stable as $$
  select case when s.ovr_day = pp_today() and s.ovr_on is not null then s.ovr_on else pp_hk_sched(s.days) end
$$;

create or replace function pp_hk_pick(p_room text) returns text language sql stable as $$
  select s.name from hk_staff s
  where not s.deleted and pp_hk_on(s)
    and (case when s.rooms is not null and jsonb_array_length(s.rooms) > 0 then s.rooms ? p_room
              else s.zones ? (case when left(p_room, 1) = 'C' then 'บ้านหลัง' else 'ตึกใหม่' end) end)
  order by (select count(*) from hk_task t where t.who = s.name and t.st < 3 and not t.deleted), s.sort, s.name
  limit 1
$$;

-- p = {k, ...}
--   staff_save {id, name, zones[], rooms[]|null, line_key, sort, days[]|null, ovr: true|false|null}
--              (รุ่นเก่าส่ง on: true/false → ถือเป็นการกดสวิตช์วันนี้)
--   staff_del  {id, to} · group_set {value}
--   task_new {room, kind, who?, note?} · task_from_booking {no} · task_upd {id, st?, who?, note?} · task_del {id} · task_cancel_out {room}
create or replace function pp_hk(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  t hk_task;
  v_who text;
  v_days jsonb;
  v_ovr boolean;
begin
  if k = 'staff_save' then
    if btrim(coalesce(p->>'name', '')) = '' then raise exception 'กรุณาพิมพ์ชื่อแม่บ้าน'; end if;
    if exists (select 1 from hk_staff where not deleted and name = btrim(p->>'name') and id <> p->>'id') then
      raise exception 'มีชื่อนี้แล้ว';
    end if;
    if p ? 'days' then
      v_days := case when jsonb_typeof(p->'days') = 'array' then p->'days' else null end;
      if v_days is not null and exists (select 1 from jsonb_array_elements(v_days) e
           where jsonb_typeof(e) <> 'number' or (e::text)::int not between 0 and 6) then
        raise exception 'วันทำงานไม่ถูกต้อง';
      end if;
    else
      v_days := (select days from hk_staff where id = p->>'id');
    end if;
    if p ? 'ovr' then v_ovr := case when jsonb_typeof(p->'ovr') = 'boolean' then (p->>'ovr')::boolean else null end;
    elsif p ? 'on' then v_ovr := (p->>'on')::boolean;
    else v_ovr := (select case when ovr_day = pp_today() then ovr_on end from hk_staff where id = p->>'id');
    end if;
    if v_ovr is not null and v_ovr = pp_hk_sched(v_days) then v_ovr := null; end if;   -- ตรงกับตารางอยู่แล้ว ไม่ต้องจำ
    insert into hk_staff (id, name, on_duty, zones, rooms, line_key, sort, days, ovr_day, ovr_on)
    values (p->>'id', btrim(p->>'name'), coalesce(v_ovr, pp_hk_sched(v_days)), coalesce(p->'zones', '[]'::jsonb),
            case when jsonb_typeof(p->'rooms') = 'array' then p->'rooms' else null end, nullif(p->>'line_key', ''),
            coalesce((p->>'sort')::int, 0), v_days, case when v_ovr is not null then pp_today() end, v_ovr)
    on conflict (id) do update set name = excluded.name, on_duty = excluded.on_duty, zones = excluded.zones,
      rooms = excluded.rooms, line_key = excluded.line_key, sort = excluded.sort, days = excluded.days,
      ovr_day = excluded.ovr_day, ovr_on = excluded.ovr_on, deleted = false, updated_at = now();
    update hk_task set who = btrim(p->>'name'), updated_at = now()
    where who = coalesce(p->>'old_name', '') and p->>'old_name' is not null and p->>'old_name' <> btrim(p->>'name');
  elsif k = 'staff_del' then
    select name into v_who from hk_staff where id = p->>'id';
    update hk_staff set deleted = true, updated_at = now() where id = p->>'id';
    update hk_task set who = coalesce(p->>'to', ''), auto = false, updated_at = now()
    where who = v_who and st < 5 and not deleted;
  elsif k = 'group_set' then
    insert into hk_settings (key, value) values ('line_group', nullif(p->>'value', ''))
    on conflict (key) do update set value = excluded.value, updated_at = now();
  elsif k = 'task_new' then
    if coalesce(p->>'room', '') = '' then raise exception 'ไม่ระบุห้อง'; end if;
    select * into t from hk_task where room = p->>'room' and kind = coalesce(p->>'kind', 'out') and st < 5 and not deleted;
    if found then return jsonb_build_object('ok', true, 'id', t.id, 'who', t.who, 'existed', true); end if;
    v_who := coalesce(nullif(p->>'who', ''), pp_hk_pick(p->>'room'), '');
    insert into hk_task (room, kind, who, note, auto)
    values (p->>'room', coalesce(p->>'kind', 'out'), v_who, coalesce(p->>'note', ''), nullif(p->>'who', '') is null and v_who <> '')
    returning * into t;
    return jsonb_build_object('ok', true, 'id', t.id, 'who', t.who, 'auto', t.auto);
  elsif k = 'task_from_booking' then
    return pp_hk(jsonb_build_object('k', 'task_new', 'kind', 'out', 'note', 'สร้างอัตโนมัติจากเช็คเอาท์',
      'room', (select room_id from bookings where booking_no = p->>'no')), p_role);
  elsif k = 'task_upd' then
    update hk_task set
      st = coalesce((p->>'st')::int, st),
      t2 = case when p ? 'st' then (case when (p->>'st')::int >= 2 then coalesce(t2, now()) else null end) else t2 end,
      t3 = case when p ? 'st' then (case when (p->>'st')::int >= 3 then coalesce(t3, now()) else null end) else t3 end,
      who = coalesce(p->>'who', who),
      auto = case when p ? 'who' then false else auto end,
      note = coalesce(p->>'note', note),
      updated_at = now()
    where id = (p->>'id')::bigint and not deleted;
    if not found then raise exception 'ไม่พบงานนี้'; end if;
  elsif k = 'task_del' then
    update hk_task set deleted = true, updated_at = now() where id = (p->>'id')::bigint;
  elsif k = 'task_cancel_out' then
    update hk_task set deleted = true, updated_at = now()
    where room = p->>'room' and kind = 'out' and st = 1 and not deleted;
  else
    raise exception 'ไม่รู้จักคำสั่งงานแม่บ้าน: %', k;
  end if;
  return jsonb_build_object('ok', true);
end $$;

create or replace function pp_hk_state() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'staff', coalesce((select jsonb_agg(jsonb_build_object('id', s.id, 'name', s.name, 'on', pp_hk_on(s), 'zones', s.zones, 'rooms', s.rooms,
               'line_key', s.line_key, 'sort', s.sort, 'days', s.days,
               'ovr', case when s.ovr_day = pp_today() then s.ovr_on end) order by s.sort, s.name)
             from hk_staff s where not s.deleted), '[]'::jsonb),
    'has_staff', exists (select 1 from hk_staff),
    'group', (select value from hk_settings where key = 'line_group'),
    'tasks', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'room', room, 'kind', kind, 'who', who, 'st', st,
               't2', t2, 't3', t3, 'note', note, 'auto', auto, 'day', day) order by id) from hk_task
             where not deleted and (st < 5 or day >= (now() at time zone 'Asia/Bangkok')::date)), '[]'::jsonb))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_hk', 'pp_hk_pick', 'pp_hk_state', 'pp_hk_sched', 'pp_hk_on') loop
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
