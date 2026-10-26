-- PROMPT PAK · ศูนย์ไอเดีย: Agent Insight (วิเคราะห์ข้อมูลจริงวันละครั้ง) + ข่าวรอบโรงแรม (AI ค้นเว็บสัปดาห์ละครั้ง)
-- วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)
begin;

-- ผลงานของ AI ที่เก็บไว้ใช้ซ้ำ (insight = รายวัน, news = รายสัปดาห์)
create table if not exists ai_feed (
  key        text primary key,
  value      jsonb,
  busy_at    timestamptz,
  updated_at timestamptz not null default now()
);
alter table ai_feed enable row level security;

create or replace function pp_feed_get(p_key text) returns jsonb language sql stable as $$
  select value from ai_feed where key = p_key
$$;

-- กันเรียก AI ซ้อนกันหลายเครื่อง: จองคิว 3 นาที · true = ได้คิว
create or replace function pp_feed_lock(p_key text) returns boolean language plpgsql as $$
declare n int;
begin
  insert into ai_feed (key) values (p_key) on conflict (key) do nothing;
  update ai_feed set busy_at = now() where key = p_key and (busy_at is null or busy_at < now() - interval '3 minutes');
  get diagnostics n = row_count;
  return n > 0;
end $$;

create or replace function pp_feed_put(p_key text, p_value jsonb) returns void language sql as $$
  insert into ai_feed (key, value, busy_at, updated_at) values (p_key, p_value, null, now())
  on conflict (key) do update set value = coalesce(excluded.value, ai_feed.value), busy_at = null, updated_at = now()
$$;

