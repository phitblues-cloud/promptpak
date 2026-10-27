-- PROMPT PAK · ข้อความอัตโนมัติหาลูกค้าทาง LINE (เช้าวันเข้าพัก / มอบคีย์การ์ด / เตือนเช็คเอาท์ / เช็คเอาท์ + ให้คะแนน)
-- เก็บ: ตั้งค่า (สวิตช์หลัก + ข้อมูลโรงแรม) · ประวัติการส่ง (กันส่งซ้ำ) · คะแนนที่ลูกค้าให้
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)

create table if not exists auto_msg_cfg (
  k          text primary key,
  data       jsonb not null default '{}'::jsonb,
  by_role    text,
  updated_at timestamptz not null default now()
);

create table if not exists auto_msg_log (
  id           bigserial primary key,
  kind         text not null,                 -- arrive | welcome | remind | rate
  key          text not null,                 -- กลุ่มการจอง (group_no หรือ booking_no) · 1 เหตุการณ์ต่อ 1 การจองส่งครั้งเดียว
  line_user_id text,
  booking_no   text,
  status       text not null check (status in ('pending', 'sent', 'skipped', 'failed')),
  reason       text,
  payload      jsonb,
  attempts     int not null default 1,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (kind, key)
);

create table if not exists auto_msg_rating (
  key          text primary key,
  score        int not null check (score between 1 and 5),
  line_user_id text,
  created_at   timestamptz not null default now()
);

alter table auto_msg_cfg enable row level security;
alter table auto_msg_log enable row level security;
alter table auto_msg_rating enable row level security;

create or replace function pp_am_cfg() returns jsonb language sql stable as $$
  select coalesce((select data from auto_msg_cfg where k = 'main'), '{}'::jsonb)
$$;

