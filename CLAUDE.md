# CLAUDE.md

คำแนะนำสำหรับ Claude Code (claude.ai/code) เมื่อทำงานกับโค้ดในโปรเจกต์นี้

> อัปเดตล่าสุด: สำรวจโค้ดจริงถึง commit `a04fc2e` ("Update gemini.py") — เอกสารฉบับก่อนหน้านี้ตกยุค
> ไปหลายจุด (โดยเฉพาะหน้า Gemini CLI และหน้า Pipeline ที่ถูกพัฒนาเพิ่มเยอะมาก) จึงปรับปรุงใหม่ทั้งฉบับ

## ภาพรวมโปรเจกต์

**UNIT (Unified Toolkit)** เป็นแอปเดสก์ท็อป GUI ที่เขียนด้วย Python + CustomTkinter สำหรับงานด้าน
Cybersecurity / CTF (Capture The Flag) โดยรวมเครื่องมือ encode/decode, hashing, file inspection,
pipeline รัน CLI tools ภายนอก (แบบต่อ node เป็นสายพาน), และ AI agent ผ่าน Gemini CLI ไว้ในแอปเดียว

**ธีมหน้าตาไม่ได้เป็น dark cyberpunk ทั้งแอปแล้ว** — ปัจจุบัน `app.py` ตั้ง
`ctk.set_appearance_mode("Light")` เป็นค่าเริ่มต้นของทั้งแอป (พื้นหลัง container สีเทาอ่อน
`#f5f6f8`, sidebar สีเทาอมม่วง `#5f6475`) มีเฉพาะบางหน้าเท่านั้นที่ hardcode ธีม "Cyberpunk /
Terminal" (พื้นดำ ตัวอักษร Neon cyan/green) ทับของตัวเองอีกที ได้แก่ `gemini.py`,
`app_portal.py`, และบางส่วนของ `file_inspection.py` — ถ้าจะแก้ธีม ต้องรู้ว่าแก้ที่ระดับแอป
(`app.py`) จะไม่กระทบหน้าที่ hardcode สีเอง

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
  `re`, `json`, `os`, `threading`, `shutil`, `tempfile`, `time`, `glob`

หน้า **Pipeline**, **App Portal** และ **Gemini CLI** เรียกโปรแกรมภายนอกผ่าน `subprocess` ทั้งหมด:
- เครื่องมือวิเคราะห์ไฟล์/CTF ทั่วไป: `xxd`, `hexdump`, `7z`, `unzip`, `tar`, `strings`, `grep`,
  `openssl` ฯลฯ (นิยามไว้ใน `Pipeline/custom_tools.json`)
- เครื่องมือ security แบบเปิดโปรแกรม GUI/terminal: `wireshark`, `burpsuite`, `ghidra`, `nmap`,
  `msfconsole`, `hashcat`, `firefox` (นิยามไว้ใน `custom_tools.json` ที่ root — ดูหัวข้อ
  "custom_tools.json มีสองไฟล์" ด้านล่าง เพราะ schema ไม่เหมือนกัน)
- **`gemini` CLI** (`@google/gemini-cli`, ติดตั้งผ่าน `npm install -g @google/gemini-cli`) —
  หน้า Gemini เรียกผ่าน `shutil.which("gemini")` แล้ว `subprocess.run([...])` ไม่ใช่เรียก REST API
  ตรงๆ

ทุกโปรแกรมข้างต้นต้องติดตั้ง/มีอยู่ใน `PATH` ของระบบเองแยกต่างหาก ไม่ใช่ Python package และ repo
ยังไม่มี `requirements.txt` ณ ตอนนี้เช่นกัน

## โครงสร้างโค้ด

