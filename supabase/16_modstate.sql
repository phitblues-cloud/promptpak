-- PROMPT PAK · เมนูที่เหลือบันทึกจริง: แม่บ้าน (ของที่พบ/แจ้งลืม/แจ้งซ่อม) · เครื่องมือ CRM (ดีล/ลีด/ข้อความอัตโนมัติ/ตั้งค่า LINE/โปรบริษัท)
--   · การตลาด (แคมเปญ/แผน/Google) · โปรโมชั่นพาร์ทเนอร์ของบริษัท · ยืนยันจุดยืน (STP)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้) · ต้องรัน 15_fin.sql ก่อน
begin;

create table if not exists mod_state (
  k          text primary key,
  data       jsonb not null default '{}'::jsonb,
  by_role    text,
  updated_at timestamptz not null default now()
);
alter table mod_state enable row level security;

create or replace function pp_mod_save(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare v_k text := p->>'k';
begin
  if v_k is null or v_k not in ('hk', 'crmtool', 'cust', 'crm', 'mkt', 'stp') then raise exception 'ไม่รู้จักเมนู %', v_k; end if;
  if jsonb_typeof(p->'data') <> 'object' then raise exception 'ข้อมูลไม่ถูกต้อง'; end if;
  if length((p->'data')::text) > 3000000 then raise exception 'ข้อมูลใหญ่เกินไป (รูปเยอะเกิน)'; end if;
  insert into mod_state (k, data, by_role) values (v_k, p->'data', p_role)
  on conflict (k) do update set data = excluded.data, by_role = excluded.by_role, updated_at = now();
  return jsonb_build_object('ok', true);
end $$;

create or replace function pp_mod_state() returns jsonb language sql stable as $$
  select coalesce(jsonb_object_agg(k, data), '{}'::jsonb) from mod_state
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
    (select coalesce(max(updated_at)::text, '') from hk_settings),
    (select coalesce(max(updated_at)::text, '') from fin_state),
    (select coalesce(max(updated_at)::text, '') from mod_state))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_mod_save', 'pp_mod_state', 'pp_stamp') loop
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
