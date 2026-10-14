# คู่มือศึกษา UNIT จากโค้ดจริง

เอกสารชุดนี้อ้างอิง source checkout ที่ราก repository ณ วันที่ 14 ตุลาคม 2026 ผู้ใช้ระบุชื่อแอปเป็น `Unit-review/` แต่ checkout ที่ตรวจจริงไม่มีโฟลเดอร์นั้น แอปหลัก (`app.py`, `pages/`, `Pipeline/`, `Tools/`) อยู่ที่ราก จึงใช้ราก repository เป็นฐานเลขบรรทัดและ path ทั้งหมด ไม่มีการแก้โค้ดแอป, `data/dashboard_state.json`, `custom_tools.json`, `config/*.json` หรือหลักฐานผู้ใช้

## ขอบเขตที่ตรวจ

- หน้า sidebar 8 หน้า: Dashboard, Data Hashing, File Inspection, Pipeline, Gemini CLI, App Portal, My Tools และ Challenge
- Solve History และ System Check ซึ่งเปิดจากหน้าอื่น
- Data Hashing 4 โหมด รวม 52 algorithm entries ใน dropdown (17 Encode, 19 Decode, 12 Hash, 4 Bitwise) และ backend-only SHAKE อีก 2 รายการ
- File Inspection 6 operations และ regex presets ที่ประกาศใน runtime 7 แบบ
- Pipeline tools เริ่มต้น 36 รายการใน 10 หมวด พร้อม preset options 20 รายการ, input modes, manual arguments, 5 templates และ Auto/Step mode
- App Portal เริ่มต้น 8 launchers; custom tools อธิบาย schema โดยไม่คัดลอกข้อมูลส่วนตัวปัจจุบันลงเอกสาร
- คำสั่ง action ภายใน packaged executable 4 คำสั่ง, help อีก 1 ทางเข้า และ build/release scripts
- backend ที่ยังไม่เชื่อม UI เช่น SHAKE, helper functions และ popup เก่าที่ไม่ได้ถูกเรียก

คำว่า “ครบ” ในเอกสารนี้หมายถึงความสามารถและตัวเลือกที่พบใน revision นี้ ไม่ได้หมายความว่าครอบคลุม options ทั้งหมดของโปรแกรมภายนอก เช่น `openssl`, `grep` หรือ `tshark`

## วิธีอ่าน

1. เริ่มที่ [inventory.md](inventory.md) เพื่อดู checklist, จำนวน และสถานะเข้าถึง
2. อ่าน [data-hashing.md](data-hashing.md) สำหรับ encoding/decoding/hash/bitwise และตัวอย่างระดับ byte/bit
3. อ่าน [file-inspection.md](file-inspection.md) สำหรับ file/header/strings/regex และข้อจำกัด preview
4. อ่าน [pipeline.md](pipeline.md) คู่กับ [external-tools.md](external-tools.md); หากใช้ AES/OpenSSL ให้ต่อด้วย [openssl.md](openssl.md)
5. ความสามารถที่ไม่ใช่อัลกอริทึมอยู่ใน [workspace-and-navigation.md](workspace-and-navigation.md), [gemini-cli.md](gemini-cli.md) และ [persistence-and-history.md](persistence-and-history.md); สำหรับเตรียมเครื่องใหม่ให้ใช้ [gemini-cli-fresh-vm.md](gemini-cli-fresh-vm.md)
6. ใช้ [quick-reference.md](quick-reference.md) ทบทวนเร็ว และ [review-questions.md](review-questions.md) ฝึกตอบ

## ป้ายหลักฐาน

