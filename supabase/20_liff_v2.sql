-- PROMPT PAK · จองผ่าน LINE รอบ 2: ใช้ข้อมูลเดิม · จ่ายเงินประกันห้องพร้อมค่าห้อง · แนบสลิปในหน้าจอจอง
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้) · ต้องรัน 18_liff.sql และ 19_liff_pay.sql ก่อน
begin;

-- เงินประกันห้อง 200 บาท/ห้อง (เจ้าของยืนยัน 27 ต.ค.) · การจองที่ยังไม่รับเงินประกัน ปรับเป็น 200 ด้วย
alter table bookings alter column deposit set default 200;
update bookings b set deposit = 200
where deposit = 300 and status <> 'ยกเลิก' and check_out >= pp_today()
  and not exists (select 1 from ops o where o.booking_no = b.booking_no and not o.undone
                  and (o.kind in ('dep_in', 'dep_out') or (o.kind = 'pay' and o.data ? 'dep')));

-- ข้อมูลจากการจองครั้งก่อนของบัญชี LINE นี้ (เลขบัตรเต็มส่งให้เซิร์ฟเวอร์เท่านั้น หน้าจอจะเห็นแบบปิดบางหลัก)
create or replace function pp_liff_prev(p_line_user_id text) returns jsonb language sql stable as $$
  with g as (select * from guests where line_user_id = p_line_user_id),
  last as (select b.* from bookings b join g on g.id = b.guest_id where b.status <> 'ยกเลิก' order by b.created_at desc limit 1),
  tx as (select b.details->'tax' t from bookings b join g on g.id = b.guest_id
         where coalesce(b.details->'tax'->>'name', '') <> '' order by b.created_at desc limit 1),
  d as (select doc_no from guest_docs where line_user_id = p_line_user_id order by consent_at desc limit 1)
  select case when not exists (select 1 from last) then null else jsonb_build_object(
    'name', (select full_name from g), 'phone', (select phone from g),
    'email', (select nullif(details->>'email', '') from last),
    'since', (select check_in from last),
    'doc_no', (select doc_no from d),
    'tax', (select t from tx)) end
$$;

-- วิธีชำระ + เงินประกันที่ลูกค้าจ่ายมาพร้อมค่าห้อง (บาท/ห้อง · 0 = จ่ายที่เคาน์เตอร์)
drop function if exists pp_liff_setpay(jsonb, text);
create or replace function pp_liff_setpay(p_nos jsonb, p_pay text, p_dep int default 0) returns void language sql as $$
  update bookings set details = coalesce(details, '{}'::jsonb)
      || jsonb_build_object('liff_pay', case when p_pay = 'arrival' then 'arrival' else 'now' end,
                            'liff_dep', case when p_pay = 'arrival' then 0 else greatest(0, coalesce(p_dep, 0)) end),
    note = case when p_pay = 'arrival' then concat_ws(' · ', nullif(note, ''), 'ชำระวันเข้าพัก')
                when coalesce(p_dep, 0) > 0 then concat_ws(' · ', nullif(note, ''), 'จ่ายเงินประกันมาพร้อมค่าห้อง')
                else note end
  where booking_no in (select jsonb_array_elements_text(p_nos))
$$;

-- ยอดที่ต้องโอน (รวมเงินประกันถ้าเลือกจ่ายมาด้วย)
create or replace function pp_liff_due(p_no text) returns jsonb language sql stable as $$
  with g as (select coalesce(group_no, booking_no) k from bookings where booking_no = p_no),
  bs as (select b.* from bookings b, g where coalesce(b.group_no, b.booking_no) = g.k and b.status <> 'ยกเลิก')
  select jsonb_build_object('no', p_no,
    'total', (select coalesce(sum(room_total + coalesce((details->>'bf')::int, 0) + coalesce((details->>'liff_dep')::int, 0)), 0) from bs),
    'dep', (select coalesce(sum(coalesce((details->>'liff_dep')::int, 0)), 0) from bs),
    'nos', (select jsonb_agg(booking_no order by booking_no) from bs),
    'paid', exists (select 1 from ops o join bs on bs.booking_no = o.booking_no where o.kind = 'pay' and not o.undone))
$$;

-- รูปสลิป (จากแชท หรือแนบในหน้าจอจอง) → บันทึกค่าห้อง + เงินประกัน (ถ้าจ่ายมา) ป้าย "สลิปยังไม่ตรวจ"
create or replace function pp_liff_slip(p_line_user_id text, p_url text) returns jsonb language plpgsql as $$
declare v_nos jsonb := '[]'; b bookings; v_total int := 0; v_amt int; v_dep int;
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
    v_dep := coalesce((b.details->>'liff_dep')::int, 0);
    insert into ops (role, kind, booking_no, data)
    values ('staff', 'pay', b.booking_no, jsonb_build_object('m', 'transfer', 'room_amt', v_amt, 'slip', p_url, 'unchecked', true, 'by', 'line')
                                          || case when v_dep > 0 then jsonb_build_object('dep', v_dep) else '{}'::jsonb end);
    update bookings set note = concat_ws(' · ', nullif(note, ''), 'สลิปยังไม่ตรวจ') where booking_no = b.booking_no;
    v_nos := v_nos || to_jsonb(b.booking_no); v_total := v_total + v_amt + v_dep;
  end loop;
  return jsonb_build_object('matched', jsonb_array_length(v_nos) > 0, 'nos', v_nos, 'total', v_total);
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_liff_prev', 'pp_liff_setpay', 'pp_liff_due', 'pp_liff_slip') loop
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
