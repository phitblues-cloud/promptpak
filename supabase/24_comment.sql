-- PROMPT PAK · เก็บความเห็นที่ลูกค้าพิมพ์ต่อท้ายแบบสอบถามความพึงพอใจ (ช่องพิมพ์ในการ์ดขั้น 3)
-- ต่อจาก 23_survey.sql · วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)

alter table auto_msg_rating add column if not exists comment text;
alter table auto_msg_rating add column if not exists comment_at timestamptz;

-- บันทึกความเห็นของลูกค้า LINE คนนี้ ลงแบบสอบถามล่าสุดที่ตอบเสร็จภายใน 14 วัน (ส่งหลายข้อความต่อกันได้)
create or replace function pp_am_comment(p_line text, p_text text) returns jsonb language plpgsql as $$
declare v_key text; v_score int; v_t text := left(trim(coalesce(p_text, '')), 2000);
begin
  if v_t = '' then return jsonb_build_object('ok', false); end if;
  select key, score into v_key, v_score from auto_msg_rating
   where line_user_id = p_line and done and updated_at > now() - interval '14 days'
   order by updated_at desc limit 1;
  if v_key is null then return jsonb_build_object('ok', false); end if;
  update auto_msg_rating set comment = case when comment is null or comment = '' then v_t else comment || E'\n' || v_t end,
         comment_at = now() where key = v_key;
  return jsonb_build_object('ok', true, 'key', v_key, 'score', v_score);
end $$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname = 'pp_am_comment' loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
