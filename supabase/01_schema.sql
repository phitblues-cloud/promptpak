-- PROMPT PAK · ฐานข้อมูลระบบจริง (เฟส 1: จองผ่าน LINE + AI)
-- วิธีใช้: เปิด Supabase > SQL Editor > วางทั้งไฟล์นี้ > Run (รันซ้ำได้ ไม่ลบข้อมูลเดิม)

create extension if not exists btree_gist;

-- ---------- ตาราง ----------
create table if not exists rooms (
  id          text primary key,                       -- ตึกใหม่ A01–A08 (ชั้น 1), B01–B08 (ชั้น 2) · บ้านหลัง C01–C15
  zone        text not null,                          -- ตึกใหม่ / บ้านหลัง (ดูท้ายไฟล์)
  room_type   text not null,                          -- เตียงเดี่ยว / เตียงคู่ / ห้องครอบครัว
  bed         text,                                   -- รายละเอียดเตียง เช่น เตียงสองชั้น
  rate        int  not null check (rate > 0),          -- ราคาต่อคืน รวม VAT แล้ว
  max_guests  int  not null default 2,
  active      boolean not null default true
);

create table if not exists guests (
  id                uuid primary key default gen_random_uuid(),
  full_name         text,
  phone             text,
  company           text,
  line_user_id      text unique,
  line_display_name text,
  is_member         boolean not null default false,
  created_at        timestamptz not null default now()
);

create table if not exists bookings (
  id             bigserial primary key,
  booking_no     text unique not null,
  group_no       text,                                 -- จองหลายห้องพร้อมกัน = group เดียวกัน
  guest_id       uuid references guests(id),
  guest_name     text not null,
  phone          text,
  company        text,
  room_id        text not null references rooms(id),
  check_in       date not null,
  check_out      date not null,
  nights         int  generated always as (check_out - check_in) stored,
  rate           int  not null,
  room_total     int  generated always as ((check_out - check_in) * rate) stored,
  deposit        int  not null default 300,
  status         text not null default 'ยืนยันแล้ว' check (status in ('ยืนยันแล้ว','ยกเลิก')),
  payment_status text not null default 'ยังไม่ชำระ',
  channel        text not null default 'LINE OA',
  created_by     text not null default 'staff' check (created_by in ('ai','staff','seed')),
  note           text,
  created_at     timestamptz not null default now(),
  check (check_out > check_in),
  -- ราวกันตกชั้นที่ 1: ห้องเดียวกันห้ามมีการจองทับคืนกัน (ฐานข้อมูลปฏิเสธเอง)
  constraint no_double_booking exclude using gist (
    room_id with =, daterange(check_in, check_out, '[)') with &&
  ) where (status <> 'ยกเลิก')
);
create index if not exists bookings_dates on bookings (check_in, check_out);

create table if not exists chat_threads (
  id              bigserial primary key,
  line_user_id    text unique not null,
  guest_id        uuid references guests(id),
  display_name    text,
  needs_staff     boolean not null default false,       -- AI ส่งต่อให้พนักงาน
  handoff_reason  text,
  is_seed         boolean not null default false,
  last_message_at timestamptz not null default now()
);

create table if not exists chat_messages (
  id         bigserial primary key,
  thread_id  bigint not null references chat_threads(id) on delete cascade,
  sender     text not null check (sender in ('ลูกค้า','AI','พนักงาน','ระบบ')),
  body       text not null,
  meta       jsonb,
  created_at timestamptz not null default now()
);
create index if not exists chat_messages_thread on chat_messages (thread_id, created_at);

-- กันข้อความ LINE ซ้ำ (LINE อาจส่ง webhook ซ้ำ)
create table if not exists line_events (
  event_id   text primary key,
  created_at timestamptz not null default now()
);

-- ปิดการเข้าถึงตรงจากเบราว์เซอร์ทั้งหมด: ทุกอย่างต้องผ่านหลังบ้าน (service role) เท่านั้น
alter table rooms         enable row level security;
alter table guests        enable row level security;
alter table bookings      enable row level security;
alter table chat_threads  enable row level security;
alter table chat_messages enable row level security;
alter table line_events   enable row level security;

-- ---------- ฟังก์ชันช่วย ----------
create or replace function pp_today() returns date language sql stable as $$
  select (now() at time zone 'Asia/Bangkok')::date
$$;

-- ห้องว่างตามประเภท ในช่วง [check_in, check_out)
create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not exists (
      select 1 from bookings b
      where b.room_id = r.id and b.status <> 'ยกเลิก'
        and daterange(b.check_in, b.check_out, '[)') && daterange(p_check_in, p_check_out, '[)'))
  )
  select jsonb_build_object(
    'check_in', p_check_in, 'check_out', p_check_out, 'nights', p_check_out - p_check_in,
    'types', coalesce((
      select jsonb_agg(jsonb_build_object(
        'zone', t.zone, 'room_type', t.room_type, 'rate', t.rate, 'max_guests', t.max_guests,
        'bed', t.bed, 'total_rooms', t.total,
        'free_rooms', (select count(*) from free f where f.room_type = t.room_type))
        order by t.zone desc, t.rate)
      from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) total
            from rooms where active group by zone, room_type) t), '[]'::jsonb))
$$;

-- เลขที่การจองถัดไป เช่น BK6910078 (BK + ปี พ.ศ. 2 หลัก + เดือน + ลำดับ)
create or replace function pp_next_booking_no() returns text language plpgsql as $$
declare pfx text; n int;
begin
  pfx := 'BK' || lpad(((extract(year from pp_today())::int + 543) % 100)::text, 2, '0')
               || to_char(pp_today(), 'MM');
  perform pg_advisory_xact_lock(hashtext('pp_booking_no'));
  select coalesce(max(substring(booking_no from length(pfx) + 1)::int), 0) + 1 into n
    from bookings where booking_no like pfx || '%' and booking_no ~ ('^' || pfx || '[0-9]+$');
  return pfx || lpad(n::text, 3, '0');
end $$;

-- จองห้อง (ทำทั้งหมดหรือไม่ทำเลย)
-- p = {guest_name, phone, company, line_user_id, check_in, check_out, created_by, note,
--      items:[{room_type, count}]}
create or replace function pp_book(p jsonb) returns jsonb language plpgsql as $$
declare
  v_in date := (p->>'check_in')::date;
  v_out date := (p->>'check_out')::date;
  v_by text := coalesce(p->>'created_by', 'staff');
  v_name text := nullif(trim(p->>'guest_name'), '');
  v_phone text := nullif(regexp_replace(coalesce(p->>'phone', ''), '[^0-9+]', '', 'g'), '');
  v_guest uuid; v_group text; v_no text; v_total_rooms int := 0;
  it jsonb; r record; v_cnt int; v_got int; out_rows jsonb := '[]'::jsonb;
begin
  if v_name is null then raise exception 'ต้องมีชื่อผู้จอง'; end if;
  if v_phone is null or length(v_phone) < 9 then raise exception 'ต้องมีเบอร์โทรที่ถูกต้อง'; end if;
  if v_in is null or v_out is null or v_out <= v_in then raise exception 'วันเข้าพัก/วันออกไม่ถูกต้อง'; end if;
  if v_in < pp_today() then raise exception 'วันเข้าพักต้องไม่ใช่วันที่ผ่านมาแล้ว'; end if;
  if v_out - v_in > 30 then raise exception 'จองได้ครั้งละไม่เกิน 30 คืน'; end if;
  select coalesce(sum((x->>'count')::int), 0) into v_total_rooms from jsonb_array_elements(p->'items') x;
  if v_total_rooms < 1 then raise exception 'ต้องระบุจำนวนห้องอย่างน้อย 1 ห้อง'; end if;
  -- ราวกันตกชั้นที่ 3: AI ยืนยันเองได้ไม่เกิน 4 ห้อง (5 ห้องขึ้นไปส่งพนักงาน)
  if v_by = 'ai' and v_total_rooms > 4 then raise exception 'จอง 5 ห้องขึ้นไปต้องให้พนักงานยืนยัน'; end if;

  -- ผูก/สร้างลูกค้า
  if p->>'line_user_id' is not null then
    insert into guests (full_name, phone, company, line_user_id, line_display_name)
    values (v_name, v_phone, p->>'company', p->>'line_user_id', p->>'line_display_name')
    on conflict (line_user_id) do update
      set full_name = excluded.full_name, phone = excluded.phone,
          company = coalesce(excluded.company, guests.company)
    returning id into v_guest;
  end if;

  v_group := case when v_total_rooms > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;

  for it in select * from jsonb_array_elements(p->'items') loop
    v_cnt := (it->>'count')::int; v_got := 0;
    if v_cnt is null or v_cnt < 1 then continue; end if;
    if not exists (select 1 from rooms where room_type = it->>'room_type' and active) then
      raise exception 'ไม่มีประเภทห้อง %', it->>'room_type';
    end if;
    for r in
      select rm.* from rooms rm
      where rm.active and rm.room_type = it->>'room_type' and not exists (
        select 1 from bookings b where b.room_id = rm.id and b.status <> 'ยกเลิก'
          and daterange(b.check_in, b.check_out, '[)') && daterange(v_in, v_out, '[)'))
      order by rm.id limit v_cnt
      for update
    loop
      v_no := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id,
                            check_in, check_out, rate, created_by, channel, note)
      values (v_no, v_group, v_guest, v_name, v_phone, p->>'company', r.id,
              v_in, v_out, r.rate, v_by, coalesce(p->>'channel', 'LINE OA'), p->>'note');
      out_rows := out_rows || jsonb_build_object('booking_no', v_no, 'room_id', r.id,
                    'room_type', r.room_type, 'rate', r.rate, 'room_total', r.rate * (v_out - v_in));
      v_got := v_got + 1;
    end loop;
    if v_got < v_cnt then
      raise exception 'ห้อง % ว่างไม่พอ (ต้องการ % ว่าง %)', it->>'room_type', v_cnt, v_got;
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'group_no', v_group, 'check_in', v_in, 'check_out', v_out,
    'nights', v_out - v_in, 'bookings', out_rows,
    'room_total', (select coalesce(sum((x->>'room_total')::int), 0) from jsonb_array_elements(out_rows) x),
    'deposit_total', 300 * jsonb_array_length(out_rows));
