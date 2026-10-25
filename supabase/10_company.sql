-- PROMPT PAK · เพิ่ม/แก้ไขข้อมูลบริษัท (แท็บบริษัท ในลูกค้าและสมาชิก)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

create table if not exists comp_state (
  cid        text primary key,              -- รหัสบริษัทใหม่ (K...) หรือรหัสบริษัทเดิมที่แก้ไข
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table comp_state enable row level security;

-- p = {cid, data: {name, short, type, site, tax, branch, addr, pay, credit, cname, crole, cphone, cemail, cline, cdecide}}
create or replace function pp_comp(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  v_cid text := nullif(btrim(coalesce(p->>'cid', '')), '');
  v_in jsonb := coalesce(p->'data', '{}'::jsonb);
  v_d jsonb := '{}'::jsonb;
  f text;
begin
  if v_cid is null then raise exception 'ไม่ระบุรหัสบริษัท'; end if;
  foreach f in array array['name','short','type','site','tax','branch','addr','pay','credit','cname','crole','cphone','cemail','cline','cdecide'] loop
    if v_in ? f then v_d := v_d || jsonb_build_object(f, left(btrim(coalesce(v_in->>f, '')), 300)); end if;
  end loop;
  if v_d ? 'name' and v_d->>'name' = '' then raise exception 'กรุณากรอกชื่อบริษัท'; end if;
  if not exists (select 1 from comp_state where cid = v_cid) and v_cid like 'K%' and coalesce(v_d->>'name', '') = '' then
    raise exception 'กรุณากรอกชื่อบริษัท';
  end if;
  if v_d ? 'type' and v_d->>'type' not in ('', 'เอกชน', 'หน่วยงานราชการ', 'รัฐวิสาหกิจ') then raise exception 'ประเภทธุรกิจไม่ถูกต้อง'; end if;
  if v_d ? 'pay' and v_d->>'pay' not in ('', 'self', 'prepay', 'credit') then raise exception 'วิธีชำระไม่ถูกต้อง'; end if;
  if v_d ? 'credit' and v_d->>'credit' !~ '^[0-9]{0,3}$' then raise exception 'จำนวนวันเครดิตไม่ถูกต้อง'; end if;
  if coalesce(v_d->>'tax', '') <> '' and v_d->>'tax' !~ '^[0-9]{13}$' then raise exception 'เลขผู้เสียภาษีต้องมี 13 หลัก'; end if;
  if coalesce(v_d->>'tax', '') <> '' and exists (select 1 from comp_state where cid <> v_cid and data->>'tax' = v_d->>'tax') then
    raise exception 'เลขผู้เสียภาษีนี้มีในระบบแล้ว';
  end if;
  insert into comp_state (cid, data) values (v_cid, v_d || jsonb_build_object('by', p_role))
  on conflict (cid) do update set data = comp_state.data || excluded.data, updated_at = now();
  return jsonb_build_object('ok', true, 'cid', v_cid);
end $$;

create or replace function pp_comp_state() returns jsonb language sql stable as $$
  select coalesce(jsonb_object_agg(cid, data), '{}'::jsonb) from comp_state
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
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from comp_state))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_comp', 'pp_comp_state', 'pp_stamp') loop
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
