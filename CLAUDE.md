# CLAUDE.md

คำแนะนำสำหรับ Claude Code (claude.ai/code) เมื่อทำงานกับโค้ดในโปรเจกต์นี้

## ภาพรวมโปรเจกต์

**UNIT (Unified Toolkit)** เป็นแอปเดสก์ท็อป GUI ที่เขียนด้วย Python + CustomTkinter สำหรับงานด้าน
Cybersecurity / CTF (Capture The Flag) โดยรวมเครื่องมือ encode/decode, hashing, file inspection,
pipeline รัน CLI tools ภายนอก และตัวช่วย AI (Gemini) ไว้ในแอปเดียว หน้าตาส่วนใหญ่ใช้ธีม
"Cyberpunk / Terminal" (พื้นดำ ตัวอักษร Neon cyan/green)

จุดเข้าโปรแกรมคือ `app.py` — เป็น `ctk.CTk` ที่ผสม `TkinterDnD.DnDWrapper` เพื่อรองรับ drag & drop
ไฟล์ทั้งแอป

## การรันโปรแกรม

```bash
python app.py
```

**หมายเหตุ:** repo นี้ไม่มี `requirements.txt` — ต้องติดตั้ง dependency ด้วยมือก่อนรัน (ดูหัวข้อ
Dependencies ด้านล่าง) ถ้าจะเพิ่มไลบรารีใหม่ ควรสร้างไฟล์ `requirements.txt` ให้โปรเจกต์ด้วย

## Dependencies (อนุมานจาก import ในโค้ด)

- `customtkinter` — GUI framework หลักของทุกหน้า
- `tkinterdnd2` — รองรับ Drag & Drop ไฟล์ (ใช้ใน `app.py`, `pages/file_inspection.py`)
- `puremagic` — ตรวจ file signature / magic bytes (ใช้ใน `pages/file_inspection.py`)
- Standard library: `hashlib`, `base64`, `urllib.parse`, `html`, `codecs`, `subprocess`, `mmap`,
  `re`, `json`, `os`, `threading`, `shutil`, `tempfile`

หน้า **Pipeline** และ **App Portal** เรียกโปรแกรมภายนอกผ่าน `subprocess` (เช่น `xxd`, `hexdump`,
`7z`, `unzip`, `tar`, `wireshark`, `burpsuite`, `ghidra`, `nmap`, `msfconsole`, `hashcat`) ซึ่งต้อง
ติดตั้ง/มีอยู่ใน `PATH` ของระบบเองแยกต่างหาก ไม่ใช่ Python package

## โครงสร้างโค้ด

```
app.py                  # Entry point: สร้างหน้าต่างหลัก, sidebar, และ page container
sidebar.py              # แถบเมนูด้านซ้าย ส่ง callback switch_page ไปยัง app.py

pages/                  # แต่ละไฟล์ = 1 หน้าในแอป (ctk.CTkFrame)
  dashboard.py          # หน้าแรก แสดงข้อมูลระบบทั่วไป
  data_hash.py           # หน้า Encode / Decode / Hash — ใช้โมดูล Encode/Decode/Hashing/Tools
  file_inspection.py    # ตรวจไฟล์: magic bytes, hex dump, regex, flag pattern, drag & drop
  pipeline.py           # UI สำหรับ Pipeline — ใช้ Pipeline/pipeline_engine.py
  gemini.py             # Wrapper เรียก Gemini CLI ผ่าน subprocess (ธีม CTF_MODE)
  app_portal.py         # Quick-launch ปุ่มเปิดโปรแกรม security ภายนอก (Wireshark, Ghidra ฯลฯ)

Encode/base_encoder.py  # encode_data(text, algo) รองรับ Base64/32/45/58/62/85, Hex, Binary,
                        # Octal, Decimal, ROT13, Reverse, URL, HTML entity, Unicode escape ฯลฯ
Decode/base_decoder.py  # decode_data(text, algo) + auto_detect_decode() เดา encoding อัตโนมัติ
Hashing/hash_utils.py   # hash_data(text, algo, length) รองรับ md5/sha1/sha2xx/sha3xx/blake2/shake
Tools/extra_tools.py    # highlight_text, bitwise_mask/unmask (XOR/OR/AND), encode/decode ย่อย ๆ

Pipeline/
  pipeline_engine.py    # PipelineEngine: โหลด/รัน custom tool จาก custom_tools.json ผ่าน
                        # subprocess, ตรวจหา flag ด้วย regex, บันทึก tool ใหม่ลง JSON
  custom_tools.json     # นิยาม external CLI tools แบ่งเป็นหมวด (เช่น "File Analysis",
                        # "Archive Extraction") พร้อม command/options/description
  saved_pipelines.json  # pipeline ที่ผู้ใช้บันทึกไว้
```

