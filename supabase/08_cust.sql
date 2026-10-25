-- PROMPT PAK · ลูกค้าและสมาชิก บันทึกจริง: แก้ไขข้อมูล / เพศ / ผูก-ลบบริษัท / สมัครสมาชิก
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

-- ข้อมูลลูกค้าที่พนักงานแก้ในโมดูลลูกค้า (ทับข้อมูลเดิม) และลูกค้าใหม่ที่สมัครสมาชิก
-- gid: รหัสลูกค้าในระบบ (เช่น G0012) หรือรหัสลูกค้าใหม่ที่สร้างตอนสมัคร (N...)
-- ไม่เก็บเลข/ภาพบัตรประชาชน (รอขั้นยินยอมตาม PDPA)
create table if not exists cust_state (
  gid        text primary key,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table cust_state enable row level security;

-- p = {k: edit|company|member, gid, data?, company?, base?, is_new?}
create or replace function pp_cust(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  v_gid text := nullif(btrim(coalesce(p->>'gid', '')), '');
  v_in jsonb := coalesce(p->'data', '{}'::jsonb);
  v_d jsonb := '{}'::jsonb;
  v_seq int; v_no text;
  f text;
begin
  if k is null or v_gid is null then raise exception 'ข้อมูลลูกค้าไม่ครบ'; end if;
  if jsonb_typeof(v_in) <> 'object' then raise exception 'ข้อมูลลูกค้าไม่ถูกต้อง'; end if;
  -- รับเฉพาะช่องที่อนุญาต
  foreach f in array array['name','phone','line','addr','prov','bday','special','gender','purpose'] loop
    if v_in ? f then v_d := v_d || jsonb_build_object(f, left(btrim(coalesce(v_in->>f, '')), 300)); end if;
  end loop;
  if v_d ? 'gender' and v_d->>'gender' not in ('', 'ชาย', 'หญิง', 'เพศหลากหลาย', 'ไม่ระบุ') then
    raise exception 'เพศไม่ถูกต้อง';
  end if;
  if v_d ? 'name' and v_d->>'name' = '' then raise exception 'กรุณากรอกชื่อ-สกุล'; end if;
  insert into cust_state (gid) values (v_gid) on conflict (gid) do nothing;

  if k = 'edit' then
    update cust_state set data = data || v_d, updated_at = now() where gid = v_gid;
  elsif k = 'company' then
    update cust_state set data = data || jsonb_build_object('company', coalesce(p->>'company', '')), updated_at = now()
    where gid = v_gid;
  elsif k = 'member' then
    if exists (select 1 from cust_state where gid = v_gid and data ? 'memberNo') then
      raise exception 'ลูกค้าท่านนี้เป็นสมาชิกอยู่แล้ว';
    end if;
    select greatest(coalesce((p->>'base')::int, 0), coalesce(max((data->>'memberSeq')::int), 0)) + 1 into v_seq
    from cust_state where data ? 'memberSeq';
    v_no := 'M' || lpad(v_seq::text, 3, '0');
    update cust_state set data = data || v_d || jsonb_build_object('memberNo', v_no, 'memberSeq', v_seq,
        'memberSince', to_char((now() at time zone 'Asia/Bangkok')::date, 'YYYY-MM-DD'))
      || case when coalesce((p->>'is_new')::boolean, false)
              then jsonb_build_object('is_new', true, 'company', coalesce(p->>'company', ''),
                                      'added', to_char((now() at time zone 'Asia/Bangkok')::date, 'YYYY-MM-DD'))
              else '{}'::jsonb end,
      updated_at = now()
    where gid = v_gid;
    return jsonb_build_object('ok', true, 'memberNo', v_no);
  else
    raise exception 'ไม่รู้จักคำสั่งลูกค้า: %', k;
  end if;
  return jsonb_build_object('ok', true);
end $$;

create or replace function pp_cust_state() returns jsonb language sql stable as $$
  select coalesce(jsonb_object_agg(gid, data), '{}'::jsonb) from cust_state
$$;

-- ตัวบอกว่าข้อมูลเปลี่ยน — เพิ่มข้อมูลลูกค้า
create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed),
    (select md5(string_agg(id || room_type || rate || max_guests || active::text, ',' order by id)) from rooms),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from chat_state),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from cust_state))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_cust', 'pp_cust_state', 'pp_stamp') loop
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
