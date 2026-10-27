-- PROMPT PAK · หน้ารายละเอียดการจองใน LINE (LIFF): ลูกค้าเปิดดูการจองของตัวเองจากการ์ดในแชท
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้) · ต้องรัน 18–20 ก่อน
begin;

-- คืนข้อมูลการจองทั้งชุด (กลุ่มเดียวกัน) เฉพาะเมื่อ LINE นี้เป็นเจ้าของการจองเท่านั้น · ไม่ส่งเลขบัตร/รูปบัตร
create or replace function pp_liff_detail(p_line_user_id text, p_no text) returns jsonb language sql stable as $$
  with g as (
    select coalesce(b.group_no, b.booking_no) k from bookings b join guests gu on gu.id = b.guest_id
    where b.booking_no = p_no and gu.line_user_id = p_line_user_id limit 1),
  bs as (
    select b.*, r.zone, r.room_type from bookings b join rooms r on r.id = b.room_id, g
    where coalesce(b.group_no, b.booking_no) = g.k order by b.booking_no)
  select case when not exists (select 1 from bs) then null else jsonb_build_object(
    'no', p_no,
    'nos', (select jsonb_agg(booking_no) from bs),
    'name', (select guest_name from bs limit 1),
    'check_in', (select min(check_in) from bs), 'check_out', (select max(check_out) from bs), 'nights', (select max(nights) from bs),
    'cancelled', not exists (select 1 from bs where status <> 'ยกเลิก'),
    'adults', (select coalesce((details->>'adults')::int, 1) from bs limit 1),
    'kids', (select coalesce((details->>'kids')::int, 0) from bs limit 1),
    'purpose', (select coalesce(details->>'purpose', '') from bs limit 1),
    'rooms', (select jsonb_agg(jsonb_build_object('room', room_id, 'zone', zone, 'type', room_type, 'rate', rate, 'nights', nights, 'amt', room_total,
                'bf', coalesce((details->>'bf')::int, 0)) order by booking_no) from bs where status <> 'ยกเลิก'),
    'room_total', (select coalesce(sum(room_total), 0) from bs where status <> 'ยกเลิก'),
    'bf_total', (select coalesce(sum(coalesce((details->>'bf')::int, 0)), 0) from bs where status <> 'ยกเลิก'),
    'dep_online', (select coalesce(sum(coalesce((details->>'liff_dep')::int, 0)), 0) from bs where status <> 'ยกเลิก'),
    'dep_each', (select coalesce(max(deposit), 200) from bs),
    'pay_mode', (select coalesce(details->>'liff_pay', 'now') from bs limit 1),
    'paid', exists (select 1 from ops o join bs on bs.booking_no = o.booking_no where o.kind = 'pay' and not o.undone),
    'slip_unchecked', exists (select 1 from ops o join bs on bs.booking_no = o.booking_no where o.kind = 'pay' and not o.undone and coalesce((o.data->>'unchecked')::boolean, false)),
    'created_at', (select min(created_at) from bs)) end
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname = 'pp_liff_detail' loop
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