### ไฟล์อื่น ๆ ที่ไม่ใช่ core code
`123.txt`, `DDD`, `secret.txt`, `testXor.txt`, `decry.iso`, `dry.iso`, `tempCodeRunnerFile.py`,
`ที่อยู่ไฟล์` — ดูเหมือนเป็นไฟล์ทดสอบ/โจทย์ CTF หรือไฟล์ scratch ที่หลงเหลือจากการพัฒนา ไม่ใช่ส่วน
ของ logic หลักของแอป ควรระวังอย่าลบ/แก้โดยไม่ตรวจสอบก่อนว่ามีการอ้างอิงถึงจากที่อื่นหรือไม่

## รูปแบบสำคัญในโค้ด (Conventions)

- **หน้าใหม่ในแอป**: สร้างเป็น class ที่ inherit จาก `ctk.CTkFrame`, รับ `master` ใน `__init__`,
  แล้วเพิ่มเข้า dict `self.pages` ใน `app.py` และเพิ่มชื่อใน list `items` ของ `sidebar.py`
  (ชื่อหน้าจะถูกจับคู่แบบ case-insensitive)
- **Flag detection**: หลายโมดูล (`pipeline_engine.py`, `extra_tools.py`) ใช้ regex/pattern ตรวจหา
  flag รูปแบบ CTF เช่น `flag{...}`, `THCTT{...}`, `CTF{...}`, `picoCTF{...}` — ถ้าจะเพิ่ม pattern
  ใหม่ให้แก้ในทั้งสองจุดให้สอดคล้องกัน
- **Custom Pipeline tools**: เพิ่ม external tool ใหม่โดยแก้ `Pipeline/custom_tools.json`
  (หรือเรียก `PipelineEngine.save_custom_tool()`) — ต้องระบุ `name`, `command`, `mode`
  (`"file"` หรือ `"text"`), `params`, `options`, `description`
- **Theme**: หน้าที่ทำธีม cyberpunk (`gemini.py`, `file_inspection.py`, `app_portal.py`) กำหนดสี
  เป็นตัวแปรซ้ำในแต่ละไฟล์ (`BG_COLOR`, `PANEL_COLOR`, `ACCENT_CYAN`, `ACCENT_GREEN`, `TEXT_DIM`,
  `ALERT_RED`) — ยังไม่มีไฟล์ theme กลาง ถ้าจะรีแฟกเตอร์ให้พิจารณาดึงออกมาเป็นโมดูลเดียว
- คอมเมนต์ในโค้ดส่วนใหญ่เป็นภาษาไทย — ควรคงภาษาไทยไว้เมื่อแก้ไข/เพิ่มคอมเมนต์ในไฟล์เดิม

## ข้อควรระวังด้านความปลอดภัย

- `Pipeline/pipeline_engine.py` และ `pages/app_portal.py` เรียก `subprocess.run(...)` ด้วยคำสั่งที่
  อาจมาจาก input ของผู้ใช้หรือค่าใน `custom_tools.json` — เมื่อแก้ไขส่วนนี้ ให้ระวังเรื่อง command
  injection และหลีกเลี่ยงการใช้ `shell=True`
- โปรเจกต์นี้เป็นเครื่องมือสำหรับงาน security/CTF ที่ถูกต้องตามกฎหมาย (นิติเวชดิจิทัล, ฝึกซ้อม CTF)
  ไม่ใช่เครื่องมือโจมตีระบบผู้อื่น หากมีการร้องขอให้เพิ่มความสามารถที่อาจใช้ในทางที่ผิด (เช่น
  exploit/malware) ให้ปฏิบัติตามแนวทางความปลอดภัยตามปกติ
