-- PROMPT PAK · หน้าแชทลูกค้า LINE บันทึกจริง: ส่งข้อความ / ปิดเคส / เปลี่ยนชื่อแชท / หมายเหตุ / อ่านแล้ว
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

-- สถานะที่พนักงานตั้งให้แต่ละแชท (ทั้งแชทจริงจาก LINE และแชทตัวอย่าง)
-- key: แชทจริง = 'db:<chat_threads.id>' · แชทตัวอย่าง = รหัสแชทในข้อมูลตัวอย่าง เช่น 'T0001'
create table if not exists chat_state (
  key        text primary key,
  alias      text,                                   -- ชื่อแชทที่พนักงานตั้งเอง
  notes      jsonb not null default '[]'::jsonb,     -- หมายเหตุ
  closed_at  timestamptz,                            -- ปิดเคสล่าสุด
  read_at    timestamptz,                            -- เปิดอ่านล่าสุด
  sent       jsonb not null default '[]'::jsonb,     -- ข้อความที่พนักงานพิมพ์ในแชทตัวอย่าง (ไม่ได้ส่งเข้า LINE)
  updated_at timestamptz not null default now()
);
alter table chat_state enable row level security;

-- LINE user id ของแชทจริง (ใช้ตอนส่งข้อความเข้า LINE) · แชทตัวอย่างคืน null
create or replace function pp_chat_target(p_key text) returns text language sql stable as $$
  select t.line_user_id from chat_threads t
  where p_key like 'db:%' and t.id = nullif(substr(p_key, 4), '')::bigint and not t.is_seed
$$;

-- p = {k: send|close|name|notes|read, key, body?, alias?, notes?, line?}
create or replace function pp_chat(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  v_key text := nullif(p->>'key', '');
  v_tid bigint;
  v_body text := btrim(coalesce(p->>'body', ''));
begin
  if k is null or v_key is null then raise exception 'ข้อมูลแชทไม่ครบ'; end if;
  if v_key like 'db:%' then
    v_tid := nullif(substr(v_key, 4), '')::bigint;
    if not exists (select 1 from chat_threads where id = v_tid) then raise exception 'ไม่พบแชทนี้'; end if;
  end if;
  insert into chat_state (key) values (v_key) on conflict (key) do nothing;

  if k = 'send' then
    if v_body = '' then raise exception 'ข้อความว่าง'; end if;
    if v_tid is not null then
      insert into chat_messages (thread_id, sender, body, meta)
      values (v_tid, 'พนักงาน', v_body, jsonb_build_object('by', p_role, 'line', coalesce(p->>'line', 'sent')));
      update chat_threads set needs_staff = false, handoff_reason = null, last_message_at = now() where id = v_tid;
    else
      update chat_state set sent = sent || jsonb_build_array(jsonb_build_object('body', v_body, 'at', now(), 'by', p_role))
      where key = v_key;
    end if;
    update chat_state set read_at = now(), updated_at = now() where key = v_key;
  elsif k = 'close' then
    if v_tid is not null then
      update chat_threads set needs_staff = false, handoff_reason = null where id = v_tid;
    end if;
    update chat_state set closed_at = now(), read_at = now(), updated_at = now() where key = v_key;
  elsif k = 'name' then
    update chat_state set alias = nullif(btrim(coalesce(p->>'alias', '')), ''), updated_at = now() where key = v_key;
  elsif k = 'notes' then
    if jsonb_typeof(p->'notes') <> 'array' then raise exception 'หมายเหตุไม่ถูกต้อง'; end if;
    update chat_state set notes = p->'notes', updated_at = now() where key = v_key;
  elsif k = 'read' then
    update chat_state set read_at = now(), updated_at = now() where key = v_key;
  else
    raise exception 'ไม่รู้จักคำสั่งแชท: %', k;
  end if;
  return jsonb_build_object('ok', true);
end $$;

create or replace function pp_chat_state() returns jsonb language sql stable as $$
  select coalesce(jsonb_object_agg(key, jsonb_build_object('alias', alias, 'notes', notes, 'closed_at', closed_at,
           'read_at', read_at, 'sent', sent)), '{}'::jsonb) from chat_state
$$;

-- ตัวบอกว่าข้อมูลเปลี่ยน (หน้าจอทุกเครื่องจะดึงข้อมูลใหม่) — เพิ่มสถานะแชท
create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed),
    (select md5(string_agg(id || room_type || rate || max_guests || active::text, ',' order by id)) from rooms),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from chat_state))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_chat', 'pp_chat_target', 'pp_chat_state', 'pp_stamp') loop
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
