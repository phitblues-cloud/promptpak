"""สร้าง supabase/02_seed.sql จากชุดข้อมูลสมมติ (mock_shifted_24oct.json)
ใช้: python3 tools/make_seed.py <path/to/mock_shifted_24oct.json>
"""
import json, sys, pathlib

src = json.load(open(sys.argv[1], encoding="utf-8"))
out = pathlib.Path(__file__).resolve().parent.parent / "supabase" / "02_seed.sql"


def q(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


L = ["-- PROMPT PAK · ข้อมูลตัวอย่าง (ห้องจริง 31 ห้อง + การจอง/แชทสมมติ)",
     "-- วิธีใช้: รันหลัง 01_schema.sql · รันซ้ำได้ (ข้อมูลตัวอย่างเดิมจะถูกแทนที่ ไม่แตะข้อมูลจริง)",
     "begin;",
     "delete from bookings where created_by = 'seed';",
     "delete from chat_threads where is_seed;"]

for r in src["rooms"]:
    L.append("insert into rooms (id, zone, room_type, bed, rate, max_guests) values (%s,%s,%s,%s,%s,%s) "
             "on conflict (id) do update set zone=excluded.zone, room_type=excluded.room_type, bed=excluded.bed, "
             "rate=excluded.rate, max_guests=excluded.max_guests;"
             % (q(r["room_id"]), q(r["zone"]), q(r["room_type"]), q(r["bed"]), r["rack_rate"], r["max_guests"]))

comp = {c["company_id"]: c["name_short"] for c in src["companies"]}
guests = {g["guest_id"]: g for g in src["guests"]}
PAY = {"ชำระแล้ว": "ชำระแล้ว", "เครดิต-ยังไม่ถึงวันพัก": "เครดิตบริษัท", "รอชำระ": "เครดิตบริษัท",
       "ค้างชำระ": "ยังไม่ชำระ", "คืนเงินแล้ว": "คืนเงินแล้ว", "ไม่มีรายการเงิน": "ยังไม่ชำระ"}
for b in src["bookings"]:
    status = "ยกเลิก" if b["booking_status"] in ("ยกเลิก", "ไม่มาตามนัด") else "ยืนยันแล้ว"
    g = guests.get(b["guest_id"], {})
    L.append("insert into bookings (booking_no, group_no, guest_name, phone, company, room_id, check_in, check_out, "
             "rate, deposit, status, payment_status, channel, created_by, note, created_at) values "
             "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'seed',%s,%s) on conflict (booking_no) do nothing;"
             % (q(b["booking_id"]), q(b.get("group_id")), q(b["guest_name"]), q(g.get("phone")),
                q(comp.get(b.get("company_id"))), q(b["room_id"]), q(b["checkin_date"]), q(b["checkout_date"]),
                b["rate"], b.get("deposit") or 300, q(status), q(PAY.get(b["payment_status"], "ยังไม่ชำระ")),
                q(b["channel"]), q(b.get("note") or None), q(b["booked_at"])))

SENDER = {"ลูกค้า": "ลูกค้า", "พนักงาน": "พนักงาน", "ระบบอัตโนมัติ": "ระบบ", "AI": "AI"}
for t in src["line_chats"]:
    uid = "seed-" + t["thread_id"]
    L.append("insert into chat_threads (line_user_id, display_name, is_seed, last_message_at) values (%s,%s,true,%s);"
             % (q(uid), q(t["line_display_name"]), q(t["last_message_at"])))
    for m in t["messages"]:
        L.append("insert into chat_messages (thread_id, sender, body, created_at) select id, %s, %s, %s "
                 "from chat_threads where line_user_id = %s;"
                 % (q(SENDER.get(m["from"], "ระบบ")), q(m.get("text") or "[ไฟล์/รูปภาพ]"), q(m["at"]), q(uid)))

L.append("commit;")
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", out, len(L), "lines")