end $$;

-- ภาพรวมวันนี้ (หน้าแรก)
create or replace function pp_dashboard(p_date date default null) returns jsonb language sql stable as $$
  with d as (select coalesce(p_date, pp_today()) as day),
  act as (select b.*, r.zone, r.room_type from bookings b join rooms r on r.id = b.room_id where b.status <> 'ยกเลิก'),
  rowj as (
    select a.*, jsonb_build_object('booking_no', a.booking_no, 'guest_name', a.guest_name, 'company', a.company,
      'room_id', a.room_id, 'zone', a.zone, 'room_type', a.room_type, 'check_in', a.check_in,
      'check_out', a.check_out, 'nights', a.nights, 'payment_status', a.payment_status,
      'created_by', a.created_by, 'group_no', a.group_no, 'phone', a.phone,
      'created_at', a.created_at, 'rate', a.rate, 'room_total', a.room_total, 'deposit', a.deposit,
      'channel', a.channel, 'status', a.status, 'note', a.note) j
    from act a)
  select jsonb_build_object(
    'date', (select day from d),
    'rooms_total', (select count(*) from rooms where active),
    'arrivals',   coalesce((select jsonb_agg(j order by room_id) from rowj, d where check_in = d.day), '[]'),
    'in_house',   coalesce((select jsonb_agg(j order by room_id) from rowj, d where check_in < d.day and check_out > d.day), '[]'),
    'departures', coalesce((select jsonb_agg(j order by room_id) from rowj, d where check_out = d.day), '[]'),
    'occupied_tonight', (select count(*) from act, d where check_in <= d.day and check_out > d.day),
    'ai_bookings_today', (select count(*) from bookings, d where created_by = 'ai'
                            and (created_at at time zone 'Asia/Bangkok')::date = d.day),
    'chats_need_staff', (select count(*) from chat_threads where needs_staff),
    'latest_ai', coalesce((select jsonb_agg(j order by created_at desc) from
                    (select j, created_at from rowj where created_by = 'ai' order by created_at desc limit 5) z), '[]'))
$$;

-- การจองในช่วงวัน (ปฏิทิน + รายการ)
create or replace function pp_bookings(p_from date, p_to date) returns jsonb language sql stable as $$
  select jsonb_build_object(
    'from', p_from, 'to', p_to, 'today', pp_today(),
    'rooms', (select jsonb_agg(jsonb_build_object('id', id, 'zone', zone, 'room_type', room_type, 'rate', rate) order by id)
              from rooms where active),
    'bookings', coalesce((select jsonb_agg(jsonb_build_object(
        'booking_no', b.booking_no, 'group_no', b.group_no, 'guest_name', b.guest_name, 'phone', b.phone,
        'company', b.company, 'room_id', b.room_id, 'check_in', b.check_in, 'check_out', b.check_out,
        'nights', b.nights, 'rate', b.rate, 'room_total', b.room_total, 'deposit', b.deposit,
        'status', b.status, 'payment_status', b.payment_status, 'channel', b.channel,
        'created_by', b.created_by, 'created_at', b.created_at, 'note', b.note)
        order by b.check_in, b.room_id)
      from bookings b where b.check_in < p_to and b.check_out > p_from), '[]'))
$$;

-- บันทึกข้อความแชท (สร้างห้องแชทถ้ายังไม่มี)
create or replace function pp_chat_log(p_line_user_id text, p_display_name text, p_sender text,
                                       p_body text, p_meta jsonb default null)
returns bigint language plpgsql as $$
declare t bigint;
begin
  insert into chat_threads (line_user_id, display_name, guest_id)
  values (p_line_user_id, p_display_name, (select id from guests where line_user_id = p_line_user_id))
  on conflict (line_user_id) do update
    set display_name = coalesce(excluded.display_name, chat_threads.display_name), last_message_at = now()
  returning id into t;
  insert into chat_messages (thread_id, sender, body, meta) values (t, p_sender, p_body, p_meta);
  return t;
end $$;

-- บริบทสำหรับ AI: ข้อความล่าสุด + การจองที่จะมาถึงของลูกค้าคนนี้
create or replace function pp_chat_context(p_line_user_id text, p_limit int default 20)
returns jsonb language sql stable as $$
  select jsonb_build_object(
    'thread', (select to_jsonb(t) from chat_threads t where line_user_id = p_line_user_id),
    'guest', (select to_jsonb(g) from guests g where line_user_id = p_line_user_id),
    'messages', coalesce((select jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'at', created_at) order by created_at)
       from (select m.* from chat_messages m join chat_threads t on t.id = m.thread_id
             where t.line_user_id = p_line_user_id order by m.created_at desc, m.id desc limit p_limit) z), '[]'),
    'upcoming', coalesce((select jsonb_agg(jsonb_build_object('booking_no', b.booking_no, 'room_id', b.room_id,
         'check_in', b.check_in, 'check_out', b.check_out, 'room_total', b.room_total) order by b.check_in)
       from bookings b join guests g on g.id = b.guest_id
       where g.line_user_id = p_line_user_id and b.status <> 'ยกเลิก' and b.check_out >= pp_today()), '[]'))
$$;

-- คืนค่า true ถ้าเหตุการณ์นี้เคยประมวลผลแล้ว (กันตอบซ้ำ)
create or replace function pp_event_seen(p_event_id text) returns boolean language plpgsql as $$
begin
  insert into line_events (event_id) values (p_event_id);
  return false;
exception when unique_violation then
  return true;
end $$;


create or replace function pp_chat_threads() returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(x order by x->>'last_message_at' desc), '[]') from (
    select jsonb_build_object('id', t.id, 'display_name', t.display_name, 'needs_staff', t.needs_staff,
      'handoff_reason', t.handoff_reason, 'is_seed', t.is_seed, 'last_message_at', t.last_message_at,
      'last_body', (select body from chat_messages m where m.thread_id = t.id order by created_at desc, id desc limit 1),
      'count', (select count(*) from chat_messages m where m.thread_id = t.id)) x
    from chat_threads t) z
$$;

create or replace function pp_chat_messages(p_thread_id bigint) returns jsonb language sql stable as $$
  select jsonb_build_object(
    'thread', (select to_jsonb(t) from chat_threads t where id = p_thread_id),
    'messages', coalesce((select jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'meta', meta, 'at', created_at) order by created_at, id)
                 from chat_messages where thread_id = p_thread_id), '[]'))
$$;

create or replace function pp_chat_resolve(p_thread_id bigint) returns void language sql as $$
  update chat_threads set needs_staff = false, handoff_reason = null where id = p_thread_id
$$;

-- ข้อมูลสำหรับ AI สรุปให้เจ้าของ (ตัวเลขทั้งหมดคำนวณจากฐานข้อมูล ไม่ให้ AI คิดเลขเอง)
create or replace function pp_summary_data(p_date date default null) returns jsonb language sql stable as $$
  with d as (select coalesce(p_date, pp_today()) as day),
  act as (select * from bookings where status <> 'ยกเลิก'),
  days as (select (d.day + i) as day from d, generate_series(0, 6) i)
  select jsonb_build_object(
    'today', (select day from d),
    'rooms_total', (select count(*) from rooms where active),
    'next7', (select jsonb_agg(jsonb_build_object('date', x.day,
                 'occupied', (select count(*) from act where check_in <= x.day and check_out > x.day),
                 'arrivals', (select count(*) from act where check_in = x.day),
                 'departures', (select count(*) from act where check_out = x.day)) order by x.day) from days x),
    'arrivals_today', (select coalesce(jsonb_agg(jsonb_build_object('room', room_id, 'guest', guest_name,
                 'company', company, 'payment', payment_status) order by room_id), '[]') from act, d where check_in = d.day),
    'unpaid_arrivals_today', (select count(*) from act, d where check_in = d.day and payment_status <> 'ชำระแล้ว'),
    'new_bookings_24h', (select coalesce(jsonb_agg(jsonb_build_object('booking_no', booking_no, 'guest', guest_name,
                 'room', room_id, 'check_in', check_in, 'nights', nights, 'by', created_by) order by created_at), '[]')
                 from bookings where created_at > now() - interval '24 hours' and created_by <> 'seed'),
    'chats_need_staff', (select coalesce(jsonb_agg(jsonb_build_object('name', display_name, 'reason', handoff_reason)), '[]')
                 from chat_threads where needs_staff),
    'recent_chats', (select coalesce(jsonb_agg(jsonb_build_object('name', t.display_name, 'messages',
                 (select jsonb_agg(jsonb_build_object('from', sender, 'text', left(body, 300)) order by created_at)
                  from (select * from chat_messages m where m.thread_id = t.id order by created_at desc limit 6) mm))), '[]')
                 from (select * from chat_threads order by last_message_at desc limit 8) t))
