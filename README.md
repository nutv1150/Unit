# UNIT — การติดตั้งและเปิดใช้งาน

UNIT (Unified Toolkit) เป็นโปรแกรมเดสก์ท็อปสำหรับแปลงข้อมูล ตรวจไฟล์ และเรียกเครื่องมือวิเคราะห์ผ่าน Pipeline

## วิธีที่ 1: เปิดโปรแกรมสำเร็จรูปบน Linux x86_64

ในโฟลเดอร์ `dist/` มีโปรแกรมรุ่น **0.1.6** และไฟล์ `.tar.gz` สำหรับนำไปติดตั้งอีกเครื่อง

1. เปิดโฟลเดอร์ `dist/UNIT-0.1.6-linux-x86_64/` หากใช้ไฟล์ `.tar.gz` ให้แตกไฟล์ก่อน
2. เก็บทั้งโฟลเดอร์ไว้ด้วยกัน รวมถึง `_internal/` ห้ามย้ายเฉพาะ executable `UNIT`
3. ดับเบิลคลิก `UNIT` หรือรันจากโฟลเดอร์โปรเจกต์:

```bash
./dist/UNIT-0.1.6-linux-x86_64/UNIT
```

แพ็กเกจรวม Python และไลบรารีของแอปไว้แล้ว ไม่ต้องติดตั้ง `Requirements.txt` สำหรับวิธีนี้

หากต้องการสร้างไอคอนในเมนูแอป:

```bash
./dist/UNIT-0.1.6-linux-x86_64/install-user.sh
```

ไม่ต้องใช้ sudo สคริปต์สร้าง shortcut ไปยังตำแหน่งปัจจุบัน หากย้ายโฟลเดอร์ภายหลังต้องจัดการ shortcut ใหม่ รายละเอียดอยู่ใน [คู่มือติดตั้ง Linux](docs/linux-package.md)

## ติดตั้งเครื่องมือภายนอก

โปรแกรมอย่าง OpenSSL, 7z, ExifTool, zsteg และเครื่องมือใน App Portal ต้องติดตั้งแยกตามงานที่ใช้งาน

เปิด `Install UNIT Dependencies.desktop` หรือรันจากโฟลเดอร์ Unit:

```bash
bash install_dependencies.sh
```

ตัวติดตั้งสำหรับระบบที่ใช้ APT เช่น Kali จะแสดงรายการและถามยืนยันก่อนติดตั้ง เลือกเฉพาะเครื่องมือหลักได้ด้วย:

```bash
bash install_dependencies.sh --core-only
```

ดูแผนหรือตรวจเครื่องมือโดยไม่ติดตั้ง:

```bash
bash install_dependencies.sh --plan
bash install_dependencies.sh --check
./dist/UNIT-0.1.6-linux-x86_64/UNIT --check-tools
```

การติดตั้งใช้เครือข่ายและอาจขอ sudo สำหรับแพ็กเกจระบบ ส่วนการเปิด UNIT ใช้สิทธิ์ผู้ใช้ปกติ Gemini CLI ต้องติดตั้งและยืนยันตัวตนแยก ผล `FOUND` หมายถึงพบ executable ไม่ใช่การยืนยันว่าทุกฟังก์ชันพร้อมใช้งาน

## วิธีที่ 2: รันจากซอร์ส Python

เปิด Terminal ในโฟลเดอร์ Unit ใช้ Python ที่มี Tkinter หากระบบ Debian/Kali ยังไม่มีเครื่องมือพื้นฐาน:

```bash
sudo apt install python3 python3-venv python3-tk
```

สร้าง environment และติดตั้งไลบรารี:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r Requirements.txt
.venv/bin/python app.py
```

หาก `.venv` เดิมใช้งานได้แล้ว เรียก `.venv/bin/python app.py` ได้เลย ชื่อไฟล์ `Requirements.txt` ใช้ R ตัวใหญ่

## ข้อมูลและการตั้งค่า

- รันจากซอร์ส: ข้อมูลอยู่ใน `data/`, `config/` และไฟล์ JSON ของโปรเจกต์
- โปรแกรมสำเร็จรูป: ข้อมูลอยู่ที่ `$XDG_DATA_HOME/unit` หรือ `~/.local/share/unit`
- `UNIT_DATA_HOME` ใช้กำหนดตำแหน่งข้อมูลเองได้ โดยต้องเป็น absolute path
- การตั้งค่าและประวัติเดิมยังคงอยู่ ไม่ต้องลบเพื่อติดตั้ง dependencies

## โครงสร้างที่เก็บไว้

| รายการ | หน้าที่ |
|---|---|
| `app.py`, `sidebar.py`, `pages/` | โปรแกรมหลักและหน้าจอ |
| `Encode/`, `Decode/`, `Hashing/`, `Tools/`, `Pipeline/` | การประมวลผลและระบบเครื่องมือ |
| `config/`, `data/`, `custom_tools.json` | การตั้งค่าและข้อมูลของแอป |
| `Requirements.txt`, `.venv/` | ไลบรารีสำหรับรันซอร์ส |
| `install_dependencies.sh`, `Install UNIT Dependencies.desktop` | ตัวช่วยติดตั้งเครื่องมือภายนอก |
| `packaging/` | ไฟล์สำหรับสร้างแพ็กเกจ ตัวติดตั้ง ไอคอน และค่าเริ่มต้น |
| `dist/` | โปรแกรมสำเร็จรูปรุ่น 0.1.6 และ archive สำหรับแจก |
| `docs/linux-package.md` | คู่มือติดตั้ง สร้างแพ็กเกจ และตรวจการทำงาน |

แพ็กเกจที่มีอยู่สร้างสำหรับ Linux x86_64 ไม่ใช่ Windows executable และไม่ได้รับรองทุก Linux distribution ดูข้อกำหนดระบบและวิธีแก้ปัญหาเพิ่มเติมใน [คู่มือติดตั้ง Linux](docs/linux-package.md)