```
app.py                  # Entry point: สร้างหน้าต่างหลัก, sidebar, และ page container
sidebar.py              # แถบเมนูด้านซ้าย ส่ง callback switch_page ไปยัง app.py

pages/                  # แต่ละไฟล์ = 1 หน้าในแอป (ctk.CTkFrame)
  dashboard.py          # หน้าแรก แสดงข้อมูลระบบทั่วไป (ธีม Light)
  data_hash.py           # หน้า Encode / Decode / Hash — ใช้โมดูล Encode/Decode/Hashing/Tools
  file_inspection.py    # ตรวจไฟล์: magic bytes, hex dump, regex, flag pattern, drag & drop
  pipeline.py           # UI Pipeline แบบ node canvas (1198 บรรทัด) — ใช้ Pipeline/pipeline_engine.py
                        # ดูรายละเอียดสถาปัตยกรรมในหัวข้อ "Pipeline: จุดที่ควรรู้ก่อนพัฒนาต่อ"
  gemini.py             # Wrapper เรียก `gemini` CLI ผ่าน subprocess (ธีม CTF_MODE) — รองรับ
                        # auto-exec คำสั่งที่ AI ตอบกลับมาด้วย (ดูหัวข้อความปลอดภัยด้านล่าง!)
  app_portal.py         # Quick-launch ปุ่มเปิดโปรแกรม security ภายนอก (Wireshark, Ghidra ฯลฯ)
                        # โหลด custom tool เพิ่มเองได้จาก custom_tools.json ที่ root (คนละไฟล์กับ
                        # Pipeline/custom_tools.json)

Encode/base_encoder.py  # encode_data(text, algo) รองรับ Base64/32/45/58/62/85, Hex, Binary,
                        # Octal, Decimal, ROT13, Reverse, URL, HTML entity, Unicode escape ฯลฯ
Decode/base_decoder.py  # decode_data(text, algo) + auto_detect_decode() เดา encoding อัตโนมัติ
Hashing/hash_utils.py   # hash_data(text, algo, length) รองรับ md5/sha1/sha2xx/sha3xx/blake2/shake
Tools/extra_tools.py    # highlight_text, bitwise_mask/unmask (XOR/OR/AND), encode/decode ย่อย ๆ,
                        # find_flag() ตรวจ pattern "flag{", "CTF{", "picoCTF{", "TCHTT{"
                        # (สังเกตว่าสะกดต่างจาก "THCTT" ใน pipeline_engine.py — ดูข้อควรระวังด้านล่าง)

Pipeline/
  pipeline_engine.py    # PipelineEngine: โหลด/รัน custom tool จาก Pipeline/custom_tools.json
                        # ผ่าน subprocess, ตรวจหา flag ด้วย regex (FLAG_PATTERN = "THCTT{...}" หรือ
                        # "flag{...}"), บันทึก tool ใหม่ลง JSON ผ่าน save_custom_tool()
  custom_tools.json     # นิยาม external CLI tools ของ "Pipeline" เท่านั้น แบ่งเป็นหมวด (เช่น
                        # "File Analysis", "Archive Extraction") พร้อม
                        # name/command/mode(file|text)/params/options/description
                        # *** อย่าสับสนกับ custom_tools.json ที่ root ซึ่งเป็นของ App Portal
                        #     และมี schema คนละแบบ (name/desc/icon/check/cmd) ***
  saved_pipelines.json  # pipeline หลายขั้นตอนที่ผู้ใช้บันทึกไว้ผ่านหน้า Pipeline (wizard/canvas)
                        # โครงสร้าง: {"saved_pipelines": [{"pipeline_name", "steps": [{"name",
                        # "params", "user_description", "options": [{"flag","type","description"}]}]}]}
```

### ไฟล์อื่น ๆ ที่ไม่ใช่ core code
`123.txt`, `DDD`, `secret.txt`, `testXor.txt`, `decry.iso`, `dry.iso`, `tempCodeRunnerFile.py`,
`ที่อยู่ไฟล์` — ดูเหมือนเป็นไฟล์ทดสอบ/โจทย์ CTF หรือไฟล์ scratch ที่หลงเหลือจากการพัฒนา ไม่ใช่ส่วน
ของ logic หลักของแอป ควรระวังอย่าลบ/แก้โดยไม่ตรวจสอบก่อนว่ามีการอ้างอิงถึงจากที่อื่นหรือไม่

