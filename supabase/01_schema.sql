-- PROMPT PAK · ฐานข้อมูลระบบจริง (เฟส 1: จองผ่าน LINE + AI)
-- วิธีใช้: เปิด Supabase > SQL Editor > วางทั้งไฟล์นี้ > Run (รันซ้ำได้ ไม่ลบข้อมูลเดิม)

create extension if not exists btree_gist;

-- ---------- ตาราง ----------
create table if not exists rooms (
  id          text primary key,                       -- A001..A016, B001..B015
  zone        text not null check (zone in ('ตึก','บ้าน')),
  room_type   text not null,                          -- สแตนดาร์ด (เตียงคู่) / ดีลักซ์ (เตียงใหญ่) / บ้านพัก / บ้านพัก (ใหญ่)
  bed         text,
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

create or replace function pp_handoff(p_line_user_id text, p_reason text) returns void language sql as $$
  update chat_threads set needs_staff = true, handoff_reason = p_reason where line_user_id = p_line_user_id
$$;

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