$$;

-- ทุกฟังก์ชันเรียกได้จากหลังบ้านเท่านั้น
do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname like 'pp\_%' loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;

-- ---------- สำหรับหน้าจอ v196 ----------
alter table chat_threads add column if not exists handoff_at timestamptz;

create table if not exists pin_fails (
  id bigserial primary key,
  ip text not null,
  at timestamptz not null default now()
);
alter table pin_fails enable row level security;

-- ค่าที่เปลี่ยนเมื่อข้อมูลเปลี่ยน (หน้าจอใช้ตรวจว่าต้องโหลดข้อมูลใหม่ไหม)
create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff))
$$;

-- ข้อมูลทั้งหมดที่หน้าจอใช้
create or replace function pp_export() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'stamp', pp_stamp(),
    'bookings', coalesce((select jsonb_agg(to_jsonb(b) - 'id' order by b.booking_no) from bookings b), '[]'),
    'guests', coalesce((select jsonb_agg(to_jsonb(g)) from guests g), '[]'),
    'threads', coalesce((select jsonb_agg(jsonb_build_object('id', t.id, 'line_user_id', t.line_user_id,
        'display_name', t.display_name, 'needs_staff', t.needs_staff, 'is_seed', t.is_seed,
        'messages', (select coalesce(jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'at', created_at)
                       order by created_at, id), '[]') from chat_messages m where m.thread_id = t.id))
        order by t.id)
      from chat_threads t where not t.is_seed), '[]'))
$$;

-- AI เงียบเมื่อส่งต่อพนักงาน: เปิดให้ AI ตอบอีกครั้งอัตโนมัติหลัง 6 ชั่วโมง
create or replace function pp_staff_active(p_line_user_id text) returns boolean language plpgsql as $$
declare t chat_threads;
begin
  select * into t from chat_threads where line_user_id = p_line_user_id;
  if t.id is null or not t.needs_staff then return false; end if;
  if t.handoff_at is not null and t.handoff_at < now() - interval '6 hours' then
    update chat_threads set needs_staff = false, handoff_reason = null where id = t.id;
    return false;
  end if;
  return true;
end $$;

create or replace function pp_handoff(p_line_user_id text, p_reason text) returns void language sql as $$
  update chat_threads set needs_staff = true, handoff_reason = p_reason, handoff_at = now() where line_user_id = p_line_user_id
$$;

-- กันเดา PIN: ผิดเกิน 8 ครั้งใน 15 นาที ล็อก
create or replace function pp_pin_locked(p_ip text) returns boolean language sql stable as $$
  select count(*) >= 8 from pin_fails where ip = p_ip and at > now() - interval '15 minutes'
$$;
create or replace function pp_pin_fail(p_ip text) returns void language sql as $$
  insert into pin_fails (ip) values (p_ip)
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname like 'pp\_%' loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;

-- เก็บผล AI สรุปไว้ใช้ซ้ำ (ข้อมูลไม่เปลี่ยน = ไม่เรียก AI ซ้ำ ประหยัดค่าใช้จ่าย)
create table if not exists ai_cache (
  key        text primary key,
  value      jsonb not null,
  created_at timestamptz not null default now()
);
alter table ai_cache enable row level security;
create or replace function pp_cache_get(p_key text) returns jsonb language sql stable as $$
  select value from ai_cache where key = p_key and created_at > now() - interval '1 hour'
$$;
create or replace function pp_cache_put(p_key text, p_value jsonb) returns void language sql as $$
  insert into ai_cache (key, value) values (p_key, p_value)
  on conflict (key) do update set value = excluded.value, created_at = now()
$$;
do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_cache_get', 'pp_cache_put') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;

-- ให้สิทธิ์หลังบ้าน (service_role) ใช้ตารางและฟังก์ชันทั้งหมดอย่างชัดเจน
grant usage on schema public to service_role;
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;
grant execute on all functions in schema public to service_role;

-- ---------- ห้องจริง 2569: รหัส/โซน/ประเภทใหม่ (รันซ้ำได้) ----------
-- โซนตึกใหม่ 16 ห้อง (A = ชั้น 1, B = ชั้น 2) · โซนบ้านหลัง 15 ห้อง (C01–C15 ชั้นเดียว)
alter table rooms drop constraint if exists rooms_zone_check;
alter table rooms add column if not exists floor int not null default 1;

insert into rooms (id, zone, room_type, bed, rate, max_guests, floor) values
  ('A01', 'ตึกใหม่', 'เตียงคู่', 'เตียงสองชั้น (ชั้นบนเตียงเดี่ยว + ชั้นล่างเตียงเดี่ยว)', 700, 2, 1),
  ('A02', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 1),
  ('A03', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 1),
  ('A04', 'ตึกใหม่', 'ห้องครอบครัว', 'เตียงสองชั้น (ชั้นล่างเตียงใหญ่ 2 คน + ชั้นบนเตียงเดี่ยว 1 คน)', 800, 3, 1),
  ('A05', 'ตึกใหม่', 'ห้องครอบครัว', 'เตียงสองชั้น (ชั้นล่างเตียงใหญ่ 2 คน + ชั้นบนเตียงเดี่ยว 1 คน)', 800, 3, 1),
  ('A06', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 1),
  ('A07', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 1),
  ('A08', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 1),
  ('B01', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 2),
  ('B02', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 2),
  ('B03', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 2),
  ('B04', 'ตึกใหม่', 'เตียงคู่', 'เตียงสองชั้น (ชั้นบนเตียงเดี่ยว + ชั้นล่างเตียงเดี่ยว)', 700, 2, 2),
  ('B05', 'ตึกใหม่', 'เตียงคู่', 'เตียงสองชั้น (ชั้นบนเตียงเดี่ยว + ชั้นล่างเตียงเดี่ยว)', 700, 2, 2),
  ('B06', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 2),
  ('B07', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 2),
  ('B08', 'ตึกใหม่', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 700, 2, 2),
  ('C01', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C02', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C03', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C04', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C05', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C06', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C07', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C08', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C09', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C10', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C11', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C12', 'บ้านหลัง', 'เตียงเดี่ยว', 'เตียงใหญ่ 1 เตียง', 400, 2, 1),
  ('C13', 'บ้านหลัง', 'เตียงคู่', 'เตียงเดี่ยว 2 เตียง วางแยกกัน', 500, 2, 1),
  ('C14', 'บ้านหลัง', 'เตียงคู่', 'เตียงเดี่ยว 2 เตียง วางแยกกัน', 500, 2, 1),
  ('C15', 'บ้านหลัง', 'เตียงคู่', 'เตียงเดี่ยว 2 เตียง วางแยกกัน', 500, 2, 1)
on conflict (id) do update set zone = excluded.zone, room_type = excluded.room_type, bed = excluded.bed,
  rate = excluded.rate, max_guests = excluded.max_guests, floor = excluded.floor, active = true;

-- ย้ายการจองทุกรายการ (รวมการจองจริงจาก LINE) จากรหัสเก่าไปรหัสใหม่ แล้วลบห้องรหัสเก่า
update bookings b set room_id = m.new_id
from (values
  ('A001', 'A02'),
  ('A002', 'A03'),
  ('A003', 'A06'),
  ('A004', 'A07'),
  ('A005', 'A08'),
  ('A006', 'B01'),
  ('A007', 'B02'),
  ('A008', 'B03'),
  ('A009', 'B06'),
  ('A010', 'B07'),
  ('A011', 'B08'),
  ('A012', 'A01'),
  ('A013', 'B04'),
  ('A014', 'B05'),
  ('A015', 'A04'),
  ('A016', 'A05'),
  ('B001', 'C01'),
  ('B002', 'C02'),
  ('B003', 'C03'),
  ('B004', 'C04'),
  ('B005', 'C05'),
  ('B006', 'C06'),
  ('B007', 'C07'),
  ('B008', 'C08'),
  ('B009', 'C09'),
  ('B010', 'C10'),
  ('B011', 'C11'),
  ('B012', 'C12'),
  ('B013', 'C13'),
  ('B014', 'C14'),
  ('B015', 'C15')
) as m(old_id, new_id)
where b.room_id = m.old_id;
delete from rooms where id ~ '^[AB]0[0-9][0-9]$';
alter table rooms add constraint rooms_zone_check check (zone in ('ตึกใหม่', 'บ้านหลัง'));

-- ห้องว่างแยกตามโซน + ประเภท (นับห้องชั้น 1 ที่ว่างด้วย)
create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not exists (
      select 1 from bookings b
      where b.room_id = r.id and b.status <> 'ยกเลิก'
        and daterange(b.check_in, b.check_out, '[)') && daterange(p_check_in, p_check_out, '[)'))
  )
  select jsonb_build_object(
    'check_in', p_check_in, 'check_out', p_check_out, 'nights', p_check_out - p_check_in,
    'types', coalesce((
      select jsonb_agg(jsonb_build_object(
        'zone', t.zone, 'room_type', t.room_type, 'rate', t.rate, 'max_guests', t.max_guests,
        'bed', t.bed, 'total_rooms', t.total,
        'free_rooms', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type),
        'free_ground_floor', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type and f.floor = 1))
        order by t.zone desc, t.rate, t.room_type)
      from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) total
            from rooms where active group by zone, room_type) t), '[]'::jsonb))
$$;