## Pipeline: จุดที่ควรรู้ก่อนพัฒนาต่อ

หน้า Pipeline (`pages/pipeline.py`) ไม่ใช่แค่ฟอร์มรัน tool เดียวอีกต่อไป แต่เป็น **UI แบบ node
canvas** ที่ให้ลากวาง tool เป็นสายพาน (multi-step) ได้ ไฟล์นี้ใหญ่มาก (~1200 บรรทัด) และมีโค้ดฝัง
(closure) เยอะ ก่อนแก้ควรอ่านโครงตามลำดับนี้:

1. **`load_tools_from_json()` / `refresh_tools_panel()`** — โหลดรายการ tool ที่เลือกได้จาก
   `Pipeline/custom_tools.json` มาแสดงเป็นปุ่มในแผงด้านข้าง
2. **`add_tool_node()`** — ผู้ใช้กดเพิ่ม tool เข้าสาย pipeline บน canvas, เก็บลง `self.nodes`
   (list ของ dict ที่มี `frame`, `name`, ตำแหน่ง ฯลฯ), แล้ว `draw_connections()` วาดเส้นเชื่อม node
3. **`run_pipeline()`** — วน `self.nodes` ตามลำดับ, ส่ง output ของ step ก่อนหน้าเป็น input ของ
   step ถัดไป (`current_data` เป็น `bytes`) โดยเปิด popup ทีละ step ผ่าน `open_step_window()`
   ให้ผู้ใช้ preview/ปรับ option ก่อนรันจริงในแต่ละ step
4. **`open_step_window()`** — popup ต่อ step เดียว มี logic ย่อยเยอะมาก (before/after option row,
   preview command, `run_tool()` ที่เรียก `PipelineEngine.run_file_tool()` /
   `run_text_tool()` จริง ๆ, `next_step()` ส่ง output กลับให้ `run_pipeline()`)
5. **`open_pipeline_wizard()`** — อีก flow นึงสำหรับ "สร้าง pipeline ใหม่" แบบทีละขั้นแล้วบันทึกลง
   `Pipeline/saved_pipelines.json` ผ่าน `finalize_wizard_pipeline()` (คนละ flow กับ canvas ที่รันสด)
6. **`load_saved_pipeline_to_canvas()`** — โหลด pipeline ที่เคยบันทึกกลับขึ้น canvas เพื่อรันซ้ำ/แก้

**ตัวจริงที่รันคำสั่งคือ `Pipeline/pipeline_engine.py` (`PipelineEngine`)** — `pages/pipeline.py`
เป็นแค่ UI/orchestration ทั้งหมด ไม่ได้เรียก `subprocess` ตรง ๆ เอง ถ้าจะเพิ่มความสามารถให้ pipeline
(เช่น branching, condition, retry, export เป็น script) ควรตัดสินใจว่าจะใส่ logic ที่ระดับ
`PipelineEngine` (เพื่อให้ non-GUI ใช้ซ้ำได้) หรือที่ `pages/pipeline.py` (เฉพาะ UI flow)

**จุดที่ยังเป็นข้อจำกัด/โอกาสพัฒนาต่อ**:
- `PipelineEngine.FLAG_PATTERN` จับได้แค่ `THCTT{...}` และ `flag{...}` — ไม่ครอบคลุม `CTF{...}`,
  `picoCTF{...}` เหมือนที่ `file_inspection.py`/`extra_tools.py` รองรับ ถ้าจะให้ pipeline ตรวจ flag
  ได้ครบเหมือนหน้าอื่น ต้องอัปเดต regex นี้ให้ตรงกัน (และเช็ค `TCHTT` vs `THCTT` ที่สะกดไม่ตรงกันด้วย)
- `run_text_tool`/`run_file_tool` มี timeout ตายตัวที่ 30 วินาที ไม่ config ได้จาก UI
- ยังไม่มีการ validate ว่า option/param จาก UI ปลอดภัยก่อนต่อเป็น command list (ดูหัวข้อความ
  ปลอดภัยด้านล่าง)
