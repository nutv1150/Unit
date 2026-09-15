# แนวทางพัฒนา UNIT (Unified Toolkit)

อัปเดตจากโค้ดในโปรเจกต์เมื่อ 14 กันยายน 2026

## ภาพรวมและเอกสารผู้ใช้

UNIT เป็นแอปเดสก์ท็อป Python + CustomTkinter สำหรับวิเคราะห์ข้อมูลและไฟล์ในงาน Cybersecurity / CTF ดูความสามารถ รายละเอียดทุกหมวด และวิธีเริ่มใช้งานใน [README.md](README.md)

จุดเข้าโปรแกรมคือ `app.py` โดย `UNITApp` ใช้ `TkinterDnD.DnDWrapper` รองรับ Drag & Drop และสร้างหน้าต่างจาก `pages/` ผ่าน Sidebar

## การติดตั้งและรัน

```bash
python -m pip install -r Requirements.txt
python app.py
```

รันจากโฟลเดอร์โปรเจกต์ ใช้ Python ที่มี Tkinter และระบบแสดงผล GUI ชื่อไฟล์ dependency คือ `Requirements.txt` ตัว R ใหญ่ มี `customtkinter`, `tkinterdnd2`, `puremagic` ส่วนเครื่องมือภายนอกและ Gemini CLI ต้องติดตั้งแยกและอยู่ใน `PATH`

## โครงสร้างและจุดแก้ไข

- `app.py` ลงทะเบียน 8 หน้า: Dashboard, Data Hashing, File Inspection, Pipeline, Gemini CLI, App Portal และมี `record_activity()` สำหรับบันทึกกิจกรรมผ่าน store กลาง
- `pages/my_tools.py` และ `pages/challenge.py` ลงทะเบียนใน `app.py` แล้ว ใช้ `navigate_to(page, sub)` เปิดโหมดย่อย และ `on_close()` บันทึก/พัก timer ก่อน destroy ข้อมูลอยู่ใน `config/` ผ่าน `Tools/workspace_store.py`; สีโทนเข้มและ dialog ใช้ `pages/workspace_ui.py`
- `pages/dashboard.py` แสดงสถิติ รายการโปรด คีย์ลัด หมวดหมู่ การแข่งขัน และไฟล์ล่าสุด
- `Tools/dashboard_store.py` เก็บข้อมูลที่ `data/dashboard_state.json` ในโปรเจกต์ ไม่ใช่ `~/.unit/` จำกัดประวัติไว้ 2,000 เหตุการณ์
- `pages/data_hash.py` มี Decode, Encode, Hash, Bitwise โดยใช้ `Encode/`, `Decode/`, `Hashing/`, `Tools/extra_tools.py` รายการอัลกอริทึมใน UI อาจไม่เท่ากับที่ backend รองรับ เช่น SHAKE มีใน backend แต่ไม่มีในรายการ Hash ของหน้า
- `pages/file_inspection.py` จัดการหลายไฟล์ ตรวจ header/executable/strings และเรียก `file`, `zsteg`, `exiftool` มี regex และส่งข้อความข้ามหน้า
- `pages/pipeline.py` จัดการ node canvas, ลำดับขั้นตอน, preview, options, wizard และโหลด Pipeline ที่บันทึกไว้ ส่วน `Pipeline/pipeline_engine.py` เป็นตัวเรียกเครื่องมือจริง
- `Tools/artifact_bridge.py` แปลงผลไบนารีเป็นไฟล์ชั่วคราวและช่วยเลือก input ให้ file tool คงการส่งข้อมูลแบบ bytes เพื่อไม่ทำลายข้อมูลไบนารี
- `Tools/flag_detector.py` เป็น detector กลาง ใช้ `find_flags()` / `find_first_flag()` รองรับหลาย prefix เช่น flag, CTF, picoCTF, HTB, THCTT และรูปแบบการแข่งขันบางกลุ่ม การตรวจพบเป็น pattern match ไม่ใช่ยืนยันคำตอบ
- `pages/gemini.py` เป็น wrapper และ agent loop ผ่าน Gemini CLI ไม่ใช่การเรียก REST API โดยตรง
- `pages/app_portal.py` เป็นตัวเปิดโปรแกรมภายนอก พร้อมจัดการ custom tool และเลือกแอปของระบบ