-- จองห้อง (ทำทั้งหมดหรือไม่ทำเลย)
-- p = {guest_name, phone, company, line_user_id, check_in, check_out, created_by, note, prefer_ground_floor,
--      items:[{zone, room_type, count}]}
-- prefer_ground_floor = true -> จัดเฉพาะห้องชั้น 1 ถ้าไม่พอจะไม่จอง (ให้พนักงานดูแลต่อ)
create or replace function pp_book(p jsonb) returns jsonb language plpgsql as $$
declare
  v_in date := (p->>'check_in')::date;
  v_out date := (p->>'check_out')::date;
  v_by text := coalesce(p->>'created_by', 'staff');
  v_name text := nullif(trim(p->>'guest_name'), '');
  v_phone text := nullif(regexp_replace(coalesce(p->>'phone', ''), '[^0-9+]', '', 'g'), '');
  v_ground boolean := coalesce((p->>'prefer_ground_floor')::boolean, false);
  v_guest uuid; v_group text; v_no text; v_total_rooms int := 0; v_zone text;
  it jsonb; r record; v_cnt int; v_got int; out_rows jsonb := '[]'::jsonb;
begin
  if v_name is null then raise exception 'ต้องมีชื่อผู้จอง'; end if;
  if v_phone is null or length(v_phone) < 9 then raise exception 'ต้องมีเบอร์โทรที่ถูกต้อง'; end if;
  if v_in is null or v_out is null or v_out <= v_in then raise exception 'วันเข้าพัก/วันออกไม่ถูกต้อง'; end if;
  if v_in < pp_today() then raise exception 'วันเข้าพักต้องไม่ใช่วันที่ผ่านมาแล้ว'; end if;
  if v_out - v_in > 30 then raise exception 'จองได้ครั้งละไม่เกิน 30 คืน'; end if;
  select coalesce(sum((x->>'count')::int), 0) into v_total_rooms from jsonb_array_elements(p->'items') x;
  if v_total_rooms < 1 then raise exception 'ต้องระบุจำนวนห้องอย่างน้อย 1 ห้อง'; end if;
  -- ราวกันตกชั้นที่ 3: AI ยืนยันเองได้ไม่เกิน 4 ห้อง (5 ห้องขึ้นไปส่งพนักงาน)
  if v_by = 'ai' and v_total_rooms > 4 then raise exception 'จอง 5 ห้องขึ้นไปต้องให้พนักงานยืนยัน'; end if;

  if p->>'line_user_id' is not null then
    insert into guests (full_name, phone, company, line_user_id, line_display_name)
    values (v_name, v_phone, p->>'company', p->>'line_user_id', p->>'line_display_name')
    on conflict (line_user_id) do update
      set full_name = excluded.full_name, phone = excluded.phone,
          company = coalesce(excluded.company, guests.company)
    returning id into v_guest;
  end if;

  v_group := case when v_total_rooms > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;

  for it in select * from jsonb_array_elements(p->'items') loop
    v_cnt := (it->>'count')::int; v_got := 0; v_zone := nullif(it->>'zone', '');
    if v_cnt is null or v_cnt < 1 then continue; end if;
    if v_zone is null and (select count(distinct zone) from rooms where room_type = it->>'room_type' and active) > 1 then
      raise exception 'ประเภท % มีทั้งโซนตึกใหม่และโซนบ้านหลัง ต้องระบุโซน', it->>'room_type';
    end if;
    if not exists (select 1 from rooms where room_type = it->>'room_type' and (v_zone is null or zone = v_zone) and active) then
      raise exception 'ไม่มีห้องประเภท % ในโซน %', it->>'room_type', coalesce(v_zone, '-');
    end if;
    for r in
      select rm.* from rooms rm
      where rm.active and rm.room_type = it->>'room_type' and (v_zone is null or rm.zone = v_zone)
        and (not v_ground or rm.floor = 1)
        and not exists (
          select 1 from bookings b where b.room_id = rm.id and b.status <> 'ยกเลิก'
            and daterange(b.check_in, b.check_out, '[)') && daterange(v_in, v_out, '[)'))
      order by rm.id limit v_cnt
      for update
    loop
      v_no := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id,
                            check_in, check_out, rate, created_by, channel, note)
      values (v_no, v_group, v_guest, v_name, v_phone, p->>'company', r.id,
              v_in, v_out, r.rate, v_by, coalesce(p->>'channel', 'LINE OA'),
              nullif(concat_ws(' · ', case when v_ground then 'ขอห้องชั้นล่าง' end, p->>'note'), ''));
      out_rows := out_rows || jsonb_build_object('booking_no', v_no, 'room_id', r.id, 'zone', r.zone, 'floor', r.floor,
                    'room_type', r.room_type, 'rate', r.rate, 'room_total', r.rate * (v_out - v_in));
      v_got := v_got + 1;
    end loop;
    if v_got < v_cnt then
      if v_ground then
        raise exception 'ห้องชั้นล่าง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
      end if;
      raise exception 'ห้อง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'group_no', v_group, 'check_in', v_in, 'check_out', v_out,
    'nights', v_out - v_in, 'bookings', out_rows,
    'room_total', (select coalesce(sum((x->>'room_total')::int), 0) from jsonb_array_elements(out_rows) x),
    'deposit_total', 300 * jsonb_array_length(out_rows));
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_availability', 'pp_book') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;


-- ---------- บันทึกการทำงานหน้าเคาน์เตอร์ (เช็คอิน รับเงิน มัดจำ เช็คเอาท์ ฯลฯ) ----------
create table if not exists ops (
  id         bigserial primary key,
  at         timestamptz not null default now(),
  role       text,                                 -- owner / staff
  kind       text not null,                        -- book, pay, dep_in, dep_out, checkin, checkout, credit, cancel, extend, room
  booking_no text,
  data       jsonb not null default '{}'::jsonb,
  undone     boolean not null default false,
  undo_info  jsonb
);
create index if not exists ops_booking on ops (booking_no);
alter table ops enable row level security;

-- ห้องปิดซ่อม (ยังอยู่ในระบบ แต่ไม่เปิดขาย)
alter table rooms add column if not exists closed boolean not null default false;

-- ห้องว่าง: ไม่นับห้องที่ปิด
create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not r.closed and not exists (
      select 1 from bookings b
      where b.room_id = r.id and b.status <> 'ยกเลิก'
        and daterange(b.check_in, b.check_out, '[)') && daterange(p_check_in, p_check_out, '[)'))
  )
  select jsonb_build_object(
    'check_in', p_check_in, 'check_out', p_check_out, 'nights', p_check_out - p_check_in,
    'types', coalesce((
      select jsonb_agg(jsonb_build_object(
        'zone', t.zone, 'room_type', t.room_type, 'rate', t.rate, 'max_guests', t.max_guests,
        'bed', t.bed, 'total_rooms', t.total,
        'free_rooms', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type),
        'free_ground_floor', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type and f.floor = 1))
        order by t.zone desc, t.rate, t.room_type)
      from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) total
            from rooms where active group by zone, room_type) t), '[]'::jsonb))
$$;

-- AI จองไม่ได้ในห้องที่ปิด
-- จองห้อง (ทำทั้งหมดหรือไม่ทำเลย)
-- p = {guest_name, phone, company, line_user_id, check_in, check_out, created_by, note, prefer_ground_floor,
--      items:[{zone, room_type, count}]}
-- prefer_ground_floor = true -> จัดเฉพาะห้องชั้น 1 ถ้าไม่พอจะไม่จอง (ให้พนักงานดูแลต่อ)
create or replace function pp_book(p jsonb) returns jsonb language plpgsql as $$
declare
  v_in date := (p->>'check_in')::date;
  v_out date := (p->>'check_out')::date;
  v_by text := coalesce(p->>'created_by', 'staff');
  v_name text := nullif(trim(p->>'guest_name'), '');
  v_phone text := nullif(regexp_replace(coalesce(p->>'phone', ''), '[^0-9+]', '', 'g'), '');
  v_ground boolean := coalesce((p->>'prefer_ground_floor')::boolean, false);
  v_guest uuid; v_group text; v_no text; v_total_rooms int := 0; v_zone text;
  it jsonb; r record; v_cnt int; v_got int; out_rows jsonb := '[]'::jsonb;
