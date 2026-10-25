-- PROMPT PAK · บัตรประชาชน / หนังสือเดินทางของลูกค้า (ทะเบียนผู้พักตาม พ.ร.บ.โรงแรม + PDPA)
-- เลขเอกสาร: เก็บเพื่อทะเบียนผู้พักตามกฎหมาย · ภาพบัตร: เก็บเมื่อลูกค้ายินยอมเท่านั้น และลบอัตโนมัติ 1 ปีหลังเข้าพักครั้งล่าสุด
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

create table if not exists cust_id (
  gid        text primary key,              -- รหัสลูกค้า (เหมือน cust_state)
  doc_type   text not null check (doc_type in ('id', 'passport')),
  doc_no     text not null,
  img        text,                          -- ภาพบัตร (data URL ย่อขนาดแล้ว) · มีได้เฉพาะเมื่อยินยอม
  consent_at timestamptz,                   -- เวลาที่พนักงานติ๊กว่าลูกค้ายินยอมให้เก็บภาพ
  consent_by text,                          -- owner / staff
  img_at     timestamptz,                   -- เวลาที่บันทึกภาพ
  updated_at timestamptz not null default now()
);
alter table cust_id enable row level security;

-- p = {gid, doc_type, doc_no, img?: data URL | '' (ลบภาพ) | ไม่ส่ง (คงเดิม), consent?: true}
create or replace function pp_cust_id(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  v_gid text := nullif(btrim(coalesce(p->>'gid', '')), '');
  v_type text := coalesce(p->>'doc_type', 'id');
  v_no text := upper(regexp_replace(coalesce(p->>'doc_no', ''), '[^0-9A-Za-z]', '', 'g'));
  v_img text := p->>'img';
  v_consent boolean := coalesce((p->>'consent')::boolean, false);
begin
  if v_gid is null then raise exception 'ไม่ระบุลูกค้า'; end if;
  if v_type not in ('id', 'passport') then raise exception 'ประเภทเอกสารไม่ถูกต้อง'; end if;
  if v_type = 'id' and v_no !~ '^[0-9]{13}$' then raise exception 'เลขบัตรประชาชนต้องมี 13 หลัก'; end if;
  if v_type = 'passport' and v_no !~ '^[0-9A-Z]{6,12}$' then raise exception 'เลขหนังสือเดินทางไม่ถูกต้อง'; end if;
  if v_img is not null and v_img <> '' then
    if not v_consent then raise exception 'ต้องติ๊กว่าลูกค้ายินยอมก่อนเก็บภาพบัตร'; end if;
    if v_img !~ '^data:image/(jpeg|png|webp);base64,' then raise exception 'ไฟล์ภาพไม่ถูกต้อง'; end if;
    if length(v_img) > 600000 then raise exception 'ภาพใหญ่เกินไป'; end if;
  end if;
  insert into cust_id (gid, doc_type, doc_no) values (v_gid, v_type, v_no)
  on conflict (gid) do update set doc_type = excluded.doc_type, doc_no = excluded.doc_no, updated_at = now();
  if v_img = '' then
    update cust_id set img = null, img_at = null, consent_at = null, consent_by = null where gid = v_gid;
  elsif v_img is not null then
    update cust_id set img = v_img, img_at = now(), consent_at = now(), consent_by = p_role where gid = v_gid;
  end if;
  return jsonb_build_object('ok', true);
end $$;

-- รายการเอกสาร (ไม่ส่งภาพ) — หน้าจอปิดเลขบางส่วนให้พนักงานเอง
create or replace function pp_cust_ids() returns jsonb language sql stable as $$
  select coalesce(jsonb_object_agg(gid, jsonb_build_object('t', doc_type, 'no', doc_no, 'img', img is not null,
           'ca', consent_at, 'cb', consent_by)), '{}'::jsonb) from cust_id
$$;

create or replace function pp_cust_id_img(p_gid text) returns text language sql stable as $$
  select img from cust_id where gid = p_gid
$$;

-- ลบภาพบัตรที่เก็บเกิน 1 ปี ของลูกค้าที่ไม่ได้เข้าพักภายใน 1 ปี (p_keep = รหัสลูกค้าที่ยังเข้าพักภายใน 1 ปีหรือมีการจองล่วงหน้า)
create or replace function pp_id_purge(p_keep jsonb) returns int language plpgsql as $$
declare n int;
begin
  update cust_id set img = null, img_at = null
  where img is not null and img_at < now() - interval '365 days'
    and not (gid in (select jsonb_array_elements_text(coalesce(p_keep, '[]'::jsonb))));
  get diagnostics n = row_count;
  return n;
end $$;

-- ตัวบอกว่าข้อมูลเปลี่ยน — เพิ่มเอกสารลูกค้า
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
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') || '/' || count(img) from cust_id))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_cust_id', 'pp_cust_ids', 'pp_cust_id_img', 'pp_id_purge', 'pp_stamp') loop
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
