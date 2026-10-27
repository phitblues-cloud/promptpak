#!/bin/bash
# เปิดระบบทดสอบในเครื่อง (Postgres พอร์ต 5433 + เว็บ http://localhost:3999 · PIN เจ้าของ 123456 / พนักงาน 654321 — ค่าทดสอบเท่านั้น)
# ใช้: bash dev/dev.sh   ·  จำลอง AI: EXTRA="PP_FAKE_AI=1" bash dev/dev.sh
# ถ้า Postgres ดับ (เกิดบ่อยในเครื่องคลาวด์) รันคำสั่งนี้ซ้ำได้เลย
ROOT=$(cd "$(dirname "$0")/.." && pwd); PGD=${PGDATA_DIR:-$([ -d /home/claude ] && echo /home/claude/pgdata || echo /tmp/pp-pgdata)}; BIN=$(ls -d /usr/lib/postgresql/*/bin | tail -1)
if [ ! -d "$PGD" ]; then mkdir -p "$PGD"; chown postgres "$PGD"; su postgres -c "$BIN/initdb -D $PGD -A trust" >/dev/null; FRESH=1; fi
su postgres -c "$BIN/pg_ctl -D $PGD status" >/dev/null 2>&1 || su postgres -c "$BIN/pg_ctl -D $PGD -l $PGD/log -o '-p 5433 -k /tmp' start" >/dev/null; sleep 1
if [ -n "$FRESH" ]; then
  for r in anon authenticated service_role; do psql -h /tmp -p 5433 -U postgres -qc "create role $r" 2>/dev/null; done
  for d in pp pptest; do createdb -h /tmp -p 5433 -U postgres $d; done
  psql "postgresql://postgres@/pp?host=/tmp&port=5433" -q -f "$ROOT/supabase/01_schema.sql" -f "$ROOT/supabase/02_seed.sql" >/dev/null
fi
for p in $(pgrep -f "^node dev/server.mjs"); do kill $p; done
cd "$ROOT"; export LOCAL_DEV=1 LOCAL_PG="postgresql://postgres@/pp?host=/tmp&port=5433" APP_SECRET=devsecret OWNER_PIN=123456 STAFF_PIN=654321 PORT=3999 $EXTRA
nohup node dev/server.mjs > /tmp/pp-dev.log 2>&1 & sleep 1
echo "เปิดแล้ว: http://localhost:3999 · log: /tmp/pp-dev.log"
