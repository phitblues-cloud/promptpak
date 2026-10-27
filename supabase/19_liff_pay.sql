-- PROMPT PAK · จองผ่าน LINE: ลูกค้าเลือกวิธีชำระ (ชำระทันที = QR พร้อมเพย์ / ชำระวันเข้าพัก = จ่ายที่เคาน์เตอร์)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้) · ต้องรัน 18_liff.sql ก่อน
begin;

-- บันทึกวิธีชำระที่ลูกค้าเลือกลงในรายละเอียดการจอง (เรียกหลัง pp_liff_book)
create or replace function pp_liff_setpay(p_nos jsonb, p_pay text) returns void language sql as $$
  update bookings set details = coalesce(details, '{}'::jsonb) || jsonb_build_object('liff_pay', case when p_pay = 'arrival' then 'arrival' else 'now' end),
    note = case when p_pay = 'arrival' then concat_ws(' · ', nullif(note, ''), 'ชำระวันเข้าพัก') else note end
  where booking_no in (select jsonb_array_elements_text(p_nos))
$$;

-- รูปในแชท = สลิป เฉพาะการจองที่เลือก "ชำระทันที"
create or replace function pp_liff_slip(p_line_user_id text, p_url text) returns jsonb language plpgsql as $$
declare v_nos jsonb := '[]'; b bookings; v_total int := 0; v_amt int;
begin
  for b in
    select bk.* from bookings bk join guests g on g.id = bk.guest_id
    where g.line_user_id = p_line_user_id and bk.created_by = 'line' and bk.status <> 'ยกเลิก' and bk.check_out >= pp_today()
      and coalesce(bk.details->>'liff_pay', 'now') = 'now'
      and not exists (select 1 from ops o where o.booking_no = bk.booking_no and o.kind = 'pay' and not o.undone)
      and coalesce(bk.group_no, bk.booking_no) = (
        select coalesce(x.group_no, x.booking_no) from bookings x join guests gx on gx.id = x.guest_id
        where gx.line_user_id = p_line_user_id and x.created_by = 'line' and x.status <> 'ยกเลิก' and x.check_out >= pp_today()
          and coalesce(x.details->>'liff_pay', 'now') = 'now'
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

-- เตือนสลิปค้าง 24 ชม. เฉพาะ "ชำระทันที"
create or replace function pp_liff_overdue() returns int language plpgsql as $$
declare n int := 0; t record;
begin
  for t in
    select distinct g.line_user_id from bookings bk join guests g on g.id = bk.guest_id
    where bk.created_by = 'line' and bk.status <> 'ยกเลิก' and bk.created_at < now() - interval '24 hours' and bk.check_out >= pp_today()
      and coalesce(bk.details->>'liff_pay', 'now') = 'now'
      and not exists (select 1 from ops o where o.booking_no = bk.booking_no and o.kind = 'pay' and not o.undone)
      and coalesce(bk.note, '') not like '%ยังไม่ส่งสลิปเกิน 24 ชม.%'
  loop
    perform pp_handoff(t.line_user_id, 'การจองผ่าน LINE ยังไม่ส่งสลิปเกิน 24 ชม. · ตัดสินใจยกเลิกหรือติดตาม');
    update bookings bk set note = concat_ws(' · ', nullif(bk.note, ''), 'ยังไม่ส่งสลิปเกิน 24 ชม.')
    from guests g where g.id = bk.guest_id and g.line_user_id = t.line_user_id and bk.created_by = 'line' and bk.status <> 'ยกเลิก'
      and coalesce(bk.details->>'liff_pay', 'now') = 'now'
      and not exists (select 1 from ops o where o.booking_no = bk.booking_no and o.kind = 'pay' and not o.undone);
    n := n + 1;
  end loop;
  return n;
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_liff_setpay', 'pp_liff_slip', 'pp_liff_overdue') loop
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
