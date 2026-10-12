# UNIT Linux desktop package

## เปิดใช้งาน

1. แตก `UNIT-<version>-linux-x86_64.tar.gz` แล้วเก็บ **ทั้งโฟลเดอร์** ในตำแหน่งถาวร ห้ามย้ายเฉพาะไฟล์ `UNIT` ออกมา
2. เปิด executable `UNIT` จาก file manager หรือรัน `./UNIT` ภายในโฟลเดอร์ ไม่ต้องใช้ Python/venv ของโปรเจกต์
3. หากต้องการไอคอนในเมนูแอป ให้รัน `./install-user.sh` หนึ่งครั้ง (ไม่ใช้ sudo) จากนั้นค้นหา **UNIT** ในเมนูแอป สคริปต์สร้างเฉพาะ shortcut ของผู้ใช้ ไม่ติดตั้งเครื่องมือและไม่คัดลอกประวัติ
4. หากย้ายโฟลเดอร์ภายหลัง shortcut เดิมจะใช้ไม่ได้ ให้ตรวจและลบเฉพาะ `~/.local/share/applications/unit-toolkit.desktop` เดิมด้วยตนเอง ก่อนสร้างใหม่ ตัวช่วยจะไม่เขียนทับ shortcut ที่แตกต่างจากเดิม

ข้อมูลใหม่เก็บที่ `$XDG_DATA_HOME/unit` หรือ `~/.local/share/unit` (ค่าเริ่มต้น) แยกจากตัวแอป: `data/` สำหรับ History/Dashboard, `config/` สำหรับ My Tools/Challenge, `Pipeline/` สำหรับ tool definitions/Saved Pipelines และ `workspace/` สำหรับ working directory ของคำสั่งที่ไม่ได้กำหนดปลายทาง ตั้ง `UNIT_DATA_HOME` เป็น absolute path เพื่อใช้ profile แยกได้

แอปที่แพ็กเริ่มด้วยประวัติและ Saved Pipelines ว่าง ไม่รวมโจทย์ ผล solve, API key หรือ custom App Portal ของผู้พัฒนา ข้อมูลเดิมใน source checkout **ไม่ถูกย้าย/ลบ/เขียนทับ** การรัน `python app.py` จากซอร์สยังใช้ที่เก็บเดิม ยกเว้นตั้ง `UNIT_DATA_HOME` ไว้ หากต้องย้ายข้อมูลเดิม ควรปิดทั้งสองแอป สำรองข้อมูล และเลือกย้ายแยกต่างหาก อย่าคัดลอก SQLite ขณะกำลังใช้งาน

## เครื่องมือภายนอกและ offline

Dashboard → **System Check** หรือ `./UNIT --check-tools` แสดงรายการ executable ที่พบ/ขาด โดยไม่เรียกใช้หรือติดตั้ง ไม่ได้ยืนยันเวอร์ชัน ความสามารถ หรือการ login

เครื่องมือเช่น `strings`, `xxd`, `openssl`, `7z`, `exiftool`, `zsteg`, `python3` (URL decode Pipeline), Gemini CLI/Node.js และ App Portal ต้องติดตั้งแยกตามงานที่ใช้ Missing ไม่ได้หมายถึงทุกหมวดใช้ไม่ได้ Data Hashing และการตรวจไฟล์ภายในทำ offline ได้ ส่วน Gemini ต้องมี CLI/credential/network ของผู้ใช้เอง ไม่มีการทดสอบ AI ที่เสียค่าใช้จ่ายระหว่าง build

ตัวแอปและคำสั่งทำงานด้วยสิทธิ์ผู้ใช้ **ไม่ใช่ sandbox** ไม่ควรรันด้วย root การแพ็กไม่ได้ทำให้คำสั่ง/โจทย์ที่ไม่น่าเชื่อถือปลอดภัยขึ้น

## ขอบเขตระบบที่รองรับ

แพ็กเกจนี้ build สำหรับ **Linux x86_64** บน Kali Rolling, glibc 2.42 ดู Python/ไลบรารี/ระบบ build ใน `manifest.json` ไม่ใช่ Windows executable และยังไม่รับรอง Ubuntu รุ่นเก่าหรือทุก Linux distribution หากต้องแจกหลาย distro ควร build บนระบบฐานที่เก่าที่สุดที่ตั้งใจรองรับ แล้วทดสอบ VM สะอาดแต่ละรุ่น โดยเฉพาะ glibc, Tcl/Tk, Drag & Drop และเครื่องมือภายนอก

เก็บ symbolic links ของแพ็กเกจไว้ ใช้ tar.gz และ filesystem ที่รองรับ symlink เมื่อต้องแจก ไม่แนะนำให้คัดลอกไฟล์แยกผ่าน FAT/exFAT โดยไม่ใช้ archive

## Build จาก source

```bash
python3 -m venv build/venv-linux
build/venv-linux/bin/python -m pip install -r packaging/requirements-build.txt
build/venv-linux/bin/python packaging/build.py --version 0.1.0
```

สคริปต์ปฏิเสธการเขียนทับ release เดิม เลือก version ใหม่เมื่อต้อง build ใหม่ รวมเฉพาะ defaults ที่ผ่านการตรวจใน `packaging/defaults` ไม่ดึง JSON ส่วนตัวจาก workspace มาแจก ใช้ PyInstaller แบบ onedir; ไฟล์ `.spec` ต้องอยู่ใน version control

## ตรวจแพ็กเกจ

```bash
./UNIT --check-tools
xvfb-run -a ./UNIT --smoke-test
```

Smoke test ใช้ profile/ไฟล์ชั่วคราว ทดสอบเปิด 8 หน้า, โหลด TkDnD, Regex Unicode/timeout, codec, Strings, Pipeline Base64, บันทึก History/Export/Saved Pipeline และปิดแอป ไม่เชื่อมต่อ Gemini ไม่แก้ข้อมูลผู้ใช้ และไม่ได้แทนการทดสอบลากไฟล์ด้วยเมาส์หรือ VM สะอาดจริง

ข้อมูลอ้างอิง: [PyInstaller runtime](https://pyinstaller.org/en/stable/runtime-information.html), [external-program environment](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html), [TkinterDnD2 packaging](https://github.com/Eliav2/tkinterdnd2). ตรวจใบอนุญาตของ dependency/ไลบรารีระบบที่รวมไปก่อนเผยแพร่ต่อสาธารณะ
