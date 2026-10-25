-- PROMPT PAK · แชท LINE: รับ/ส่ง รูปภาพ สติกเกอร์ ไฟล์ (ที่เก็บไฟล์ Supabase Storage ชื่อ chat)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

-- ที่เก็บรูป/ไฟล์ในแชท (ต้องเปิดสาธารณะ เพราะ LINE ต้องดึงรูปจากลิงก์ได้ · ชื่อไฟล์สุ่มเดาไม่ได้)
insert into storage.buckets (id, name, public, file_size_limit)
values ('chat', 'chat', true, 10485760)
on conflict (id) do update set public = true, file_size_limit = 10485760;

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
      values (v_tid, 'พนักงาน', v_body, jsonb_build_object('by', p_role, 'line', coalesce(p->>'line', 'sent')) || coalesce(p->'meta', '{}'::jsonb));
      update chat_threads set needs_staff = false, handoff_reason = null, last_message_at = now() where id = v_tid;
    else
      update chat_state set sent = sent || jsonb_build_array(jsonb_build_object('body', v_body, 'at', now(), 'by', p_role, 'meta', coalesce(p->'meta', '{}'::jsonb)))
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


-- ส่งข้อมูลแนบ (รูป/สติกเกอร์/ไฟล์) ของแต่ละข้อความไปหน้าจอด้วย
create or replace function pp_export() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'stamp', pp_stamp(),
    'bookings', coalesce((select jsonb_agg(to_jsonb(b) - 'id' order by b.booking_no) from bookings b), '[]'),
    'guests', coalesce((select jsonb_agg(to_jsonb(g)) from guests g), '[]'),
    'threads', coalesce((select jsonb_agg(jsonb_build_object('id', t.id, 'line_user_id', t.line_user_id,
        'display_name', t.display_name, 'needs_staff', t.needs_staff, 'is_seed', t.is_seed,
        'messages', (select coalesce(jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'at', created_at, 'meta', meta)
                       order by created_at, id), '[]') from chat_messages m where m.thread_id = t.id))
        order by t.id)
      from chat_threads t where not t.is_seed), '[]'),
    'ops', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'at', at, 'role', role, 'kind', kind,
        'no', booking_no, 'data', data) order by id) from ops where not undone), '[]'),
    'closed_rooms', coalesce((select jsonb_agg(id order by id) from rooms where closed), '[]'),
    'rooms', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'zone', zone, 'room_type', room_type, 'bed', bed,
        'rate', rate, 'max_guests', max_guests, 'floor', floor, 'closed', closed) order by id) from rooms where active), '[]'))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_chat', 'pp_export') loop
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
