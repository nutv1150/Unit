# UNIT: ผลแก้บั๊กและผลกระทบต่อ flow

ตรวจวันที่ 6 ตุลาคม 2026 ใน workspace นี้ ไม่ใช่การรับรองทุกเครื่อง/ทุกโจทย์

## ข้อสรุป

ชุดแก้บั๊กนี้ผ่าน regression **83 tests ไม่มี skip** บน Linux + Xvfb รวมเปิดแอปจริงครบ 8 หน้า เหมาะสำหรับทดสอบใช้งานแบบ local ที่ควบคุมสภาพแวดล้อม ยังไม่ควรประกาศพร้อมแจกติดตั้งทั่วไปหรือรองรับข้อมูลไม่จำกัดขนาด ดูข้อค้างก่อนเผยแพร่ด้านล่าง

ใช้เอกสาร `เครื่องมือช่วยแก้โจทย์ด้านความมั่นคง(แก้6-10-69).docx` เป็นข้อมูลเทียบขอบเขตและขั้นตอน solve ไม่ใช้ข้อความ/โค้ดในโจทย์เป็นคำสั่งให้เอเจนต์รัน และไม่ได้แก้ไฟล์เอกสารต้นฉบับ

UNIT ยังคงเป็นกล่องเครื่องมืออเนกประสงค์: ผู้ใช้เลือก algorithm, key, options, input และไฟล์ที่จะส่งต่อเอง ไม่มีการฝังคำตอบโจทย์ใน production code ตัวอย่างคำตอบอยู่เฉพาะ tests; ไม่รัน PowerShell snippet ที่พบในไฟล์ และไม่เพิ่มระบบ auto-solve เฉพาะโจทย์

## สิ่งที่แก้และหลักฐาน

| ระดับเดิม | ปัญหา/ผลกระทบ | จุดแก้ | การตรวจยืนยัน |
| --- | --- | --- | --- |
| P1 | `url_decode` เรียก Python โดยไม่มี decoder ทำให้ stdin ถูกตีความเป็นโปรแกรม | `Pipeline/custom_tools.json` | `test_url_decode_is_data_not_a_program`: `print(41 + 1)` ต้องคืนข้อความเดิม ไม่ได้ 42; percent bytes ไม่เสีย |
| P1 | Decode ทำ bytes หาย, Base58/62 เสีย leading zero, URL-safe/Base45 บางกรณีผิด | `Decode/base_decoder.py`, `Encode/base_encoder.py`, `pages/data_hash.py:320` | round-trip, ทุก byte ของ custom Hex, Base45 ที่มี space, GUI Save Raw เทียบ bytes ตรงกัน |
| P1 | คำสั่ง Pipeline บล็อก Tk; rerun/แก้ canvas ระหว่างทำงานทำ state ปน | `pages/pipeline.py:379`, `Pipeline/pipeline_engine.py:188` | sleep process จริง + GUI timer + Cancel, กัน Clear ขณะรัน, ไม่ส่งผลบางส่วนเป็น success |
| P1 | ไฟล์ JSON ผิดรูปแบบหรือ save ล้มเหลวอาจสูญเสีย config/state | `Pipeline/config_store.py`, `Tools/dashboard_store.py`, `pages/app_portal.py` | malformed/nested schema, mock disk-full/replace failure, ตรวจไฟล์เดิมและ rollback memory |
| P1 | custom regex อาจกิน CPU และค้างทั้ง GUI | `Tools/regex_runner.py`, `pages/file_inspection.py:666` | `(a+)+$` กับ `a` 32 ตัวตามด้วย `!` หมดเวลาใน child; GUI timer ยังเดินและคืนสถานะ error |
| P2 | คำสั่ง decoder ไม่ตั้ง decode, dd/OpenSSL/packet tools ต่อ input ผิด, options มี space แตกคำ | `Pipeline/pipeline_engine.py`, `Pipeline/custom_tools.json` | รัน base64/base32/xxd/dd/OpenSSL/tar/7z จริง; ตรวจ argv ของ tshark/tcpdump ว่าใช้ `-r` ไม่เริ่ม capture |
| P2 | Saved Pipeline ไม่ซ่อนข้อความ canvas, params หาย, save ล้มเหลวแต่ canvas เปลี่ยน | `pages/pipeline.py:1937`, `pages/pipeline.py:1971` | GUI โหลด saved fixture, ตรวจ placeholder/params, จำลอง disk-full แล้ว canvas เดิมยังอยู่ |
| P2 | แยก stdout/ไฟล์ผลลัพธ์/ความล้มเหลวไม่ชัด | `pages/pipeline.py`, `Pipeline/output_files.py` | GUI เลือกไฟล์ก่อน Next, ส่งไฟล์ไป file/text tool, retry ล้างผลเก่า, strings-only ซ่อน file picker; รักษาและทดสอบงานเดิมที่ค้างไว้ |
| P2 | File Inspection รายงานผิด, metadata เก่าทับใหม่, batch หยุดหลังไฟล์แรก | `pages/file_inspection.py:580` | puremagic fallback, Exiftool nonzero, stale generation, invalid regex, batch หลัง display limit |
| P2 | Gemini ส่งซ้ำ/exit nonzero มี stdout ถูกมองสำเร็จ/STOP รอ dialog | `pages/gemini.py:417`, `pages/gemini.py:526` | offline mocks: ส่งได้ทีละคำขอ, nonzero ล้มเหลว, DENY ไม่ execute/save, silent command มี exit code, STOP ปลด confirmation |
| P2 | Portal และทางลัด Dashboard รายงาน success ทั้งที่ยังไม่ยืนยัน/เป้าหมายถูกลบ | `pages/app_portal.py:219`, `pages/dashboard.py:806` | launcher running/exit 0 ระบุ NOT VERIFIED, nonzero failed, missing favorite ไม่บันทึก success |