create or replace function pp_am_save(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare cur jsonb := pp_am_cfg(); kk text; v jsonb; val text;
begin
  if jsonb_typeof(p) <> 'object' then raise exception 'ข้อมูลไม่ถูกต้อง'; end if;
  for kk, v in select * from jsonb_each(p) loop
    if kk = 'on' then
      cur := cur || jsonb_build_object('on', v = 'true'::jsonb);
    elsif kk in ('wifi_name', 'wifi_pass', 'breakfast', 'checkin_time', 'checkout_time', 'phone', 'map', 'review_url', 'test_to') then
      if jsonb_typeof(v) not in ('string', 'null') then raise exception 'ข้อมูล % ไม่ถูกต้อง', kk; end if;
      val := trim(coalesce(v #>> '{}', ''));
      if length(val) > 300 then raise exception 'ข้อมูล % ยาวเกินไป', kk; end if;
      if kk in ('map', 'review_url') and val <> '' and val !~* '^https?://' then raise exception 'ลิงก์ต้องขึ้นต้นด้วย https://'; end if;
      cur := cur || jsonb_build_object(kk, val);
    end if;
  end loop;
  insert into auto_msg_cfg (k, data, by_role) values ('main', cur, p_role)
  on conflict (k) do update set data = excluded.data, by_role = excluded.by_role, updated_at = now();
  return cur;
end $$;

-- จองคิวส่ง: คืน true ถ้าเป็นคนแรกที่ได้ส่ง (ส่งไม่สำเร็จแล้วลองใหม่ได้สูงสุด 3 ครั้ง)
create or replace function pp_am_claim(p_kind text, p_key text, p_line text, p_no text) returns boolean language plpgsql as $$
declare v_id bigint;
begin
  insert into auto_msg_log (kind, key, line_user_id, booking_no, status) values (p_kind, p_key, p_line, p_no, 'pending')
  on conflict (kind, key) do update set status = 'pending', attempts = auto_msg_log.attempts + 1, updated_at = now()
    where auto_msg_log.status = 'failed' and auto_msg_log.attempts < 3
  returning id into v_id;
  return v_id is not null;
end $$;

create or replace function pp_am_done(p_kind text, p_key text, p_status text, p_reason text, p_payload jsonb) returns void language sql as $$
  update auto_msg_log set status = p_status, reason = p_reason, payload = p_payload, updated_at = now()
  where kind = p_kind and key = p_key
$$;

-- ผู้รับ + ห้องทั้งหมดในกลุ่มการจองของเลขการจองนี้
create or replace function pp_am_target(p_no text) returns jsonb language sql stable as $$
  select jsonb_build_object(
    'key', coalesce(b.group_no, b.booking_no), 'no', b.booking_no,
    'name', coalesce(nullif(g.full_name, ''), b.guest_name), 'line_user_id', g.line_user_id,
    'check_in', b.check_in, 'check_out', b.check_out, 'nights', b.nights, 'cancelled', b.status = 'ยกเลิก',
    'rooms', (select coalesce(jsonb_agg(x.room_id order by x.room_id), '[]'::jsonb) from bookings x
              where x.status <> 'ยกเลิก' and coalesce(x.group_no, x.booking_no) = coalesce(b.group_no, b.booking_no)
                and (b.group_no is null or x.guest_id is not distinct from b.guest_id)),
    'all_out', not exists (select 1 from bookings x
              where x.status <> 'ยกเลิก' and coalesce(x.group_no, x.booking_no) = coalesce(b.group_no, b.booking_no)
                and (b.group_no is null or x.guest_id is not distinct from b.guest_id)
                and not exists (select 1 from ops o where o.booking_no = x.booking_no and o.kind = 'checkout' and not o.undone)))
  from bookings b left join guests g on g.id = b.guest_id
  where b.booking_no = p_no
$$;

-- ห้องพร้อมไหม: ไม่มีงานทำความสะอาดค้าง และไม่มีแขกเก่าที่ยังอยู่ในห้องวันนี้
create or replace function pp_am_room_ready(p_room text, p_no text, p_today date) returns boolean language sql stable as $$
  select not exists (select 1 from hk_task t where t.room = p_room and t.st < 5 and not t.deleted)
     and not exists (select 1 from bookings o
        where o.room_id = p_room and o.status <> 'ยกเลิก' and o.booking_no <> p_no
          and o.check_in <= p_today and o.check_out >= p_today and pp_checked_in(o.booking_no)
          and not exists (select 1 from ops x where x.booking_no = o.booking_no and x.kind = 'checkout' and not x.undone))
$$;

-- วันเข้าพักวันนี้ที่ยังไม่เช็คอิน (มีบัญชี LINE) — กลุ่มละ 1 แถว
create or replace function pp_am_arrivals(p_today date) returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(t), '[]'::jsonb) from (
    select distinct on (coalesce(b.group_no, b.booking_no)) pp_am_target(b.booking_no) || jsonb_build_object('ready',
      (select bool_and(pp_am_room_ready(x.room_id, x.booking_no, p_today)) from bookings x
        where x.status <> 'ยกเลิก' and coalesce(x.group_no, x.booking_no) = coalesce(b.group_no, b.booking_no)
          and (b.group_no is null or x.guest_id is not distinct from b.guest_id))) as t
    from bookings b join guests g on g.id = b.guest_id
    where b.check_in = p_today and b.status <> 'ยกเลิก' and g.line_user_id is not null and not pp_checked_in(b.booking_no)
    order by coalesce(b.group_no, b.booking_no), b.booking_no) s
$$;

-- คืนสุดท้ายของคนพักหลายคืน (พรุ่งนี้เช็คเอาท์) ที่เช็คอินแล้วและยังไม่เช็คเอาท์
create or replace function pp_am_reminders(p_today date) returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(t), '[]'::jsonb) from (
    select distinct on (coalesce(b.group_no, b.booking_no)) pp_am_target(b.booking_no) as t
    from bookings b join guests g on g.id = b.guest_id
    where b.check_out = p_today + 1 and b.nights >= 2 and b.status <> 'ยกเลิก' and g.line_user_id is not null
      and pp_checked_in(b.booking_no)
      and not exists (select 1 from ops o where o.booking_no = b.booking_no and o.kind = 'checkout' and not o.undone)
    order by coalesce(b.group_no, b.booking_no), b.booking_no) s
$$;

-- บันทึกคะแนนที่ลูกค้ากด (ครั้งแรกเท่านั้น) · ตรวจว่าเป็นเจ้าของการจองจริง
create or replace function pp_am_rate(p_key text, p_line text, p_score int) returns jsonb language plpgsql as $$
declare v_name text; v_first boolean;
begin
  if p_score is null or p_score < 1 or p_score > 5 then raise exception 'คะแนนไม่ถูกต้อง'; end if;
  select coalesce(nullif(g.full_name, ''), b.guest_name) into v_name
  from bookings b join guests g on g.id = b.guest_id
  where coalesce(b.group_no, b.booking_no) = p_key and g.line_user_id = p_line limit 1;
  if v_name is null then raise exception 'ไม่พบการจองของบัญชี LINE นี้'; end if;
  insert into auto_msg_rating (key, score, line_user_id) values (p_key, p_score, p_line) on conflict (key) do nothing;
  get diagnostics v_first = row_count;
  return jsonb_build_object('first', v_first, 'name', v_name, 'score', (select score from auto_msg_rating where key = p_key));
end $$;

-- ตัวเลขสรุปสำหรับหน้าตั้งค่า: ส่งแล้ว/ข้าม/ล้มเหลว 30 วัน + ผู้รับทดสอบที่เลือกได้
create or replace function pp_am_overview() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'cfg', pp_am_cfg(),
    'stats', (select coalesce(jsonb_object_agg(kind || ':' || status, n), '{}'::jsonb)
              from (select kind, status, count(*) n from auto_msg_log where created_at > now() - interval '30 days' group by 1, 2) s),
    'recent', (select coalesce(jsonb_agg(r), '[]'::jsonb) from (
               select kind, booking_no, status, reason, created_at from auto_msg_log order by id desc limit 12) r),
    'people', (select coalesce(jsonb_agg(p), '[]'::jsonb) from (
               select coalesce(nullif(full_name, ''), line_display_name, 'ไม่ระบุชื่อ') as name, line_user_id as id
               from guests where line_user_id is not null order by created_at desc limit 20) p))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_am_cfg', 'pp_am_save', 'pp_am_claim', 'pp_am_done', 'pp_am_target',
             'pp_am_room_ready', 'pp_am_arrivals', 'pp_am_reminders', 'pp_am_rate', 'pp_am_overview') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