-- ตัวเลขรวมจากข้อมูลจริงในระบบ ให้ Agent Insight วิเคราะห์ (ไม่มีชื่อ/เบอร์ลูกค้า)
create or replace function pp_insight_data() returns jsonb language sql stable as $$
  with d as (select pp_today() as today, (select count(*) from rooms where active)::int as nroom),
  act as (select * from bookings where status <> 'ยกเลิก'),
  rng as (select greatest(min(check_in), (select today from d) - 60) as a,
                 least(max(check_out), (select today from d) + 60) as b from act),
  days as (select g::date as day from rng, generate_series(rng.a, rng.b - 1, interval '1 day') g),
  occ as (select x.day, extract(dow from x.day)::int as dow,
                 (select count(*) from act where check_in <= x.day and check_out > x.day)::int as n
          from days x),
  gst as (select coalesce(nullif(regexp_replace(phone, '\D', '', 'g'), ''), guest_name) as gk,
                 count(distinct check_in) as stays, max(check_out) as last_out,
                 bool_or(check_in > (select today from d)) as upcoming,
                 (array_agg(channel order by check_in))[1] as first_ch
          from act group by 1),
  co as (select company, count(*)::int as bookings, sum(nights)::int as room_nights, sum(room_total)::int as revenue,
                max(check_out) as last_out,
                count(*) filter (where check_in > (select today from d))::int as upcoming_rooms
         from act where coalesce(company, '') <> '' group by company)
  select jsonb_build_object(
    'today', (select today from d),
    'rooms_total', (select nroom from d),
    'data_from', (select min(check_in) from act),
    'data_to', (select max(check_out) from act),
    'bookings', jsonb_build_object(
       'active', (select count(*) from act),
       'cancelled', (select count(*) from bookings where status = 'ยกเลิก'),
       'sample_seed', (select count(*) from act where created_by = 'seed'),
       'by_staff', (select count(*) from act where created_by = 'staff'),
       'by_ai_line', (select count(*) from act where created_by = 'ai')),
    'occupancy_by_weekday_last60_next14', (select jsonb_agg(jsonb_build_object('dow', w.dow,
         'day', (array['อาทิตย์','จันทร์','อังคาร','พุธ','พฤหัสบดี','ศุกร์','เสาร์'])[w.dow + 1],
         'avg_rooms_sold', w.avg_n, 'occ_pct', round(w.avg_n * 100.0 / nullif((select nroom from d), 0)),
         'nights_counted', w.c) order by w.dow)
       from (select dow, round(avg(n), 1) as avg_n, count(*) as c from occ where day <= (select today from d) + 13 group by dow) w),
    'next_30_days', (select jsonb_build_object(
         'avg_rooms_sold', round(avg(n), 1),
         'lowest', (select jsonb_agg(jsonb_build_object('date', l.day, 'day', (array['อาทิตย์','จันทร์','อังคาร','พุธ','พฤหัสบดี','ศุกร์','เสาร์'])[l.dow + 1], 'rooms_sold', l.n)) from
                    (select * from occ where day between (select today from d) and (select today from d) + 29 order by n, day limit 6) l),
         'highest', (select jsonb_agg(jsonb_build_object('date', l.day, 'day', (array['อาทิตย์','จันทร์','อังคาร','พุธ','พฤหัสบดี','ศุกร์','เสาร์'])[l.dow + 1], 'rooms_sold', l.n)) from
                    (select * from occ where day between (select today from d) and (select today from d) + 29 order by n desc, day limit 4) l))
       from occ where day between (select today from d) and (select today from d) + 29),
    'revenue', jsonb_build_object(
       'room_revenue_last_30d', (select coalesce(sum(rate), 0) from act, occ o
            where o.day between (select today from d) - 30 and (select today from d) - 1 and check_in <= o.day and check_out > o.day),
       'room_revenue_on_books_next_30d', (select coalesce(sum(rate), 0) from act, occ o
            where o.day between (select today from d) and (select today from d) + 29 and check_in <= o.day and check_out > o.day),
       'avg_rate', (select round(avg(rate)) from act)),
    'channels', (select jsonb_agg(jsonb_build_object('channel', channel, 'bookings', c, 'room_nights', rn) order by c desc)
       from (select channel, count(*) as c, sum(nights) as rn from act group by channel) x),
    'stay_length', jsonb_build_object(
       'avg_nights', (select round(avg(nights), 1) from act),
       'n1', (select count(*) from act where nights = 1),
       'n2_3', (select count(*) from act where nights between 2 and 3),
       'n4_plus', (select count(*) from act where nights >= 4)),
    'lead_days_avg', (select round(avg(check_in - (created_at at time zone 'Asia/Bangkok')::date)) from act where created_by <> 'seed'),
    'breakfast_share_pct', (select round(100.0 * count(*) filter (where coalesce((details->>'bf')::int, 0) > 0) / nullif(count(*), 0)) from act),
    'company', jsonb_build_object(
       'companies', (select count(*) from co),
       'room_nights_from_companies', (select coalesce(sum(room_nights), 0) from co),
       'room_nights_total', (select coalesce(sum(nights), 0) from act),
       'top', (select coalesce(jsonb_agg(jsonb_build_object('company', company, 'bookings', bookings, 'room_nights', room_nights,
                 'revenue', revenue, 'last_check_out', last_out, 'upcoming_rooms', upcoming_rooms) order by room_nights desc), '[]')
               from (select * from co order by room_nights desc limit 8) t)),
    'guests', jsonb_build_object(
       'distinct', (select count(*) from gst),
       'stayed_2plus', (select count(*) from gst where stays >= 2),
       'repeat_no_upcoming_30d_gone', (select count(*) from gst where stays >= 2 and not upcoming and last_out < (select today from d) - 30),
       'first_booking_channel', (select jsonb_object_agg(first_ch, c) from (select first_ch, count(*) c from gst group by 1) z)),
    'unpaid_upcoming_7d', (select count(*) from act where check_in between (select today from d) and (select today from d) + 6 and payment_status <> 'ชำระแล้ว'),
    'line_chats', jsonb_build_object(
       'threads', (select count(*) from chat_threads where not is_seed),
       'need_staff', (select count(*) from chat_threads where needs_staff))
  )
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_feed_get', 'pp_feed_lock', 'pp_feed_put', 'pp_insight_data') loop
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