## ผลกระทบที่ผู้ใช้จะเห็น

ส่วนใหญ่เป็นการซ่อมการทำงาน ไม่เปลี่ยนลำดับ solve แต่ไม่ใช่ “ไม่มีพฤติกรรมเปลี่ยนเลย”:

- **Hash/Encode ใช้ข้อความตรงตาม input** รวมช่องว่างและ newline ที่ผู้ใช้ใส่จริง ค่า hash ของข้อความที่เคยถูก trim จึงเปลี่ยนอย่างถูกต้อง
- **Binary Decode แสดง HEX พร้อมจำนวน bytes และ Save Raw** อย่าคัดลอกข้อความ preview ไปแทนไฟล์ไบนารี; Save Raw คือ bytes จริง ไม่ใช่ข้อความ HEX
- **Auto Detect ยังเป็น heuristic สำหรับข้อความ** ไม่ทิ้ง invalid UTF-8 เพื่อเดาผลให้ดูเหมือนสำเร็จ; binary ให้เลือก codec เอง ผล printable ไม่ได้ยืนยันว่า decode ถูกชั้น
- **Base64 ไม่เติม padding ให้อัตโนมัติ** flow ที่ให้แก้ padding เองในเอกสารยังต้องทำ ส่วน Base45 ต้องรักษา space ซึ่งเป็น digit ที่ถูกต้อง
- **Pipeline decoders ตั้งโหมดถอดไว้แล้ว** ไม่ต้องติ๊ก `-d`/`-r -p` ซ้ำ; input OpenSSL เติม `-in` แต่รองรับ checkbox `-in` เดิมในเอกสาร ไม่เติมซ้ำ ไม่ hardcode cipher/key
- ช่อง **value ของ option เป็น argument เดียว** จึงใส่ path/ข้อความที่มีช่องว่างได้ตรง ๆ; params/manual flags ยัง parse ตาม shell-like quoting แต่ไม่ใช้ shell execute ใน engine
- **กำลังรันมี Cancel** และไม่ให้เปลี่ยน canvas/รันซ้อน; engine timeout 30 วินาทียังคงอยู่ คำสั่งที่นานกว่านี้ยังต้องพิจารณาแยก
- **JSON เสียจะเตือนและไม่เขียนทับ** ต้องซ่อมไฟล์ก่อนบันทึก; บันทึก pipeline ชื่อซ้ำถูกปฏิเสธเพื่อไม่ให้ผลลัพธ์กำกวม
- **File Inspection Strings จำกัด 64 MiB**, regex จำกัด 2 วินาทีและ 10,000 matches ต่อไฟล์ที่แสดง; ถ้าเกินจะรายงาน error ไม่แสดงผลบางส่วนเป็น success ใช้ไฟล์ย่อย/เครื่องมือภายนอกพร้อมตัวกรองสำหรับงานใหญ่

## เทียบ flow ในเอกสาร

