-- PROMPT PAK · ลูกค้าจองเองผ่าน LINE (หน้าจอเด้ง LIFF) + ส่งสลิปในแชท
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้) · ต้องรัน 17_insight.sql ก่อน
begin;

-- ช่องทางใหม่: line = ลูกค้าจองเองผ่านหน้าจอเด้งใน LINE
alter table bookings drop constraint if exists bookings_created_by_check;
alter table bookings add constraint bookings_created_by_check check (created_by in ('ai', 'staff', 'seed', 'line'));

-- เลข/รูปบัตรที่ลูกค้าส่งตอนจอง (ยินยอมแล้ว) · รูปลบอัตโนมัติ 90 วันหลังเช็คเอาท์
create table if not exists guest_docs (
  id           bigserial primary key,
  line_user_id text not null,
  booking_nos  jsonb not null,
  doc_no       text not null,
  img          text,
  consent_at   timestamptz not null,
  delete_after date not null,
  created_at   timestamptz not null default now()
);
alter table guest_docs enable row level security;

create or replace function pp_doc_purge() returns int language plpgsql as $$
declare n int;
begin
  update guest_docs set img = null where img is not null and delete_after < pp_today();
  get diagnostics n = row_count;
  return n;
end $$;

-- p = {line_user_id, line_name, name, phone, check_in, check_out, adults, kids, purpose, email,
--      items:[{zone, room_type, count, bf}], doc_no, img, consent, tax:{name,id,addr,hq,branch}|null}
create or replace function pp_liff_book(p jsonb) returns jsonb language plpgsql as $$
declare
  v_bf int := coalesce((p->>'bf_price')::int, 170);
  v_items jsonb := coalesce(p->'items', '[]');
  v_rooms int := (select coalesce(sum((x->>'count')::int), 0) from jsonb_array_elements(v_items) x);
  v_adults int := greatest(1, coalesce((p->>'adults')::int, 1));
  v_kids int := greatest(0, coalesce((p->>'kids')::int, 0));
  v_pax int; v_doc text := regexp_replace(coalesce(p->>'doc_no', ''), '\D', '', 'g');
  r jsonb; b jsonb; v_nos jsonb := '[]'; i int := 0; v_share int; v_bfon boolean; v_total int := 0; v_n int;
begin
  if v_rooms < 1 then raise exception 'กรุณาเลือกห้องพักอย่างน้อย 1 ห้อง'; end if;
  if v_rooms > 4 then raise exception 'จองผ่าน LINE ได้ครั้งละไม่เกิน 4 ห้อง ถ้าต้องการมากกว่านี้ พิมพ์บอกในแชทได้เลย พนักงานจะช่วยจองให้'; end if;
  if v_doc !~ '^[0-9]{13}$' then raise exception 'เลขบัตรประชาชนต้องมี 13 หลัก'; end if;
  if not coalesce((p->>'consent')::boolean, false) then raise exception 'กรุณายินยอมการเก็บข้อมูลบัตรก่อนยืนยัน'; end if;
  v_pax := v_adults + v_kids;
  r := pp_book(jsonb_build_object('guest_name', p->>'name', 'phone', p->>'phone', 'check_in', p->>'check_in', 'check_out', p->>'check_out',
        'items', v_items, 'created_by', 'line', 'channel', 'LINE OA', 'line_user_id', p->>'line_user_id',
        'line_display_name', p->>'line_name', 'company', nullif(p->'tax'->>'name', '')));
  v_n := jsonb_array_length(r->'bookings');
  for b in select * from jsonb_array_elements(r->'bookings') loop
    v_share := greatest(1, v_pax / v_n + case when i < v_pax % v_n then 1 else 0 end);
    v_bfon := coalesce((select (x->>'bf')::boolean from jsonb_array_elements(v_items) x
                        where x->>'room_type' = b->>'room_type' and coalesce(x->>'zone', b->>'zone') = b->>'zone' limit 1), false);
    update bookings set details = jsonb_build_object(
        'adults', v_adults, 'kids', v_kids, 'pax', v_share, 'purpose', coalesce(p->>'purpose', ''), 'email', coalesce(p->>'email', ''),
        'bf', case when v_bfon then v_bf * v_share * (r->>'nights')::int else 0 end, 'disc', 0, 'pay', 'later', 'liff', true,
        'doc_last4', right(v_doc, 4),
        'tax', case when p->'tax' is not null and jsonb_typeof(p->'tax') = 'object' and coalesce(p->'tax'->>'name', '') <> ''
                    then jsonb_build_object('type', 'บริษัท / นิติบุคคล', 'name', p->'tax'->>'name', 'id', regexp_replace(coalesce(p->'tax'->>'id', ''), '\D', '', 'g'),
                                            'addr', p->'tax'->>'addr', 'hq', coalesce(p->'tax'->>'hq', 'สำนักงานใหญ่'), 'branch', p->'tax'->>'branch') end)
      where booking_no = b->>'booking_no'
      returning room_total + coalesce((details->>'bf')::int, 0) into v_n;
    v_total := v_total + v_n;
    v_n := jsonb_array_length(r->'bookings');
    v_nos := v_nos || to_jsonb(b->>'booking_no');
    i := i + 1;
  end loop;
  insert into guest_docs (line_user_id, booking_nos, doc_no, img, consent_at, delete_after)
  values (p->>'line_user_id', v_nos, v_doc, nullif(p->>'img', ''), now(), (r->>'check_out')::date + 90);
  perform pp_doc_purge();
  return r || jsonb_build_object('nos', v_nos, 'total', v_total);
