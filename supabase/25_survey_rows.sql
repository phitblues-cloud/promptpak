-- PROMPT PAK · ส่งผลแบบสอบถามความพึงพอใจทาง LINE ให้หน้า CRM (CSAT / เสียงลูกค้า) นับรวมเป็นรีวิวจริง
-- ต่อจาก 24_comment.sql · วิธีใช้: Supabase > SQL Editor > New query > วางทั้งไฟล์ > Run (รันซ้ำได้)

create or replace function pp_survey_rows() returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(jsonb_build_object(
      'key', r.key, 'score', r.score, 'topics', r.topics, 'comment', r.comment, 'at', coalesce(r.comment_at, r.updated_at, r.created_at),
      'line_user_id', r.line_user_id) order by r.created_at), '[]'::jsonb)
  from auto_msg_rating r where r.key <> 'TEST';
$$;

do $$ declare f record; begin
  for f in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname = 'public' and p.proname = 'pp_survey_rows' loop
    execute format('revoke all on function %s from public', f.sig);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon, authenticated', f.sig);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.sig);
    end if;
  end loop;
end $$;
