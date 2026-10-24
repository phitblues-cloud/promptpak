# คู่มือติดตั้ง PROMPT PAK (ระบบจริง เฟส 1) — ทำบน iPad ได้ทั้งหมด

> กติกา: รหัสผ่านและคีย์ทุกตัว **ห้ามส่งในแชท ห้ามใส่ในไฟล์บน GitHub** ใส่ใน Vercel เท่านั้น

## ขั้น 1 · Supabase (ฐานข้อมูล + ล็อกอิน)
1. supabase.com → Continue with GitHub → New project → Name `promptpak`, Region **Southeast Asia (Singapore)**, Plan Free → จดรหัสฐานข้อมูลเก็บเอง
2. เมนูซ้าย **SQL Editor** → New query → เปิดไฟล์ `supabase/01_schema.sql` บน GitHub → กด Raw → เลือกทั้งหมด คัดลอก → วาง → **Run** (ต้องขึ้น Success)
3. ทำซ้ำกับไฟล์ `supabase/02_seed.sql` (ห้องจริง 31 ห้อง + การจอง/แชทตัวอย่าง)
4. **Authentication → Users → Add user → Create new user** ใส่อีเมล + รหัสผ่านของเจ้าของ ติ๊ก Auto Confirm
5. **Authentication → Sign In / Providers** → ปิด **Allow new users to sign up** (กันคนนอกสมัครเข้าระบบเอง)
6. **Project Settings → API Keys** เตรียมค่า 3 ตัว (ยังไม่ต้องคัดลอกไปไหน): Project URL, publishable/anon key, secret/service_role key

## ขั้น 2 · LINE Messaging API
1. LINE Official Account Manager → **ตั้งค่า → Messaging API → เปิดใช้งาน** → สร้าง/เลือก Provider
2. developers.line.biz → Console → เลือก Channel ของ OA
   - แท็บ Basic settings → **Channel secret**
   - แท็บ Messaging API → **Channel access token (long-lived) → Issue**
3. OA Manager → **ตั้งค่าการตอบกลับ**: ข้อความตอบกลับอัตโนมัติ = **ปิด**, ข้อความทักทาย = **ปิด** (AI ทักทายเอง), Webhook = **เปิด**, แชท = เปิดได้ (ให้พนักงานตอบเองเมื่อ AI ส่งต่อ)

## ขั้น 3 · Claude API (AI)
1. console.anthropic.com → สมัคร → **Billing** เติมเครดิต (ขั้นต่ำ ~5 ดอลลาร์) → **Limits** ตั้งเพดานใช้จ่ายต่อเดือน
2. **API Keys → Create Key** ตั้งชื่อ `promptpak`

## ขั้น 4 · Vercel (เปิดเว็บจริง)
1. vercel.com → Continue with GitHub → **Add New → Project** → Import `promptpak`
2. ก่อนกด Deploy เปิด **Environment Variables** ใส่ 6 ค่า:
   | Name | ค่า |
   |---|---|
   | SUPABASE_URL | Project URL จาก Supabase |
   | SUPABASE_ANON_KEY | publishable / anon key |
   | SUPABASE_SERVICE_ROLE_KEY | secret / service_role key |
   | LINE_CHANNEL_SECRET | Channel secret |
   | LINE_CHANNEL_ACCESS_TOKEN | Channel access token |
   | ANTHROPIC_API_KEY | คีย์ Claude |
3. Deploy → ได้ลิงก์ เช่น `https://promptpak-xxx.vercel.app`
4. เปิด `ลิงก์/api/health` → ทุกค่าต้องเป็น `true` และ database = `ok`

## ขั้น 5 · ต่อ LINE เข้ากับเว็บ
1. developers.line.biz → แท็บ Messaging API → **Webhook URL** = `ลิงก์/api/line-webhook` → Update → **Verify** (ต้องขึ้น Success) → เปิด **Use webhook**
2. ทดสอบ: ใช้ LINE ส่วนตัวทักแชท OA "ขอห้องตึก 2 ห้อง วันที่ ... ถึง ..." → เปิดเว็บหน้าแรกดูการจองเด้งขึ้น

## เกณฑ์ผ่าน (ล็อกไว้ก่อน)
- ทัก LINE → การจองขึ้นหน้าแรก ≤ 30 วินาที
- บทสนทนาทดสอบ 10 แบบ ราคา/ห้องว่างถูก 10/10
- จองซ้ำห้องคืนเดียวกัน = 0 ครั้ง (ฐานข้อมูลกันไว้)
- ตัวเลขใน AI สรุปตรงฐานข้อมูล 100%