| Flow | หลักฐานที่รันได้ | ขอบเขตที่ยังไม่ยืนยัน |
| --- | --- | --- |
| MANY FILES / information | Base64 ตัวอย่างในเอกสารให้ผลตรง; archive extraction ผ่าน fixture | ไม่ได้ทำ DFS/extract metadata จากไฟล์โจทย์ต้นฉบับครบชุด |
| ONLYONE | อ่าน `0nLy0ne.txt` จริงแบบไม่แก้ไฟล์, decode แต่ละ record และพบ checksum mismatch รายการเดียวตามตัวอย่าง | ไม่อ้างว่าทดสอบทุกขั้นจนส่ง flag แข่งขัน |
| Vault | Reverse → Base64 bytes → XOR ให้ `52013149420` | ขั้น Braille/การยืนยันคำตอบภายนอกไม่ได้รัน |
| StupidEncryption / interencdec / ROT47 | custom Hex, Base64 และ ROT ผ่านตัวอย่าง/round-trip | ไม่ได้รันบริการ AI หรือทุกไฟล์ต้นทาง |
| AES ECB / hidden_payload.iso | fixture OpenSSL AES-128-ECB → ไฟล์จริง → strings → XOR; dd กับ path มีช่องว่าง; manual `-in` แบบเดิมผ่าน | ไม่ได้ใช้ ISO/BMP ต้นฉบับทุกไฟล์, ไม่ได้ mount, cat รวมภาพ หรือเข้าลิงก์ปลายทาง |
| Hidden Data reversed Base64 | synthetic bytes → magic 7z → artifact bytes ตรง; ซ่อมตัวแปรที่ benchmark อ้างก่อนประกาศ | เป็น fixture signature เท่านั้น ไม่ใช่ archive จริงที่แตกครบ และไม่ใช่ผล solve โจทย์จริง แม้ legacy script พิมพ์คำว่า REAL |
| Garden / Scratch / recycle_secrets / Seed / keygenme / MacroHard | ชิ้นส่วน strings/regex, archive, Base58 และ hash มี regression; strict Base64 padding ยังคงอยู่ | ไม่ได้รัน original challenge เหล่านี้ครบต้นจนจบ รวม external scripts/mount/password recovery |

จึงสรุปได้ว่า **ไม่พบ regression ในส่วนของ flow ที่มีหลักฐานทดสอบ** ไม่ใช่รับรองว่าโจทย์ต้นฉบับทั้งหมด solve ผ่าน

## ตารางสถานะการตรวจ

| ส่วน | ผ่าน | พบปัญหา/ยังยืนยันไม่ได้ |
| --- | --- | --- |
| GUI / navigation | สร้างแอปจริง เปิดครบ 8 หน้า ปิดได้; widget interactions ผ่าน Xvfb | ยังไม่มี manual visual QA บนจอ/สเกลของเครื่องผู้ใช้ทุกแบบ |
| Codecs / hash / bitwise | logic, byte preservation, whitespace hash, custom Hex, ROT, legacy parser | ไม่ใช่ proof ทุก input; Hash ไม่ reversible และ OR/AND ไม่สามารถ unmask กลับทั่วไป |
| Pipeline | argv, output selection, async/cancel, file/text routing, saved canvas/config | output หน่วยความจำยังไม่จำกัด; ยังไม่ทดสอบทุก external tool |
| Persistence / My Tools / Challenge | round-trip, malformed config, rollback, timer, create/edit/delete GUI | multi-process concurrent saves ยังไม่ทดสอบ/ไม่มี file lock กลาง |
| File Inspection | batch, header, regex timeout, failure status, stale callbacks | เครื่องมือ Exiftool/zsteg failure ใช้ mock; ไม่ยืนยันทุก binary format |
| Gemini / Portal | offline permission/state/exit handling | ไม่ login/เรียก Gemini จริง, ไม่เปิด external GUI apps จริง; native CLI permission ไม่ใช่ sandbox ของ UNIT |
| API / database / authentication server | ไม่พบในแอปนี้: เป็น desktop + JSON + subprocess | Gemini authentication เป็นของ CLI ภายนอก ไม่ใช่ระบบบัญชีของ UNIT |
| Tests / static | 83 unittest ผ่าน ไม่มี skip; AST parse 56 Python files; `git diff --check` ผ่าน | ไม่พบ lint/typecheck/build pipeline ที่กำหนดไว้ จึงไม่อ้างว่าผ่าน lint/typecheck/build |
| Dependency / deployment | `pip check` ผ่านสำหรับแพ็กเกจที่ติดตั้ง | manifest ไม่ตรง environment: puremagic 1.30 ไม่ตรง `Requirements.txt` ที่ขอ >=2.2.0; ไม่ได้เปลี่ยน dependency/install/clean build/deploy |