begin
  if v_name is null then raise exception 'ต้องมีชื่อผู้จอง'; end if;
  if v_phone is null or length(v_phone) < 9 then raise exception 'ต้องมีเบอร์โทรที่ถูกต้อง'; end if;
  if v_in is null or v_out is null or v_out <= v_in then raise exception 'วันเข้าพัก/วันออกไม่ถูกต้อง'; end if;
  if v_in < pp_today() then raise exception 'วันเข้าพักต้องไม่ใช่วันที่ผ่านมาแล้ว'; end if;
  if v_out - v_in > 30 then raise exception 'จองได้ครั้งละไม่เกิน 30 คืน'; end if;
  select coalesce(sum((x->>'count')::int), 0) into v_total_rooms from jsonb_array_elements(p->'items') x;
  if v_total_rooms < 1 then raise exception 'ต้องระบุจำนวนห้องอย่างน้อย 1 ห้อง'; end if;
  -- ราวกันตกชั้นที่ 3: AI ยืนยันเองได้ไม่เกิน 4 ห้อง (5 ห้องขึ้นไปส่งพนักงาน)
  if v_by = 'ai' and v_total_rooms > 4 then raise exception 'จอง 5 ห้องขึ้นไปต้องให้พนักงานยืนยัน'; end if;

  if p->>'line_user_id' is not null then
    insert into guests (full_name, phone, company, line_user_id, line_display_name)
    values (v_name, v_phone, p->>'company', p->>'line_user_id', p->>'line_display_name')
    on conflict (line_user_id) do update
      set full_name = excluded.full_name, phone = excluded.phone,
          company = coalesce(excluded.company, guests.company)
    returning id into v_guest;
  end if;

  v_group := case when v_total_rooms > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;

  for it in select * from jsonb_array_elements(p->'items') loop
    v_cnt := (it->>'count')::int; v_got := 0; v_zone := nullif(it->>'zone', '');
    if v_cnt is null or v_cnt < 1 then continue; end if;
    if v_zone is null and (select count(distinct zone) from rooms where room_type = it->>'room_type' and active) > 1 then
      raise exception 'ประเภท % มีทั้งโซนตึกใหม่และโซนบ้านหลัง ต้องระบุโซน', it->>'room_type';
    end if;
    if not exists (select 1 from rooms where room_type = it->>'room_type' and (v_zone is null or zone = v_zone) and active) then
      raise exception 'ไม่มีห้องประเภท % ในโซน %', it->>'room_type', coalesce(v_zone, '-');
    end if;
    for r in
      select rm.* from rooms rm
      where rm.active and rm.room_type = it->>'room_type' and (v_zone is null or rm.zone = v_zone)
        and (not v_ground or rm.floor = 1) and not rm.closed
        and not exists (
          select 1 from bookings b where b.room_id = rm.id and b.status <> 'ยกเลิก'
            and daterange(b.check_in, b.check_out, '[)') && daterange(v_in, v_out, '[)'))
      order by rm.id limit v_cnt
      for update
    loop
      v_no := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id,
                            check_in, check_out, rate, created_by, channel, note)
      values (v_no, v_group, v_guest, v_name, v_phone, p->>'company', r.id,
              v_in, v_out, r.rate, v_by, coalesce(p->>'channel', 'LINE OA'),
              nullif(concat_ws(' · ', case when v_ground then 'ขอห้องชั้นล่าง' end, p->>'note'), ''));
      out_rows := out_rows || jsonb_build_object('booking_no', v_no, 'room_id', r.id, 'zone', r.zone, 'floor', r.floor,
                    'room_type', r.room_type, 'rate', r.rate, 'room_total', r.rate * (v_out - v_in));
      v_got := v_got + 1;
    end loop;
    if v_got < v_cnt then
      if v_ground then
        raise exception 'ห้องชั้นล่าง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
      end if;
      raise exception 'ห้อง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'group_no', v_group, 'check_in', v_in, 'check_out', v_out,
    'nights', v_out - v_in, 'bookings', out_rows,
    'room_total', (select coalesce(sum((x->>'room_total')::int), 0) from jsonb_array_elements(out_rows) x),
    'deposit_total', 300 * jsonb_array_length(out_rows));
end $$;

create or replace function pp_room_closed(p_room text) returns boolean language sql stable as $$
  select coalesce((select closed from rooms where id = p_room), false)
$$;

-- วันที่จาก JSON (YYYY-MM-DD)
create or replace function pp_d(v text) returns date language sql immutable as $$ select v::date $$;

-- ---------- ปุ่มในหน้าจอ -> ฐานข้อมูล ----------
-- p = {k: ชนิด, no: เลขการจอง, ...}
create or replace function pp_act(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  v_no text := nullif(p->>'no', '');
  b bookings; r record; s jsonb; o ops;
  v_id bigint; v_group text; v_nos jsonb := '[]'::jsonb; v_new text; v_in date; v_out date;
  v_undo jsonb := '{}'::jsonb; v_cnt int;
begin
  if k is null then raise exception 'ไม่ระบุชนิดการบันทึก'; end if;

  if k = 'undo' then
    select * into o from ops where id = (p->>'id')::bigint and not undone;
    if o.id is null then return jsonb_build_object('ok', true, 'skip', true); end if;
    if o.kind = 'cancel' then
      update bookings set status = 'ยืนยันแล้ว' where booking_no = o.booking_no;
    elsif o.kind in ('extend', 'checkout') and o.undo_info ? 'prev_out' then
      update ops set undone = true where at = o.at and data->>'move' = 'true'
        and (booking_no = o.booking_no or booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]'))));
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update bookings set check_out = pp_d(o.undo_info->>'prev_out') where booking_no = o.booking_no;
    elsif o.kind = 'extend' then
      update ops set undone = true where at = o.at and data->>'move' = 'true'
        and (booking_no = o.booking_no or booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]'))));
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    elsif o.kind = 'room' then
      update rooms set closed = (o.undo_info->>'prev_closed')::boolean where id = o.data->>'room';
    elsif o.kind = 'book' then
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update ops set undone = true where kind = 'pay' and booking_no in
        (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    end if;
    update ops set undone = true where id = o.id;
    return jsonb_build_object('ok', true, 'undone', o.id);
  end if;

  if k = 'book' then
    -- พนักงานจองเอง: เลือกห้องเอง {guest, phone, company, check_in, check_out, rooms:[{room}], channel, note, paid, m}
    v_in := pp_d(p->>'check_in'); v_out := pp_d(p->>'check_out');
    if nullif(trim(p->>'guest'), '') is null then raise exception 'ต้องมีชื่อผู้เข้าพัก'; end if;
    if v_out <= v_in then raise exception 'วันออกต้องหลังวันเข้าพัก'; end if;
    v_cnt := jsonb_array_length(coalesce(p->'rooms', '[]'));
    if v_cnt < 1 then raise exception 'ต้องเลือกห้องอย่างน้อย 1 ห้อง'; end if;
    v_group := case when v_cnt > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;
    for s in select * from jsonb_array_elements(p->'rooms') loop
      select * into r from rooms where id = s->>'room' and active;
      if r.id is null then raise exception 'ไม่มีห้อง %', s->>'room'; end if;
      v_new := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_name, phone, company, room_id, check_in, check_out, rate,
                            created_by, channel, note)
      values (v_new, v_group, coalesce(nullif(trim(s->>'guest'), ''), trim(p->>'guest')), nullif(p->>'phone', ''),
              nullif(p->>'company', ''), r.id, v_in, v_out, coalesce((s->>'rate')::int, r.rate),
              'staff', coalesce(nullif(p->>'channel', ''), 'Walk-in'), nullif(p->>'note', ''));
      v_nos := v_nos || to_jsonb(v_new);
      if coalesce((p->>'paid')::boolean, false) then
        insert into ops (role, kind, booking_no, data) values (p_role, 'pay', v_new,
          jsonb_build_object('m', coalesce(p->>'m', 'cash'), 'room_amt', coalesce((s->>'rate')::int, r.rate) * (v_out - v_in)));
      end if;
    end loop;
    v_undo := jsonb_build_object('new_nos', v_nos);
    v_no := v_nos->>0;

  elsif k = 'cancel' then
    update bookings set status = 'ยกเลิก' where booking_no = v_no and status <> 'ยกเลิก';

  elsif k = 'extend' then
    -- พักต่อ {no, segs:[{room, from: YYYY-MM-DD, n, rate}]}
    select * into b from bookings where booking_no = v_no;
    if b.id is null then raise exception 'ไม่พบการจอง %', v_no; end if;
    v_undo := jsonb_build_object('prev_out', b.check_out);
    for s in select * from jsonb_array_elements(p->'segs') loop
      v_in := pp_d(s->>'from'); v_out := v_in + (s->>'n')::int;
      if s->>'room' = b.room_id and v_in = (select check_out from bookings where id = b.id) then
        update bookings set check_out = v_out where id = b.id;
      else
        if pp_room_closed(s->>'room') then raise exception 'ห้อง % ปิดอยู่', s->>'room'; end if;
        v_new := pp_next_booking_no();
        insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id, check_in, check_out,
                              rate, created_by, channel, note)
        values (v_new, b.group_no, b.guest_id, b.guest_name, b.phone, b.company, s->>'room', v_in, v_out,
                coalesce((s->>'rate')::int, b.rate), 'staff', 'Walk-in', 'พักต่อจาก ' || v_no);
        v_nos := v_nos || to_jsonb(v_new);
      end if;
    end loop;
    v_undo := v_undo || jsonb_build_object('new_nos', v_nos);
    -- ย้ายห้องทันที: ห้องเดิมเช็คเอาท์ ห้องใหม่เข้าพักเลย
    if coalesce((p->>'move_now')::boolean, false) and jsonb_array_length(v_nos) > 0 then
      insert into ops (role, kind, booking_no, data) values
        (p_role, 'checkout', v_no, '{"move": true}'), (p_role, 'checkin', v_nos->>0, '{"move": true}');
    end if;

  elsif k = 'checkout' and p ? 'nights' then
    -- เช็คเอาท์ก่อนกำหนด: คิดเฉพาะคืนที่พักจริง ห้องว่างให้จองต่อได้
    select * into b from bookings where booking_no = v_no;
    if b.id is not null and b.check_in + (p->>'nights')::int < b.check_out then
      v_undo := jsonb_build_object('prev_out', b.check_out);
      update bookings set check_out = b.check_in + greatest(1, (p->>'nights')::int) where id = b.id;
    end if;

  elsif k = 'room' then
    -- เปิด/ปิดห้อง {room, open}
    select * into r from rooms where id = p->>'room';
    if r.id is null then raise exception 'ไม่มีห้อง %', p->>'room'; end if;
    v_undo := jsonb_build_object('prev_closed', r.closed);
    update rooms set closed = not coalesce((p->>'open')::boolean, true) where id = r.id;

  elsif k not in ('pay', 'dep_in', 'dep_out', 'checkin', 'checkout', 'credit') then
    raise exception 'ไม่รู้จักการบันทึกชนิด %', k;
  end if;

  if v_no is not null and k <> 'book' and not exists (select 1 from bookings where booking_no = v_no) then
    raise exception 'ไม่พบการจอง % ในฐานข้อมูล', v_no;
  end if;

  insert into ops (role, kind, booking_no, data, undo_info)
  values (p_role, k, v_no, p - 'k' - 'no', v_undo) returning id into v_id;
  return jsonb_build_object('ok', true, 'id', v_id, 'nos', v_nos);