- pipeline ที่บันทึกไว้ (`saved_pipelines.json`) เก็บเป็น flat list ไม่มี versioning/id ซ้ำชื่อกันได้

## รูปแบบสำคัญในโค้ด (Conventions)

- **หน้าใหม่ในแอป**: สร้างเป็น class ที่ inherit จาก `ctk.CTkFrame`, รับ `master` ใน `__init__`,
  แล้วเพิ่มเข้า dict `self.pages` ใน `app.py` และเพิ่มชื่อใน list `items` ของ `sidebar.py`
  (ชื่อหน้าจะถูกจับคู่แบบ case-insensitive) — **ข้อควรระวัง**: ตอนนี้ `sidebar.py` มีปุ่ม
  `"My Tools"` และ `"Challenge"` อยู่ใน list `items` แล้ว แต่ `app.py` ยังไม่มี key เหล่านี้ใน
  `self.pages` เลย กดแล้วจะเห็น `[ERROR] ❌ เปลี่ยนหน้าไม่ได้!` ใน terminal เฉย ๆ — ถ้าจะทำหน้าใหม่
  สองหน้านี้ให้เสร็จ ต้องสร้างไฟล์ใน `pages/` แล้วไปเพิ่มใน `app.py` ด้วย
- **Flag detection**: หลายโมดูล (`pipeline_engine.py`, `extra_tools.py`, `file_inspection.py`)
  ใช้ regex/pattern ตรวจหา flag รูปแบบ CTF คนละชุดกัน (ดูหัวข้อ Pipeline ด้านบน) — ถ้าจะเพิ่ม
  pattern ใหม่ ให้แก้ให้ครบทั้ง 3 จุดเพื่อความสอดคล้อง
- **Custom Pipeline tools**: เพิ่ม external tool ใหม่ให้ "หน้า Pipeline" โดยแก้
  `Pipeline/custom_tools.json` (หรือเรียก `PipelineEngine.save_custom_tool()`) — ต้องระบุ `name`,
  `command`, `mode` (`"file"` หรือ `"text"`), `params`, `options`, `description` — ส่วนการเพิ่มปุ่ม
  quick-launch โปรแกรมใหม่ให้ "หน้า App Portal" ต้องแก้ `custom_tools.json` ที่ root แทน (schema
  คนละแบบ ห้ามแก้ผิดไฟล์)
- **Theme**: หน้าที่ hardcode ธีม cyberpunk (`gemini.py`, `app_portal.py`, บางส่วนของ
  `file_inspection.py`) กำหนดสีเป็นตัวแปรซ้ำในแต่ละไฟล์ (`BG_COLOR`, `PANEL_COLOR`, `ACCENT_CYAN`,
  `ACCENT_GREEN`, `TEXT_DIM`, `ALERT_RED`) ส่วนหน้าที่เหลือ (`dashboard.py`, `data_hash.py`,
  `pipeline.py`) ใช้ธีม Light ของแอปตามปกติ — ยังไม่มีไฟล์ theme กลาง ถ้าจะรีแฟกเตอร์ให้พิจารณาดึง
  ออกมาเป็นโมดูลเดียว และตัดสินใจให้ชัดว่าทั้งแอปจะใช้ธีมเดียวหรือคงความต่างไว้
- คอมเมนต์ในโค้ดส่วนใหญ่เป็นภาษาไทย — ควรคงภาษาไทยไว้เมื่อแก้ไข/เพิ่มคอมเมนต์ในไฟล์เดิม

## หน้า Gemini CLI — AI agent ที่รันคำสั่งเองได้ (สำคัญมากด้านความปลอดภัย)

`pages/gemini.py` ไม่ใช่แค่ chat wrapper ธรรมดาแล้ว ตอนนี้เป็น **agent loop** ที่:
- เรียก `gemini` CLI ผ่าน `subprocess.run([self.gemini_cmd, "-m", model, "-p", prompt], ...)`
  (ไม่ใช่เรียก Gemini API ตรง ๆ ผ่าน HTTP) และ auto-retry เมื่อเจอ 503/overload
