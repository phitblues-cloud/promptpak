-- PROMPT PAK · แม่บ้าน: รายชื่อ/โซน/ห้องที่รับผิดชอบ/LINE + งานทำความสะอาดบันทึกจริง + มอบหมายอัตโนมัติ
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

create table if not exists hk_staff (
  id         text primary key,                      -- H...
  name       text not null,
  on_duty    boolean not null default true,         -- ทำงานวันนี้
  zones      jsonb not null default '[]'::jsonb,    -- ["ตึกใหม่","บ้านหลัง"]
  rooms      jsonb,                                 -- null = ทุกห้องในโซนที่เลือก · ["A01","A02"] = เฉพาะห้อง
  line_key   text,                                  -- แชท LINE ของแม่บ้าน (db:<thread id>)
  sort       int not null default 0,
  deleted    boolean not null default false,
  updated_at timestamptz not null default now()
);
alter table hk_staff enable row level security;

create table if not exists hk_settings (
  key        text primary key,
  value      text,
  updated_at timestamptz not null default now()
);
alter table hk_settings enable row level security;

create table if not exists hk_task (
  id          bigserial primary key,
  day         date not null default ((now() at time zone 'Asia/Bangkok')::date),
  room        text not null,
  kind        text not null default 'out' check (kind in ('out', 'stay', 'arrive', 'other')),
  who         text not null default '',             -- ชื่อแม่บ้าน
  st          int not null default 1 check (st between 1 and 5),
  t2          timestamptz,                          -- เริ่มทำ
  t3          timestamptz,                          -- ทำเสร็จ
  note        text not null default '',
  auto        boolean not null default false,       -- ระบบมอบหมายให้อัตโนมัติ
  deleted     boolean not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create unique index if not exists hk_task_open on hk_task (room, kind) where st < 5 and not deleted;
alter table hk_task enable row level security;

-- แม่บ้านที่ควรรับห้องนี้: ทำงานวันนี้ + ห้องอยู่ในความรับผิดชอบ · ถ้ามีหลายคน เลือกคนที่มีงานค้างน้อยที่สุด
create or replace function pp_hk_pick(p_room text) returns text language sql stable as $$
  select s.name from hk_staff s
  where not s.deleted and s.on_duty
    and (case when s.rooms is not null and jsonb_array_length(s.rooms) > 0 then s.rooms ? p_room
              else s.zones ? (case when left(p_room, 1) = 'C' then 'บ้านหลัง' else 'ตึกใหม่' end) end)
  order by (select count(*) from hk_task t where t.who = s.name and t.st < 3 and not t.deleted), s.sort, s.name
  limit 1
$$;

-- p = {k, ...}
--   staff_save {id, name, on, zones[], rooms[]|null, line_key, sort}
--   staff_del  {id, to}           (โอนงานค้างให้ชื่อ to หรือ '' = ยังไม่มอบหมาย)
--   group_set  {value}
--   task_new   {room, kind, who?, note?}   → ถ้ามีงานเปิดของห้อง+ประเภทนี้อยู่แล้ว คืนงานเดิม
--   task_upd   {id, st?, who?, note?}
--   task_del   {id}
--   task_cancel_out {room}        (ยกเลิกการเช็คเอาท์ → ลบงานหลังเช็คเอาท์ที่ยังไม่เริ่ม)
create or replace function pp_hk(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  t hk_task;
  v_who text;
begin
  if k = 'staff_save' then
    if btrim(coalesce(p->>'name', '')) = '' then raise exception 'กรุณาพิมพ์ชื่อแม่บ้าน'; end if;
    if exists (select 1 from hk_staff where not deleted and name = btrim(p->>'name') and id <> p->>'id') then
      raise exception 'มีชื่อนี้แล้ว';
    end if;
    insert into hk_staff (id, name, on_duty, zones, rooms, line_key, sort)
    values (p->>'id', btrim(p->>'name'), coalesce((p->>'on')::boolean, true), coalesce(p->'zones', '[]'::jsonb),
            case when jsonb_typeof(p->'rooms') = 'array' then p->'rooms' else null end, nullif(p->>'line_key', ''),
            coalesce((p->>'sort')::int, 0))
    on conflict (id) do update set name = excluded.name, on_duty = excluded.on_duty, zones = excluded.zones,
      rooms = excluded.rooms, line_key = excluded.line_key, sort = excluded.sort, deleted = false, updated_at = now();
    -- เปลี่ยนชื่อ → งานเดิมตามชื่อใหม่
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
  elsif k = 'task_from_booking' then   -- เช็คเอาท์จากหน้าแรก → สร้างงานทำความสะอาดของห้องนั้น
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

-- ข้อมูลสำหรับหน้าจอ: รายชื่อแม่บ้าน + กลุ่ม LINE + งานที่ยังไม่เสร็จ และงานที่เสร็จวันนี้
create or replace function pp_hk_state() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'staff', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'name', name, 'on', on_duty, 'zones', zones, 'rooms', rooms,
               'line_key', line_key, 'sort', sort) order by sort, name) from hk_staff where not deleted), '[]'::jsonb),
    'has_staff', exists (select 1 from hk_staff),
    'group', (select value from hk_settings where key = 'line_group'),
    'tasks', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'room', room, 'kind', kind, 'who', who, 'st', st,
               't2', t2, 't3', t3, 'note', note, 'auto', auto, 'day', day) order by id) from hk_task
             where not deleted and (st < 5 or day >= (now() at time zone 'Asia/Bangkok')::date)), '[]'::jsonb))
$$;

create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed),
    (select md5(string_agg(id || room_type || rate || max_guests || active::text, ',' order by id)) from rooms),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from chat_state),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from cust_state),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') || '/' || count(img) from cust_id),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from comp_state),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from hk_task),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from hk_staff),
    (select coalesce(max(updated_at)::text, '') from hk_settings))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_hk', 'pp_hk_pick', 'pp_hk_state', 'pp_stamp') loop
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