end $$;

-- ค่าที่เปลี่ยนเมื่อข้อมูลเปลี่ยน (นับการบันทึกหน้าเคาน์เตอร์ด้วย)
create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed))
$$;

-- ข้อมูลทั้งหมดที่หน้าจอใช้
create or replace function pp_export() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'stamp', pp_stamp(),
    'bookings', coalesce((select jsonb_agg(to_jsonb(b) - 'id' order by b.booking_no) from bookings b), '[]'),
    'guests', coalesce((select jsonb_agg(to_jsonb(g)) from guests g), '[]'),
    'threads', coalesce((select jsonb_agg(jsonb_build_object('id', t.id, 'line_user_id', t.line_user_id,
        'display_name', t.display_name, 'needs_staff', t.needs_staff, 'is_seed', t.is_seed,
        'messages', (select coalesce(jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'at', created_at)
                       order by created_at, id), '[]') from chat_messages m where m.thread_id = t.id))
        order by t.id)
      from chat_threads t where not t.is_seed), '[]'),
    'ops', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'at', at, 'role', role, 'kind', kind,
        'no', booking_no, 'data', data) order by id) from ops where not undone), '[]'),
    'closed_rooms', coalesce((select jsonb_agg(id order by id) from rooms where closed), '[]'))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_availability', 'pp_book', 'pp_room_closed', 'pp_d', 'pp_act', 'pp_stamp', 'pp_export') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
grant all on table ops to service_role;
grant all on sequence ops_id_seq to service_role;

-- ---------- กฎวันจริง (25 ต.ค. 2569) ----------
-- 1) เลยวันเข้าพัก (ถึง 06:00 วันถัดไป) แล้วไม่ได้เช็คอิน -> ยกเลิก (ไม่มาตามนัด) ห้องว่างให้ขายต่อ
-- 2) แขกที่เช็คอินแล้วแต่ยังไม่กดเช็คเอาท์ ถือว่ายังอยู่ในห้อง (AI จองห้องนั้นวันนี้ไม่ได้)
-- ใช้กับการจองจริง และข้อมูลตัวอย่างที่เข้าพักตั้งแต่ 25 ต.ค. 2569 (วันเริ่มใช้งานจริง)
create or replace function pp_checked_in(p_no text) returns boolean language sql stable as $$
  select exists (select 1 from ops o where o.booking_no = p_no and o.kind = 'checkin' and not o.undone)
      or exists (select 1 from bookings b where b.booking_no = p_no and b.created_by = 'seed' and b.check_in < date '2026-10-25')
$$;

create or replace function pp_noshow() returns int language plpgsql as $$
declare n int;
begin
  with x as (
    update bookings b set status = 'ยกเลิก'
    where b.status <> 'ยกเลิก' and (b.created_by <> 'seed' or b.check_in >= date '2026-10-25')
      and b.check_in < ((now() at time zone 'Asia/Bangkok') - interval '6 hours')::date
      and not pp_checked_in(b.booking_no)
    returning b.booking_no)
  insert into ops (role, kind, booking_no, data)
  select 'system', 'cancel', booking_no, '{"why": "ไม่มาตามนัด (ระบบยกเลิกอัตโนมัติเมื่อเลยวันเข้าพัก)", "noshow": true}'::jsonb from x;
  get diagnostics n = row_count;
  return n;
end $$;

create or replace function pp_availability(p_check_in date, p_check_out date)
returns jsonb language sql stable as $$
  with free as (
    select r.* from rooms r
    where r.active and not r.closed and not exists (
      select 1 from bookings b
      where b.room_id = r.id and b.status <> 'ยกเลิก'
        and daterange(b.check_in, b.check_out, '[)') && daterange(p_check_in, p_check_out, '[)'))
      and not exists (   -- แขกที่เช็คอินแล้วแต่ยังไม่กดเช็คเอาท์ (เลยวันออก) ยังอยู่ในห้อง
        select 1 from bookings b2
        where b2.room_id = r.id and b2.status <> 'ยกเลิก' and b2.check_out <= pp_today() and p_check_in <= pp_today()
          and b2.check_out >= date '2026-10-25' and pp_checked_in(b2.booking_no)
          and not exists (select 1 from ops ox where ox.booking_no = b2.booking_no and ox.kind = 'checkout' and not ox.undone))
  )
  select jsonb_build_object(
    'check_in', p_check_in, 'check_out', p_check_out, 'nights', p_check_out - p_check_in,
    'types', coalesce((
      select jsonb_agg(jsonb_build_object(
        'zone', t.zone, 'room_type', t.room_type, 'rate', t.rate, 'max_guests', t.max_guests,
        'bed', t.bed, 'total_rooms', t.total,
        'free_rooms', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type),
        'free_ground_floor', (select count(*) from free f where f.zone = t.zone and f.room_type = t.room_type and f.floor = 1))
        order by t.zone desc, t.rate, t.room_type)
      from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) total
            from rooms where active group by zone, room_type) t), '[]'::jsonb))
$$;

create or replace function pp_book(p jsonb) returns jsonb language plpgsql as $$
declare
  v_in date := (p->>'check_in')::date;
  v_out date := (p->>'check_out')::date;
  v_by text := coalesce(p->>'created_by', 'staff');
  v_name text := nullif(trim(p->>'guest_name'), '');
  v_phone text := nullif(regexp_replace(coalesce(p->>'phone', ''), '[^0-9+]', '', 'g'), '');
  v_ground boolean := coalesce((p->>'prefer_ground_floor')::boolean, false);
  v_guest uuid; v_group text; v_no text; v_total_rooms int := 0; v_zone text;
  it jsonb; r record; v_cnt int; v_got int; out_rows jsonb := '[]'::jsonb;
begin
  if v_name is null then raise exception 'ต้องมีชื่อผู้จอง'; end if;
  if v_phone is null or length(v_phone) < 9 then raise exception 'ต้องมีเบอร์โทรที่ถูกต้อง'; end if;
  if v_in is null or v_out is null or v_out <= v_in then raise exception 'วันเข้าพัก/วันออกไม่ถูกต้อง'; end if;
  if v_in < pp_today() then raise exception 'วันเข้าพักต้องไม่ใช่วันที่ผ่านมาแล้ว'; end if;
  if v_out - v_in > 30 then raise exception 'จองได้ครั้งละไม่เกิน 30 คืน'; end if;
  select coalesce(sum((x->>'count')::int), 0) into v_total_rooms from jsonb_array_elements(p->'items') x;
  if v_total_rooms < 1 then raise exception 'ต้องระบุจำนวนห้องอย่างน้อย 1 ห้อง'; end if;
  -- ราวกันตกชั้นที่ 3: AI ยืนยันเองได้ไม่เกิน 4 ห้อง (5 ห้องขึ้นไปส่งพนักงาน)
  if v_by = 'ai' and v_total_rooms > 4 then raise exception 'จอง 5 ห้องขึ้นไปต้องให้พนักงานยืนยัน'; end if;

  if p->>'line_user_id' is not null then
    insert into guests (full_name, phone, company, line_user_id, line_display_name)
    values (v_name, v_phone, p->>'company', p->>'line_user_id', p->>'line_display_name')
    on conflict (line_user_id) do update
      set full_name = excluded.full_name, phone = excluded.phone,
          company = coalesce(excluded.company, guests.company)
    returning id into v_guest;
  end if;

  v_group := case when v_total_rooms > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;

  for it in select * from jsonb_array_elements(p->'items') loop
    v_cnt := (it->>'count')::int; v_got := 0; v_zone := nullif(it->>'zone', '');
    if v_cnt is null or v_cnt < 1 then continue; end if;
    if v_zone is null and (select count(distinct zone) from rooms where room_type = it->>'room_type' and active) > 1 then
      raise exception 'ประเภท % มีทั้งโซนตึกใหม่และโซนบ้านหลัง ต้องระบุโซน', it->>'room_type';
    end if;
    if not exists (select 1 from rooms where room_type = it->>'room_type' and (v_zone is null or zone = v_zone) and active) then
      raise exception 'ไม่มีห้องประเภท % ในโซน %', it->>'room_type', coalesce(v_zone, '-');
    end if;
    for r in
      select rm.* from rooms rm
      where rm.active and rm.room_type = it->>'room_type' and (v_zone is null or rm.zone = v_zone)
        and (not v_ground or rm.floor = 1) and not rm.closed
        and not exists (
          select 1 from bookings b where b.room_id = rm.id and b.status <> 'ยกเลิก'
            and daterange(b.check_in, b.check_out, '[)') && daterange(v_in, v_out, '[)'))
        and not exists (
          select 1 from bookings b2
          where b2.room_id = rm.id and b2.status <> 'ยกเลิก' and b2.check_out <= pp_today() and v_in <= pp_today()
            and b2.check_out >= date '2026-10-25' and pp_checked_in(b2.booking_no)
            and not exists (select 1 from ops ox where ox.booking_no = b2.booking_no and ox.kind = 'checkout' and not ox.undone))
      order by rm.id limit v_cnt
      for update
    loop
      v_no := pp_next_booking_no();
      insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id,
                            check_in, check_out, rate, created_by, channel, note)
      values (v_no, v_group, v_guest, v_name, v_phone, p->>'company', r.id,
              v_in, v_out, r.rate, v_by, coalesce(p->>'channel', 'LINE OA'),
              nullif(concat_ws(' · ', case when v_ground then 'ขอห้องชั้นล่าง' end, p->>'note'), ''));
      out_rows := out_rows || jsonb_build_object('booking_no', v_no, 'room_id', r.id, 'zone', r.zone, 'floor', r.floor,
                    'room_type', r.room_type, 'rate', r.rate, 'room_total', r.rate * (v_out - v_in));
      v_got := v_got + 1;
    end loop;
    if v_got < v_cnt then
      if v_ground then
        raise exception 'ห้องชั้นล่าง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
      end if;
      raise exception 'ห้อง % % ว่างไม่พอ (ต้องการ % ว่าง %)', coalesce(v_zone, ''), it->>'room_type', v_cnt, v_got;
    end if;
  end loop;

  return jsonb_build_object('ok', true, 'group_no', v_group, 'check_in', v_in, 'check_out', v_out,
    'nights', v_out - v_in, 'bookings', out_rows,
    'room_total', (select coalesce(sum((x->>'room_total')::int), 0) from jsonb_array_elements(out_rows) x),
    'deposit_total', 300 * jsonb_array_length(out_rows));
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_noshow', 'pp_checked_in', 'pp_availability', 'pp_book') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;