end $$;

-- ยอดที่ต้องชำระของการจองชุดนี้ (ใช้ทำ QR พร้อมเพย์)
create or replace function pp_liff_due(p_no text) returns jsonb language sql stable as $$
  with g as (select coalesce(group_no, booking_no) k from bookings where booking_no = p_no),
  bs as (select b.* from bookings b, g where coalesce(b.group_no, b.booking_no) = g.k and b.status <> 'ยกเลิก')
  select jsonb_build_object('no', p_no, 'total', (select coalesce(sum(room_total + coalesce((details->>'bf')::int, 0)), 0) from bs),
    'paid', exists (select 1 from ops o join bs on bs.booking_no = o.booking_no where o.kind = 'pay' and not o.undone))
$$;

-- ลูกค้าส่งรูปในแชท: ถ้ามีการจองผ่าน LINE ที่ยังไม่ชำระ ถือเป็นสลิป → บันทึกชำระ (ป้าย "สลิปยังไม่ตรวจ")
create or replace function pp_liff_slip(p_line_user_id text, p_url text) returns jsonb language plpgsql as $$
declare v_nos jsonb := '[]'; b bookings; v_total int := 0; v_amt int;
begin
  for b in
    select bk.* from bookings bk join guests g on g.id = bk.guest_id
    where g.line_user_id = p_line_user_id and bk.created_by = 'line' and bk.status <> 'ยกเลิก' and bk.check_out >= pp_today()
      and not exists (select 1 from ops o where o.booking_no = bk.booking_no and o.kind = 'pay' and not o.undone)
      and coalesce(bk.group_no, bk.booking_no) = (
        select coalesce(x.group_no, x.booking_no) from bookings x join guests gx on gx.id = x.guest_id
        where gx.line_user_id = p_line_user_id and x.created_by = 'line' and x.status <> 'ยกเลิก' and x.check_out >= pp_today()
          and not exists (select 1 from ops o2 where o2.booking_no = x.booking_no and o2.kind = 'pay' and not o2.undone)
        order by x.created_at desc limit 1)
  loop
    v_amt := b.room_total + coalesce((b.details->>'bf')::int, 0);
    insert into ops (role, kind, booking_no, data)
    values ('staff', 'pay', b.booking_no, jsonb_build_object('m', 'transfer', 'room_amt', v_amt, 'slip', p_url, 'unchecked', true, 'by', 'line'));
    update bookings set note = concat_ws(' · ', nullif(note, ''), 'สลิปยังไม่ตรวจ') where booking_no = b.booking_no;
    v_nos := v_nos || to_jsonb(b.booking_no); v_total := v_total + v_amt;
  end loop;
  return jsonb_build_object('matched', jsonb_array_length(v_nos) > 0, 'nos', v_nos, 'total', v_total);
end $$;

-- การจองผ่าน LINE ที่ยังไม่ส่งสลิปเกิน 24 ชม. → ขึ้นเตือนพนักงานในแชท (ไม่ยกเลิกเอง)
create or replace function pp_liff_overdue() returns int language plpgsql as $$
declare n int := 0; t record;
begin
  for t in
    select distinct g.line_user_id from bookings bk join guests g on g.id = bk.guest_id
    where bk.created_by = 'line' and bk.status <> 'ยกเลิก' and bk.created_at < now() - interval '24 hours' and bk.check_out >= pp_today()
      and not exists (select 1 from ops o where o.booking_no = bk.booking_no and o.kind = 'pay' and not o.undone)
      and coalesce(bk.note, '') not like '%ยังไม่ส่งสลิปเกิน 24 ชม.%'
  loop
    perform pp_handoff(t.line_user_id, 'การจองผ่าน LINE ยังไม่ส่งสลิปเกิน 24 ชม. · ตัดสินใจยกเลิกหรือติดตาม');
    update bookings bk set note = concat_ws(' · ', nullif(bk.note, ''), 'ยังไม่ส่งสลิปเกิน 24 ชม.')
    from guests g where g.id = bk.guest_id and g.line_user_id = t.line_user_id and bk.created_by = 'line' and bk.status <> 'ยกเลิก'
      and not exists (select 1 from ops o where o.booking_no = bk.booking_no and o.kind = 'pay' and not o.undone);
    n := n + 1;
  end loop;
  return n;
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_doc_purge', 'pp_liff_book', 'pp_liff_due', 'pp_liff_slip', 'pp_liff_overdue') loop
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