- แนบเนื้อไฟล์ที่ผู้ใช้พิมพ์ path ไว้ในข้อความเข้าไปใน prompt อัตโนมัติ (`process_request()`
  วน `prompt.split()` แล้วเช็ค `os.path.isfile`)
- **`process_request()` สแกน output ของ AI หา tag `[EXEC]...[/EXEC]` แล้วรันด้วย
  `subprocess.run(cmd, shell=True, ...)` ทันที** (สูงสุด 2 รอบต่อข้อความ) แล้วป้อนผลลัพธ์กลับเข้า
  prompt ต่อให้ AI วิเคราะห์ต่อเอง — คือ AI สามารถสั่งรัน shell command บนเครื่องผู้ใช้ได้เองแบบ
  ไม่มีการยืนยันจากผู้ใช้ก่อนต่อคำสั่ง
- **`finish_response()` สแกน output หา tag `[SAVE:path]...[/SAVE]` แล้วเขียนทับไฟล์ที่ path นั้น
  ทันที** ก็ไม่มี confirmation เช่นกัน

**ผลคือถ้าแก้ไข/ต่อยอดหน้านี้ ต้องถือว่าเป็นจุดที่มีความเสี่ยงสูงสุดในแอป** (เทียบเท่าหรือมากกว่า
`pipeline_engine.py`/`app_portal.py`) เพราะ command ที่รันมาจาก output ของโมเดล AI ไม่ใช่จาก
input ตรงของผู้ใช้ ถ้าจะเพิ่มความสามารถ ให้พิจารณาใส่ allow-list/confirmation ก่อนรัน `[EXEC]`
จริง แทนที่จะรันทันที และอย่าเพิ่มขอบเขตการ auto-exec ให้กว้างขึ้นโดยไม่มีการควบคุมเพิ่ม

## ข้อควรระวังด้านความปลอดภัย

- `pages/gemini.py::process_request()` รัน `subprocess.run(cmd, shell=True, ...)` โดย `cmd` มาจาก
  ข้อความที่ AI ตอบกลับ (ดูหัวข้อด้านบน) — จุดนี้เสี่ยง command injection/AI ควบคุมเครื่องได้โดยตรง
  มากที่สุดในโปรเจกต์
- `pages/app_portal.py` เรียก `subprocess.Popen(cmd, shell=True, ...)` เพื่อเปิดโปรแกรมภายนอก
  (รวมถึง custom tool ที่ผู้ใช้เพิ่มเองผ่าน `custom_tools.json`) — ใช้ `shell=True` อยู่แล้วในโค้ด
  ปัจจุบัน ถ้าจะแก้ไขส่วนนี้ควรพิจารณาลด/คุม input ที่มาประกอบเป็น `cmd`
- `Pipeline/pipeline_engine.py` เรียก `subprocess.run(cmd, ...)` แบบ list (ไม่ใช้ `shell=True`)
  โดย `cmd` ประกอบจาก `command` ใน `custom_tools.json` + `params`/`options` ที่ผู้ใช้กรอกใน UI —
  ปลอดภัยกว่าสองจุดข้างบนเพราะไม่ผ่าน shell แต่ยังไม่มีการ validate ค่า params/options เมื่อแก้ไข
  ส่วนนี้ควรคงรูปแบบ list-based command และหลีกเลี่ยงการเปลี่ยนไปใช้ `shell=True`
- โปรเจกต์นี้เป็นเครื่องมือสำหรับงาน security/CTF ที่ถูกต้องตามกฎหมาย (นิติเวชดิจิทัล, ฝึกซ้อม CTF)
  ไม่ใช่เครื่องมือโจมตีระบบผู้อื่น หากมีการร้องขอให้เพิ่มความสามารถที่อาจใช้ในทางที่ผิด (เช่น
  exploit/malware) ให้ปฏิบัติตามแนวทางความปลอดภัยตามปกติ