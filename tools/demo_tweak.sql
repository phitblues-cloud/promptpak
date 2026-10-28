-- ปรับข้อมูลตัวอย่างเฉพาะเดโม่ (ฐาน ppdemo, วันที่ 25 ต.ค. 10:00): เช็คอิน 4 · กำลังพัก 5 · เช็คเอาท์ 3 · รันซ้ำได้
-- ฐานเดโม่ใช้นาฬิกาจริงของเครื่อง → ปิดการยกเลิกอัตโนมัติ (ไม่มาตามนัด) ไม่ให้ลบแขกตัวอย่างทิ้ง
create or replace function pp_noshow() returns int language sql as $$ select 0 $$;
delete from bookings where booking_no in ('BK6910091','BK6910092','BK6910093','BK6910094');
-- คืนค่าเดิมของ 4 ห้อง กฟผ. ก่อน แล้วค่อยปรับ
update bookings set check_in='2026-10-19', check_out='2026-10-31', created_by='seed', status='ยืนยันแล้ว'
 where booking_no in ('BK6910016','BK6910017','BK6910018','BK6910019');
-- กำลังพัก 5 = A02 A03 A06 (กฟผ.) + C11 C12 · ห้อง C01-C04 กฟผ. ออกไปแล้วเมื่อวาน
update bookings set check_out='2026-10-24' where booking_no in ('BK6910016','BK6910017','BK6910018','BK6910019');
-- เช็คเอาท์วันนี้ 3 = A07 B06 (กฟผ.) + C13
update bookings set check_out='2026-10-25' where booking_no in ('BK6910020','BK6910012');
-- เช็คอินวันนี้ 4 = แขกใหม่ 4 ห้อง (การจองจริงฝั่งพนักงาน/LINE ผ่านกฎ 25 ต.ค.)
insert into bookings (booking_no, guest_name, phone, room_id, check_in, check_out, rate, deposit, payment_status, channel, created_by, note, created_at) values
 ('BK6910091','นางสาวปวีณา ศรีสุวรรณ','081-234-5678','C01','2026-10-25','2026-10-27',400,200,'ชำระแล้ว','LINE OA','staff','มากับครอบครัว 2 ท่าน','2026-10-22 19:20+07'),
 ('BK6910092','นายอภิชาติ ใจซื่อ','089-765-4321','C02','2026-10-25','2026-10-26',400,200,'ยังไม่ชำระ','โทรศัพท์','staff','ขอเช็คอินก่อนเวลา','2026-10-24 09:05+07'),
 ('BK6910093','นางมาลี รุ่งเรือง','086-111-2233','C03','2026-10-25','2026-10-28',400,200,'ชำระแล้ว','LINE OA','staff',null,'2026-10-23 14:40+07'),
 ('BK6910094','นายสมหมาย พิมพ์ดี','092-444-5566','C04','2026-10-25','2026-10-26',400,200,'ยังไม่ชำระ','LINE OA','staff','ชำระวันเข้าพัก','2026-10-24 21:10+07');
-- แชตตัวอย่าง "เด็กหกล้มในห้อง ขออุปกรณ์ทำแผล" (28 ต.ค. เจ้าของสั่ง): ครอบครัวคุณนุช ห้องครอบครัว A04 เข้าพัก 24–26 ต.ค. · AI ตอบรับแล้วส่งต่อพนักงาน (ขึ้น "รอพนักงาน")
delete from chat_threads where line_user_id = 'demo-NUCH';
delete from ops where booking_no = 'BK6910095';
delete from bookings where booking_no = 'BK6910095';
delete from guests where line_user_id = 'demo-NUCH';
insert into guests (full_name, phone, line_user_id, line_display_name) values ('นางสาวนุชนาถ แก้วมณี','087-552-1948','demo-NUCH','Nuch 🌷');
insert into bookings (booking_no, guest_id, guest_name, phone, room_id, check_in, check_out, rate, deposit, payment_status, channel, created_by, note, created_at)
 select 'BK6910095', id, 'นางสาวนุชนาถ แก้วมณี','087-552-1948','A04','2026-10-24','2026-10-26',800,200,'ชำระแล้ว','LINE OA','staff','ครอบครัว ผู้ใหญ่ 2 เด็ก 1','2026-10-20 18:30+07'
 from guests where line_user_id = 'demo-NUCH';
insert into ops (at, role, kind, booking_no, data) values ('2026-10-24 14:40+07','staff','checkin','BK6910095','{}');
insert into chat_threads (line_user_id, guest_id, display_name, needs_staff, handoff_reason, last_message_at)
 select 'demo-NUCH', id, 'Nuch 🌷', true, 'ลูกค้าขออุปกรณ์ทำแผล เด็กหกล้มในห้อง A04', '2026-10-25 09:44+07' from guests where line_user_id = 'demo-NUCH';
insert into chat_messages (thread_id, sender, body, created_at)
 select t.id, v.s, v.b, v.at::timestamptz from chat_threads t,
 (values ('ลูกค้า','สวัสดีค่ะ','2026-10-25 09:41:10+07'),
         ('ลูกค้า','ลูกสาวหกล้มในห้องค่ะ เข่าถลอกเลือดออกนิดหน่อย','2026-10-25 09:41:40+07'),
         ('ลูกค้า','ทางรีสอร์ทมีอุปกรณ์ทำแผลให้ยืมไหมคะ พวกแอลกอฮอล์ ยาใส่แผล พลาสเตอร์','2026-10-25 09:42:15+07'),
         ('ลูกค้า','อยู่ห้อง A04 ค่ะ ให้ไปรับที่ไหน หรือเอามาให้ที่ห้องได้ไหมคะ','2026-10-25 09:42:50+07'),
         ('AI','ได้เลยค่ะคุณนุช ทางรีสอร์ทมีชุดปฐมพยาบาลค่ะ แจ้งพนักงานให้นำไปส่งที่ห้อง A04 แล้ว ประมาณ 5–10 นาทีค่ะ ระหว่างรอล้างแผลด้วยน้ำสะอาดก่อนได้ค่ะ ถ้าน้องเจ็บมากหรือเลือดไม่หยุด แจ้งได้ทันทีนะคะ 🙏','2026-10-25 09:43:05+07')) v(s,b,at)
 where t.line_user_id = 'demo-NUCH';