-- ---------- รายละเอียดการจองครบ + ตั้งค่าห้องบันทึกจริง (25 ต.ค. 2569) ----------
alter table bookings add column if not exists details jsonb;

create or replace function pp_act(p jsonb, p_role text) returns jsonb language plpgsql as $$
declare
  k text := p->>'k';
  v_no text := nullif(p->>'no', '');
  b bookings; r record; s jsonb; o ops;
  v_id bigint; v_group text; v_nos jsonb := '[]'::jsonb; v_new text; v_in date; v_out date;
  v_undo jsonb := '{}'::jsonb; v_cnt int; v_net int;
begin
  if k is null then raise exception 'ไม่ระบุชนิดการบันทึก'; end if;

  if k = 'undo' then
    select * into o from ops where id = (p->>'id')::bigint and not undone;
    if o.id is null then return jsonb_build_object('ok', true, 'skip', true); end if;
    if o.kind = 'cancel' then
      update bookings set status = 'ยืนยันแล้ว' where booking_no = o.booking_no;
    elsif o.kind in ('extend', 'checkout') and o.undo_info ? 'prev_out' then
      update ops set undone = true where at = o.at and data->>'move' = 'true'
        and (booking_no = o.booking_no or booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]'))));
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update bookings set check_out = pp_d(o.undo_info->>'prev_out') where booking_no = o.booking_no;
    elsif o.kind = 'extend' then
      update ops set undone = true where at = o.at and data->>'move' = 'true'
        and (booking_no = o.booking_no or booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]'))));
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    elsif o.kind = 'room' then
      update rooms set closed = (o.undo_info->>'prev_closed')::boolean where id = o.data->>'room';
    elsif o.kind = 'roomtype' then
      update rooms rr set room_type = x->>'type', rate = (x->>'rate')::int
      from jsonb_array_elements(coalesce(o.undo_info->'rooms', '[]')) x where rr.id = x->>'id';
    elsif o.kind = 'roomset' then
      if o.undo_info ? 'prev' then
        update rooms set zone = o.undo_info->'prev'->>'zone', room_type = o.undo_info->'prev'->>'room_type',
          rate = (o.undo_info->'prev'->>'rate')::int, max_guests = (o.undo_info->'prev'->>'max_guests')::int,
          closed = (o.undo_info->'prev'->>'closed')::boolean where id = o.data->>'room';
      else
        update rooms set active = false where id = upper(o.data->>'room');
      end if;
    elsif o.kind = 'book' then
      delete from bookings where booking_no in (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
      update ops set undone = true where kind in ('pay', 'credit') and booking_no in
        (select jsonb_array_elements_text(coalesce(o.undo_info->'new_nos', '[]')));
    end if;
    update ops set undone = true where id = o.id;
    return jsonb_build_object('ok', true, 'undone', o.id);
  end if;

  if k = 'book' then
    -- พนักงานจองเอง {guest, phone, company, check_in, check_out, channel, note, pay: now|later|dep|credit, m, cred_days,
    --               details:{adults, kids, purpose, email, code, co:{name,tax,addr,hq}, tax:{...}, payer, po},
    --               rooms:[{room, rate, guest, bf, disc, pax}]}
    v_in := pp_d(p->>'check_in'); v_out := pp_d(p->>'check_out');
    if nullif(trim(p->>'guest'), '') is null then raise exception 'ต้องมีชื่อผู้เข้าพัก'; end if;
    if v_out <= v_in then raise exception 'วันออกต้องหลังวันเข้าพัก'; end if;
    v_cnt := jsonb_array_length(coalesce(p->'rooms', '[]'));
    if v_cnt < 1 then raise exception 'ต้องเลือกห้องอย่างน้อย 1 ห้อง'; end if;
    v_group := case when v_cnt > 1 then 'G' || to_char(now(), 'YYMMDDHH24MISS') end;
    for s in select * from jsonb_array_elements(p->'rooms') loop
      select * into r from rooms where id = s->>'room' and active;
      if r.id is null then raise exception 'ไม่มีห้อง %', s->>'room'; end if;
      v_new := pp_next_booking_no();
      v_net := coalesce((s->>'rate')::int, r.rate) * (v_out - v_in) + coalesce((s->>'bf')::int, 0) - coalesce((s->>'disc')::int, 0);
      insert into bookings (booking_no, group_no, guest_name, phone, company, room_id, check_in, check_out, rate,
                            created_by, channel, note, details)
      values (v_new, v_group, coalesce(nullif(trim(s->>'guest'), ''), trim(p->>'guest')), nullif(p->>'phone', ''),
              nullif(p->>'company', ''), r.id, v_in, v_out, coalesce((s->>'rate')::int, r.rate),
              'staff', coalesce(nullif(p->>'channel', ''), 'Walk-in'), nullif(p->>'note', ''),
              coalesce(p->'details', '{}'::jsonb) || jsonb_build_object('bf', coalesce((s->>'bf')::int, 0),
                'disc', coalesce((s->>'disc')::int, 0), 'pax', coalesce((s->>'pax')::int, 1), 'pay', coalesce(p->>'pay', 'later'),
                'cred_days', coalesce((p->>'cred_days')::int, 30)));
      v_nos := v_nos || to_jsonb(v_new);
      if coalesce(p->>'pay', case when coalesce((p->>'paid')::boolean, false) then 'now' end) = 'now' then
        insert into ops (role, kind, booking_no, data) values (p_role, 'pay', v_new,
          jsonb_build_object('m', coalesce(p->>'m', 'cash'), 'room_amt', v_net));
      elsif p->>'pay' = 'dep' then        -- บริษัทจ่ายมัดจำ 30% ที่เหลือชำระภายหลัง
        insert into ops (role, kind, booking_no, data) values (p_role, 'pay', v_new,
          jsonb_build_object('m', coalesce(p->>'m', 'transfer'), 'room_amt', round(v_net * 0.3)::int, 'partial', true));
      elsif p->>'pay' = 'credit' then
        insert into ops (role, kind, booking_no, data) values (p_role, 'credit', v_new,
          jsonb_build_object('days', coalesce((p->>'cred_days')::int, 30)));
      end if;
    end loop;
    v_undo := jsonb_build_object('new_nos', v_nos);
    v_no := v_nos->>0;

  elsif k = 'cancel' then
    update bookings set status = 'ยกเลิก' where booking_no = v_no and status <> 'ยกเลิก';

  elsif k = 'extend' then
    -- พักต่อ {no, segs:[{room, from: YYYY-MM-DD, n, rate}]}
    select * into b from bookings where booking_no = v_no;
    if b.id is null then raise exception 'ไม่พบการจอง %', v_no; end if;
    v_undo := jsonb_build_object('prev_out', b.check_out);
    for s in select * from jsonb_array_elements(p->'segs') loop
      v_in := pp_d(s->>'from'); v_out := v_in + (s->>'n')::int;
      if s->>'room' = b.room_id and v_in = (select check_out from bookings where id = b.id) then
        update bookings set check_out = v_out where id = b.id;
      else
        if pp_room_closed(s->>'room') then raise exception 'ห้อง % ปิดอยู่', s->>'room'; end if;
        v_new := pp_next_booking_no();
        insert into bookings (booking_no, group_no, guest_id, guest_name, phone, company, room_id, check_in, check_out,
                              rate, created_by, channel, note)
        values (v_new, b.group_no, b.guest_id, b.guest_name, b.phone, b.company, s->>'room', v_in, v_out,
                coalesce((s->>'rate')::int, b.rate), 'staff', 'Walk-in', 'พักต่อจาก ' || v_no);
        v_nos := v_nos || to_jsonb(v_new);
      end if;
    end loop;
    v_undo := v_undo || jsonb_build_object('new_nos', v_nos);
    -- ย้ายห้องทันที: ห้องเดิมเช็คเอาท์ ห้องใหม่เข้าพักเลย
    if coalesce((p->>'move_now')::boolean, false) and jsonb_array_length(v_nos) > 0 then
      insert into ops (role, kind, booking_no, data) values
        (p_role, 'checkout', v_no, '{"move": true}'), (p_role, 'checkin', v_nos->>0, '{"move": true}');
    end if;

  elsif k = 'checkout' and p ? 'nights' then
    -- เช็คเอาท์ก่อนกำหนด: คิดเฉพาะคืนที่พักจริง ห้องว่างให้จองต่อได้
    select * into b from bookings where booking_no = v_no;
    if b.id is not null and b.check_in + (p->>'nights')::int < b.check_out then
      v_undo := jsonb_build_object('prev_out', b.check_out);
      update bookings set check_out = b.check_in + greatest(1, (p->>'nights')::int) where id = b.id;
    end if;

  elsif k = 'room' then
    -- เปิด/ปิดห้อง {room, open}
    select * into r from rooms where id = p->>'room';
    if r.id is null then raise exception 'ไม่มีห้อง %', p->>'room'; end if;
    v_undo := jsonb_build_object('prev_closed', r.closed);
    update rooms set closed = not coalesce((p->>'open')::boolean, true) where id = r.id;

  elsif k = 'roomtype' then
    -- ตั้งค่าประเภทห้อง (ทั้งกลุ่ม) {zone, type, new_type, rate}
    if nullif(trim(p->>'new_type'), '') is null then raise exception 'ต้องมีชื่อประเภทห้อง'; end if;
    if coalesce((p->>'rate')::int, 0) <= 0 then raise exception 'ราคาต้องมากกว่า 0'; end if;
    v_undo := jsonb_build_object('rooms', (select jsonb_agg(jsonb_build_object('id', id, 'type', room_type, 'rate', rate))
                                           from rooms where zone = p->>'zone' and room_type = p->>'type'));
    update rooms set room_type = trim(p->>'new_type'), rate = (p->>'rate')::int
    where zone = p->>'zone' and room_type = p->>'type';
    get diagnostics v_cnt = row_count;
    if v_cnt = 0 then raise exception 'ไม่พบประเภทห้อง % ในโซน %', p->>'type', p->>'zone'; end if;

  elsif k = 'roomset' then
    -- เพิ่มห้อง / แก้ห้องรายตัว {room, zone, type, rate, max, open}
    if nullif(trim(p->>'room'), '') is null then raise exception 'ต้องมีรหัสห้อง'; end if;
    v_undo := coalesce((select jsonb_build_object('prev', to_jsonb(rr)) from rooms rr where id = p->>'room'), '{"new": true}'::jsonb);
    insert into rooms (id, zone, room_type, bed, rate, max_guests, floor, closed)
    values (upper(trim(p->>'room')), p->>'zone', trim(p->>'type'),
            coalesce(nullif(trim(p->>'bed'), ''), (select bed from rooms where zone = p->>'zone' and room_type = trim(p->>'type') limit 1)),
            (p->>'rate')::int, coalesce((p->>'max')::int, 2),
            case when upper(p->>'room') like 'B%' then 2 else 1 end, not coalesce((p->>'open')::boolean, true))
    on conflict (id) do update set zone = excluded.zone, room_type = excluded.room_type, rate = excluded.rate,
      max_guests = excluded.max_guests, closed = excluded.closed, active = true,
      bed = coalesce(excluded.bed, rooms.bed);

  elsif k not in ('pay', 'dep_in', 'dep_out', 'checkin', 'checkout', 'credit') then
    raise exception 'ไม่รู้จักการบันทึกชนิด %', k;
  end if;

  if v_no is not null and k <> 'book' and not exists (select 1 from bookings where booking_no = v_no) then
    raise exception 'ไม่พบการจอง % ในฐานข้อมูล', v_no;
  end if;

  insert into ops (role, kind, booking_no, data, undo_info)
  values (p_role, k, v_no, p - 'k' - 'no', v_undo) returning id into v_id;
  return jsonb_build_object('ok', true, 'id', v_id, 'nos', v_nos);
end $$;

create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed),
    (select md5(string_agg(id || room_type || rate || max_guests || active::text, ',' order by id)) from rooms))