- **CODE** — ยืนยันจากไฟล์และเลขบรรทัดที่ระบุ
- **RUN** — รันยืนยันใน environment นี้ด้วยข้อมูลจำลอง/คำสั่งอ่านอย่างเดียว
- **GENERAL** — หลักการจากมาตรฐานหรือเอกสารทางการ ไม่ใช่พฤติกรรมเฉพาะของ UNIT
- **UNVERIFIED** — ต้องมี GUI, credential, input จริง หรือโปรแกรม/เวอร์ชันอื่นจึงยืนยันได้
- **BUG/RISK** — พฤติกรรมที่โค้ดแสดงว่าไม่ตรงชื่อ, เสี่ยงผิดความหมาย หรือ wrapper ยังไม่สมบูรณ์; งานนี้บันทึกเท่านั้น ไม่แก้

## วิธีตรวจและผลรัน

ตรวจจาก entry point `app.py:24-178`, sidebar `sidebar.py:27-69`, UI constructors/handlers ทุกไฟล์ใน `pages/`, engines ใน `Encode/`, `Decode/`, `Hashing/`, `Pipeline/`, `Tools/`, JSON definitions และ subprocess call sites ทั้ง repository (ข้าม build artifacts/caches)

ผลที่รันยืนยัน:

- `Man` → Base64 `TWFu` → bytes `b'Man'`
- SHA-256(`abc`) = `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`
- XOR bytes `41 42 43` ด้วย `0x20` ได้ `61 62 63` (`abc`)
- command builder สร้าง argument list ของ `file`, `tar_extract`, `tshark`, `dd`, `openssl enc` ตามที่บันทึกในคู่มือ
- 25 tests ผ่าน: `test_binary_decode`, `test_custom_hex`, `test_rot`, `test_pipeline_safety`, `test_regex_safety`
- OpenSSL ที่ตรวจคือ 3.5.1; `openssl enc -list` แสดง ECB/CBC/CFB/OFB/CTR สำหรับ AES-128/192/256 แต่ไม่มี GCM

ไม่ได้เปิด GUI, ไม่เชื่อม Gemini, ไม่เรียก AI แบบเสียค่าใช้จ่าย, ไม่ launch App Portal และไม่รันเครื่องมือวิเคราะห์กับไฟล์ผู้ใช้

## แหล่งหลักการทางการ

- [RFC 4648 — Base16, Base32, Base64](https://www.rfc-editor.org/info/rfc4648/)
- [RFC 9285 — Base45](https://www.rfc-editor.org/rfc/rfc9285.html)
- [Python `hashlib`](https://docs.python.org/3/library/hashlib.html)
- [NIST FIPS 180-4 — SHA-1/SHA-2](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
- [NIST FIPS 202 — SHA-3/SHAKE](https://csrc.nist.gov/pubs/fips/202/final)
- [RFC 7693 — BLAKE2](https://www.rfc-editor.org/info/rfc7693/)
- [OpenSSL 3.5 `enc`](https://docs.openssl.org/3.5/man1/openssl-enc/)
- [NIST block-cipher modes](https://csrc.nist.gov/Projects/block-cipher-techniques/bcm)

## ข้อจำกัดสำคัญ

- ชื่อ model ใน Gemini เป็นค่าจากโค้ด ไม่ใช่คำยืนยันว่า account/CLI ปัจจุบันยังให้ใช้ทั้งหมด
- เครื่องมือ Pipeline มีใน config ไม่ได้แปลว่าติดตั้งหรือ invocation สำเร็จทุกระบบ
- File Inspection regex และ flag detection ตรวจ preview เท่านั้นใน flow Strings; ไม่ใช่ผลยืนยันทั้งไฟล์หรือคำตอบ CTF
- App Portal ใช้ `shell=True`; custom command เป็น shell อิสระ จึงอธิบาย parser/scope ได้ แต่แจกแจงคำสั่งที่ผู้ใช้อาจกรอกทั้งหมดไม่ได้
- ข้อมูลผู้ใช้ปัจจุบันถูกอ่านเฉพาะเท่าที่จำเป็นต่อ schema/status และไม่คัดลอกค่ารายบุคคลลงเอกสาร