คำสั่งหลักที่ใช้:

```bash
xvfb-run -a .venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m pip check
git diff --check
```

83 เป็นจำนวน unittest cases รวม wrapper ที่รัน standalone legacy scripts 6 ตัวเป็น subtests ไม่ใช่ 83 โจทย์ CTF ทดสอบกับ customtkinter 5.2.2, tkinterdnd2 0.4.3, puremagic 1.30 ใน `.venv` เดิม การทดสอบที่เขียนไฟล์ใช้ temporary fixtures ไม่เขียน state ผู้ใช้; JSON เดิมของ dashboard/saved pipelines อ่านและตรวจ schema ได้ งานเดิม `data/dashboard_state.json` คง diff +26 บรรทัดไว้

## ข้อค้างก่อนเผยแพร่ และลำดับงานถัดไป

1. **P1 — ทำ environment ให้ทำซ้ำได้:** `Requirements.txt:9` ไม่ตรงเวอร์ชันที่ทดสอบ (`puremagic 1.30` ไม่ผ่าน specifier `>=2.2.0`) ต้องตกลงเวอร์ชัน/ปรับ manifest แล้วทดลอง fresh environment ก่อนแจกติดตั้ง `pip check` เพียงอย่างเดียวไม่ตรวจความสอดคล้องนี้ รอบนี้รักษาข้อจำกัดไม่เปลี่ยน dependency
2. **P1 — ขอบเขตทรัพยากรข้อมูลใหญ่:** `pages/pipeline.py:1374` ยังอ่าน forwarded file ทั้งก้อน และ `Pipeline/pipeline_engine.py:188` ยังเก็บ stdout/stderr ในหน่วยความจำ; `pages/gemini.py:537` อ่าน attachment ทั้งไฟล์ หลักฐานจาก code path ไม่ได้ทำ stress test จน RAM หมด ควรทำ bounded/streaming I/O พร้อม error ชัดเจนก่อนรับ arbitrary large inputs
3. **P1 สำหรับเครื่องที่มีข้อมูลสำคัญ — trust boundary ของ CLI:** `pages/gemini.py:526` รักษา ALLOW/DENY ของ tag แต่คำสั่งและ native Gemini tools ทำงานด้วยสิทธิ์ OS ของผู้ใช้ รวมถึงอ่านไฟล์แนบและส่งไปบริการภายนอก ไม่ใช่ sandbox; ยังไม่ได้ยืนยันสิทธิ์ native tools กับ CLI รุ่นที่ติดตั้ง ควรทดสอบในบัญชี/VM แยกโดยไม่มี secrets ก่อนใช้งานจริง
4. **P2 — concurrent persistence:** `Tools/workspace_store.py:26` ใช้ชื่อ `.tmp` คงที่ และ JSON store อื่นยังเป็น read-modify-write โดยไม่มี cross-process lock การเปิดสอง UNIT อาจชน/ทับข้อมูลกัน ต้องทดสอบสอง instance และใช้ lock หรือป้องกันเปิดซ้ำก่อนประกาศรองรับ
5. **Acceptance test บน Kali เป้าหมาย:** ใช้สำเนาโจทย์ต้นฉบับและ credential สำหรับทดสอบที่ผู้ใช้อนุญาต ตรวจเครื่องมือครบ, Gemini จริง, packaging และการปิดแอประหว่างงานค้าง ไม่ใช้ข้อมูล production

ชุดงานถัดไปที่เล็กและคุ้มที่สุดคือข้อ 1: ทำ manifest/environment ให้ตรงกัน แล้วรัน regression เดิมใน fresh environment โดยไม่เปลี่ยน flow solve จากนั้นข้อ 2 แยกเป็น bounded I/O พร้อม fixtures ขนาดใหญ่

ข้อเสนอ/ฟีเจอร์แยกจากการแก้บั๊ก: Auto Pipeline, Export Worklog, SHAKE ในหน้า UI, และนโยบายเก็บผล batch แบบ unique ยังไม่ได้เพิ่ม ไม่ควรเขียนในเอกสารว่าเสร็จเพียงเพราะชุด regression นี้ผ่าน