$$;

create or replace function pp_export() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'stamp', pp_stamp(),
    'bookings', coalesce((select jsonb_agg(to_jsonb(b) - 'id' order by b.booking_no) from bookings b), '[]'),
    'guests', coalesce((select jsonb_agg(to_jsonb(g)) from guests g), '[]'),
    'threads', coalesce((select jsonb_agg(jsonb_build_object('id', t.id, 'line_user_id', t.line_user_id,
        'display_name', t.display_name, 'needs_staff', t.needs_staff, 'is_seed', t.is_seed,
        'messages', (select coalesce(jsonb_agg(jsonb_build_object('sender', sender, 'body', body, 'at', created_at)
                       order by created_at, id), '[]') from chat_messages m where m.thread_id = t.id))
        order by t.id)
      from chat_threads t where not t.is_seed), '[]'),
    'ops', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'at', at, 'role', role, 'kind', kind,
        'no', booking_no, 'data', data) order by id) from ops where not undone), '[]'),
    'closed_rooms', coalesce((select jsonb_agg(id order by id) from rooms where closed), '[]'),
    'rooms', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'zone', zone, 'room_type', room_type, 'bed', bed,
        'rate', rate, 'max_guests', max_guests, 'floor', floor, 'closed', closed) order by id) from rooms where active), '[]'))
$$;

-- ประเภทห้องปัจจุบัน (ให้ AI ใช้ราคา/ชื่อล่าสุดที่เจ้าของตั้ง)
create or replace function pp_room_types() returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(jsonb_build_object('zone', zone, 'room_type', room_type, 'rate', rate, 'max_guests', max_guests,
    'bed', bed, 'rooms', n, 'ground_floor', g) order by zone desc, rate, room_type), '[]')
  from (select zone, room_type, max(rate) rate, max(max_guests) max_guests, max(bed) bed, count(*) n,
               count(*) filter (where floor = 1) g
        from rooms where active and not closed group by zone, room_type) t
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_act', 'pp_stamp', 'pp_export', 'pp_room_types') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;

-- ---------- 07 หน้าแชท LINE บันทึกจริง (25 ต.ค. 2569) ----------

-- สถานะที่พนักงานตั้งให้แต่ละแชท (ทั้งแชทจริงจาก LINE และแชทตัวอย่าง)
-- key: แชทจริง = 'db:<chat_threads.id>' · แชทตัวอย่าง = รหัสแชทในข้อมูลตัวอย่าง เช่น 'T0001'
create table if not exists chat_state (
  key        text primary key,
  alias      text,                                   -- ชื่อแชทที่พนักงานตั้งเอง
  notes      jsonb not null default '[]'::jsonb,     -- หมายเหตุ
  closed_at  timestamptz,                            -- ปิดเคสล่าสุด
  read_at    timestamptz,                            -- เปิดอ่านล่าสุด
  sent       jsonb not null default '[]'::jsonb,     -- ข้อความที่พนักงานพิมพ์ในแชทตัวอย่าง (ไม่ได้ส่งเข้า LINE)
  updated_at timestamptz not null default now()
);
alter table chat_state enable row level security;

-- LINE user id ของแชทจริง (ใช้ตอนส่งข้อความเข้า LINE) · แชทตัวอย่างคืน null
create or replace function pp_chat_target(p_key text) returns text language sql stable as $$
  select t.line_user_id from chat_threads t
  where p_key like 'db:%' and t.id = nullif(substr(p_key, 4), '')::bigint and not t.is_seed
$$;

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
      values (v_tid, 'พนักงาน', v_body, jsonb_build_object('by', p_role, 'line', coalesce(p->>'line', 'sent')));
      update chat_threads set needs_staff = false, handoff_reason = null, last_message_at = now() where id = v_tid;
    else
      update chat_state set sent = sent || jsonb_build_array(jsonb_build_object('body', v_body, 'at', now(), 'by', p_role))
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

create or replace function pp_chat_state() returns jsonb language sql stable as $$
  select coalesce(jsonb_object_agg(key, jsonb_build_object('alias', alias, 'notes', notes, 'closed_at', closed_at,
           'read_at', read_at, 'sent', sent)), '{}'::jsonb) from chat_state
$$;

-- ตัวบอกว่าข้อมูลเปลี่ยน (หน้าจอทุกเครื่องจะดึงข้อมูลใหม่) — เพิ่มสถานะแชท
create or replace function pp_stamp() returns text language sql stable as $$
  select concat_ws('|', pp_today(),
    (select count(*) from bookings), (select max(created_at) from bookings),
    (select count(*) from bookings where status = 'ยกเลิก'),
    (select count(*) from chat_messages), (select count(*) from chat_threads where needs_staff),
    (select coalesce(max(id), 0) from ops), (select count(*) from ops where undone),
    (select count(*) from rooms where closed),
    (select md5(string_agg(id || room_type || rate || max_guests || active::text, ',' order by id)) from rooms),
    (select count(*) || '/' || coalesce(max(updated_at)::text, '') from chat_state))
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_chat', 'pp_chat_target', 'pp_chat_state', 'pp_stamp') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
