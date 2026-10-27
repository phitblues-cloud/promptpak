-- PROMPT PAK · แบบสอบถามความพึงพอใจ 3 ขั้นทาง LINE (ภาพรวม 1-5 ดาว → รายเรื่อง 3 ระดับ → ขอบคุณ/ขอโทษ)
-- ต่อจาก 22_automsg.sql · วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)

alter table auto_msg_rating add column if not exists topics jsonb not null default '{}'::jsonb;   -- {room,facility,service,food,value: 1|3|5}
alter table auto_msg_rating add column if not exists done boolean not null default false;          -- ส่งข้อความขั้น 3 แล้ว
alter table auto_msg_rating add column if not exists updated_at timestamptz not null default now();

-- ข้อมูลแบบสอบถามของกลุ่มการจองนี้ (ตรวจว่าเป็นเจ้าของการจองจริง) + ลูกค้าเคยสั่งอาหารเช้าไหม (ไม่สั่ง = ข้ามคำถามอาหาร)
create or replace function pp_am_survey(p_key text, p_line text) returns jsonb language plpgsql stable as $$
declare v_name text; v_bf boolean;
begin
  select coalesce(nullif(g.full_name, ''), b.guest_name) into v_name
  from bookings b join guests g on g.id = b.guest_id
  where coalesce(b.group_no, b.booking_no) = p_key and g.line_user_id = p_line limit 1;
  if v_name is null then raise exception 'ไม่พบการจองของบัญชี LINE นี้'; end if;
  select coalesce(bool_or(coalesce((b.details->>'bf')::int, 0) > 0), false) into v_bf
  from bookings b where coalesce(b.group_no, b.booking_no) = p_key and b.status <> 'ยกเลิก';
  return jsonb_build_object('name', v_name, 'breakfast', v_bf,
    'overall', (select score from auto_msg_rating where key = p_key),
    'topics', coalesce((select topics from auto_msg_rating where key = p_key), '{}'::jsonb),
    'done', coalesce((select done from auto_msg_rating where key = p_key), false));
end $$;

-- บันทึกคะแนนรายเรื่อง (ระดับ 5=ประทับใจ · 3=พอใช้ · 1=ปรับปรุง) · แตะใหม่ = ใช้ค่าล่าสุด · ต้องให้ภาพรวมก่อน
create or replace function pp_am_topic(p_key text, p_line text, p_topic text, p_lvl int) returns jsonb language plpgsql as $$
declare s jsonb;
begin
  if p_topic not in ('room', 'facility', 'service', 'food', 'value') then raise exception 'หัวข้อไม่ถูกต้อง'; end if;
  if p_lvl not in (1, 3, 5) then raise exception 'ระดับไม่ถูกต้อง'; end if;
  s := pp_am_survey(p_key, p_line);
  if s->>'overall' is null then raise exception 'ยังไม่ได้ให้คะแนนภาพรวม'; end if;
  update auto_msg_rating set topics = topics || jsonb_build_object(p_topic, p_lvl), updated_at = now() where key = p_key;
  return pp_am_survey(p_key, p_line);
end $$;

-- ปิดแบบสอบถาม (ตอบครบ/กดเสร็จแล้ว/ข้าม): คืน first=true เฉพาะครั้งแรก เพื่อส่งข้อความขั้น 3 ครั้งเดียว
create or replace function pp_am_finish(p_key text, p_line text) returns jsonb language plpgsql as $$
declare s jsonb; v_first boolean;
begin
  s := pp_am_survey(p_key, p_line);
  if s->>'overall' is null then raise exception 'ยังไม่ได้ให้คะแนนภาพรวม'; end if;
  update auto_msg_rating set done = true, updated_at = now() where key = p_key and not done;
  get diagnostics v_first = row_count;
  return pp_am_survey(p_key, p_line) || jsonb_build_object('first', v_first);
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname in ('pp_am_survey', 'pp_am_topic', 'pp_am_finish') loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