## ไฟล์ตั้งค่าเครื่องมือสองชุด

| ไฟล์ | ใช้กับ | โครงสร้างสำคัญ |
| --- | --- | --- |
| `Pipeline/custom_tools.json` | Pipeline | หมวดที่มี list ของ tool: `name`, `command`, `mode`, `params`, `options`, `description` และอาจมี `input_mode`, `input_flag` |
| `custom_tools.json` | App Portal | list ของ tool: `name`, `desc`, `icon`, `check`, `cmd` |
| `Pipeline/saved_pipelines.json` | Pipeline ที่บันทึก | `saved_pipelines` ซึ่งมี `pipeline_name` และ `steps` |

ตรวจ schema ของไฟล์จริงก่อนแก้ ห้ามใช้สองไฟล์ custom tools แทนกัน

## แนวทางแก้โค้ด

- เพิ่มหน้าใหม่ด้วย class ที่สืบทอด `ctk.CTkFrame` แล้วลงทะเบียนทั้ง `app.py` และ `sidebar.py` การเปลี่ยนหน้าจับคู่ชื่อแบบไม่สนตัวพิมพ์ใหญ่เล็ก
- ใช้ detector กลางเมื่อต้องตรวจ flag และตรวจผู้เรียกเดิมก่อนเปลี่ยน pattern
- ส่งกิจกรรมผ่าน `record_activity()` เพื่อให้ Dashboard สรุปข้อมูลได้สอดคล้องกัน
- `app.py` ตั้ง appearance เป็น Light แต่ Data Hashing, File Inspection, Gemini CLI และ App Portal กำหนดสีเข้มของตัวเอง การเปลี่ยนธีมกลางจึงไม่เปลี่ยนทุกหน้า
- รักษาคอมเมนต์ภาษาไทยตามบริบทของไฟล์เดิม และอ่าน logic ที่เกี่ยวข้องก่อนแก้
- ไม่ลบหรือเขียนทับไฟล์โจทย์ ตัวอย่างไบนารี หรือสถานะผู้ใช้ เช่น `data/dashboard_state.json` โดยไม่เกี่ยวข้องกับงาน

## การรันคำสั่งและเขียนไฟล์

`pages/gemini.py::process_request()` อ่านไฟล์ข้อความจาก path ที่พบใน prompt และส่งเนื้อหาให้ Gemini CLI เมื่อคำตอบมี `[EXEC]` จะเรียก `ask_action_confirm()` ก่อนรันคำสั่งด้วย `shell=True` สูงสุด 2 รอบต่อข้อความ ส่วน `[SAVE:path]` ขออนุญาตก่อนเขียนไฟล์ด้วยโหมด `w` ซึ่งเขียนทับไฟล์เดิมได้ ต้องคงขั้นตอน ALLOW / DENY นี้เมื่อแก้ flow และไม่อ้างว่า tag เหล่านี้รันอัตโนมัติโดยไม่มีการยืนยัน

App Portal ใช้ `subprocess.Popen(..., shell=True)` กับคำสั่งของเครื่องมือ ส่วน Pipeline ใช้ command list ผ่าน `subprocess` ให้คงรูปแบบ list ใน engine และตรวจการประกอบ params/options เมื่อปรับการเรียกคำสั่ง

## การตรวจสอบการเปลี่ยนแปลง

มีชุดทดสอบใน `tests/` สำหรับ dashboard store, flag detector, byte parser, binary decode และ artifact/pipeline compatibility เลือกรันชุดที่เกี่ยวข้องกับ logic ที่แก้ ส่วนการเปลี่ยนเอกสารให้ตรวจชื่อเมนู path และพฤติกรรมเทียบกับโค้ดจริง ไม่อ้างว่าทดสอบ GUI หรือโปรแกรมภายนอกแล้วหากยังไม่ได้รัน
