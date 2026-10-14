# ติดตั้ง Gemini CLI บน VM ใหม่เพื่อใช้กับ UNIT

คู่มือนี้ใช้ **Ubuntu/Debian Linux VM** เป็นเส้นทางหลัก เพราะ UNIT รุ่นแพ็กปัจจุบันเป็น Linux x86_64. Gemini CLI ต้องมี Node.js 20 ขึ้นไป, อินเทอร์เน็ต และคำสั่ง `gemini` ต้องอยู่ใน `PATH` ที่ UNIT มองเห็น. เอกสารทางการแนะนำ Ubuntu 20.04+, RAM อย่างน้อย 4 GB สำหรับงานทั่วไป และ 16 GB สำหรับงานยาวหรือ codebase ใหญ่

> คำสั่งในคู่มือนี้ติดตั้ง Gemini CLI เท่านั้น ไม่ได้ติดตั้ง Pipeline tools อื่นของ UNIT. อย่ารัน UNIT หรือ Gemini CLI ด้วย `sudo` และอย่าใส่ API key ลง repository

## 1. เตรียม VM

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
uname -m
cat /etc/os-release
```

แพ็กเกจ UNIT Linux ที่ repository นี้สร้างรองรับ `x86_64`/`amd64`; ถ้า VM เป็น `aarch64` ต้องรัน UNIT จาก source หรือสร้างแพ็กเกจสำหรับ architecture นั้นเอง

## 2. ติดตั้ง Node.js 20 ขึ้นไป

ตรวจของเดิมก่อน:

```bash
node --version
npm --version
```

ถ้า `node` เป็น `v20` หรือใหม่กว่า ให้ข้ามไปข้อ 3. ถ้าไม่มีหรือเก่ากว่า ให้เลือก **วิธี A หรือ B เพียงวิธีเดียว**

### วิธี A — NVM สำหรับ VM ทดลอง (แนะนำ)

NVM ติดตั้ง Node แยกในบัญชีผู้ใช้. คำสั่งนี้ใช้ installer ของโครงการ NVM รุ่น `v0.40.8`; VM ที่ต้องการความเข้มงวดควรดาวน์โหลดมาตรวจเนื้อหาก่อนรัน

```bash
curl -o /tmp/install-nvm.sh https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh
less /tmp/install-nvm.sh
bash /tmp/install-nvm.sh
```

ปิดแล้วเปิด terminal ใหม่ หรือโหลด NVM ใน shell ปัจจุบัน:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

ติดตั้ง Node LTS และตั้งเป็นค่าเริ่มต้น:

```bash
nvm install --lts
nvm alias default 'lts/*'
node --version
npm --version
```

เมื่อใช้วิธีนี้ ให้เปิด UNIT จาก terminal เดียวกับที่ `node`, `npm` และ `gemini` ทำงาน หรือเปิด terminal ใหม่หลังติดตั้ง. Desktop launcher บางระบบไม่อ่าน `.bashrc` จึงอาจไม่เห็น PATH ของ NVM

### วิธี B — Node ของระบบสำหรับ desktop launcher

ติดตั้ง Node.js 20+ จาก package source ที่ผู้ดูแล VM เชื่อถือ แล้วตรวจเวอร์ชัน:

```bash
node --version
npm --version
```

วิธีนี้เหมาะเมื่อจะเปิด UNIT จากไอคอน เพราะ `/usr/bin/node` มักอยู่ใน desktop-session PATH. ห้ามใช้ Node รุ่นต่ำกว่า 20 แม้ package manager ของ distribution จะติดตั้งสำเร็จ

## 3. ติดตั้ง Gemini CLI

```bash
npm install -g @google/gemini-cli@latest
command -v gemini
gemini --version
```

`command -v` ต้องแสดง path และ `gemini --version` ต้องจบด้วย exit code 0. `npx @google/gemini-cli` ใช้ทดลองโดยไม่ติดตั้งได้ แต่ UNIT เรียก executable ชื่อ `gemini` โดยตรง จึงควรติดตั้ง global

## 4. เลือกวิธียืนยันตัวตน

### ทางเลือก A — Sign in with Google บน VM ที่มี desktop

```bash
gemini
```

เลือก `Sign in with Google`, เปิดลิงก์ใน browser และล็อกอินให้เสร็จ. Credential จะถูกเก็บโดย Gemini CLI สำหรับครั้งต่อไป. บัญชีบริษัท โรงเรียน หรือ Google Workspace อาจต้องกำหนด Google Cloud project ตามนโยบายองค์กร

หลังเข้าสู่ระบบแล้ว ออกจาก interactive CLI และทดสอบ mode ที่ UNIT ใช้:

```bash
gemini -p "Reply with exactly: GEMINI_OK"
```

### ทางเลือก B — Gemini API key สำหรับ headless VM

สร้าง key จาก [Google AI Studio](https://aistudio.google.com/apikey) แล้วตั้งเฉพาะใน shell ปัจจุบัน:

```bash
read -rsp "Gemini API key: " GEMINI_API_KEY
echo
export GEMINI_API_KEY
gemini -p "Reply with exactly: GEMINI_OK"
```

อย่าเขียน key ลง README, Git, shell history หรือ image/template ของ VM. สำหรับ UNIT สามารถไม่ export ตัวแปรและวาง key ในช่อง `API_KEY` แทนได้; UNIT ส่ง key ให้ subprocess ผ่าน environment และไม่ได้บันทึกช่องนี้ลง config

ถ้าต้องใช้ key แบบถาวร ให้เก็บใน secret manager หรือไฟล์ที่จำกัดสิทธิ์ ไม่ commit `.env`:

```bash
mkdir -p "$HOME/.gemini"
touch "$HOME/.gemini/.env"
chmod 600 "$HOME/.gemini/.env"
```

จากนั้นใช้ editor ใส่ `GEMINI_API_KEY=...` ใน `$HOME/.gemini/.env`

## 5. ทดสอบให้ตรงกับ UNIT

UNIT ตรวจ `gemini --version` และ `gemini -m MODEL -p "hi"` ตอนกด `[ CONNECT_CLI ]`. เริ่มจาก default model:

```bash
gemini -p "hi"
```

จากนั้นทดสอบชื่อเดียวกับที่เลือกใน UNIT เช่น:

```bash
gemini -m gemini-2.5-flash -p "hi"
```

ชื่อและสิทธิ์ใช้ model เปลี่ยนได้ตามเวลาและบัญชี. ถ้า default ผ่านแต่ `-m` ไม่ผ่าน ให้เลือก model อื่นใน UNIT; model error ไม่ได้แปลว่า npm installation เสีย

## 6. เปิด UNIT ให้เห็นคำสั่ง Gemini

### UNIT จาก source

หลังติดตั้ง dependency ของ UNIT ตาม README ให้เปิดจาก terminal ที่ทดสอบ `gemini` ผ่านแล้ว:

```bash
cd /path/to/Unit
source .venv/bin/activate
python app.py
```

จากหน้า **Gemini CLI**:

1. ใช้ API key หรือ credential ที่ล็อกอินไว้แล้วอย่างใดอย่างหนึ่ง
2. เลือก model
3. กด `[ CONNECT_CLI ]`
4. รอข้อความ `CONNECTED`
5. ทดลอง prompt ที่ไม่สั่งแก้ไฟล์ก่อน

### UNIT แบบแพ็ก

```bash
cd /path/to/extracted/UNIT-folder
./UNIT
```

การเปิดจาก terminal ทำให้แอปสืบทอด PATH ของ NVM/npm. ถ้าเปิดจากไอคอนแล้วแจ้ง `Command 'gemini' was not found` แต่ terminal หาเจอ แปลว่า desktop launcher มี PATH ต่างกัน ไม่ใช่ Gemini ติดตั้งล้มเหลว

```bash
command -v node
command -v gemini
npm prefix -g
```

สำหรับ VM ทดลอง ให้เปิด `./UNIT` จาก terminal. หากต้องใช้ไอคอนถาวร ให้ติดตั้ง Node/Gemini ใน path ที่ desktop session เห็นหรือกำหนด PATH ตามมาตรฐาน distribution แล้ว log out/login ใหม่; ไม่ควร symlink ไป path ของ Node version ที่ NVM อาจเปลี่ยน

แพ็กเกจ UNIT ที่ build จาก Kali/glibc รุ่นใหม่อาจเปิดไม่ได้บน Ubuntu ที่มี glibc เก่ากว่า แม้ Gemini CLI ติดตั้งสมบูรณ์แล้ว. ถ้า `./UNIT` แจ้ง loader หรือ `GLIBC_x.y not found` ให้ทดสอบ UNIT จาก source หรือ build package ใหม่ภายใน distro ฐานเดียวกับ VM; ปัญหานี้แยกจาก Node/Gemini

## 7. Checklist

```text
[ ] architecture ตรงกับแพ็กเกจ UNIT หรือรัน UNIT จาก source
[ ] node --version เป็น v20 ขึ้นไป
[ ] npm --version ทำงาน
[ ] command -v gemini คืน path
[ ] gemini --version ทำงาน
[ ] gemini -p "hi" ตอบได้ด้วย credential ที่เลือก
[ ] model ที่เลือกใน UNIT ใช้ผ่าน -m ได้
[ ] UNIT เปิดจาก environment ที่มองเห็น path เดียวกัน
[ ] [ CONNECT_CLI ] แสดง CONNECTED
```

## 8. แก้ปัญหาที่พบบ่อย

| อาการ | ตรวจ | วิธีแก้ |
|---|---|---|
| `node: command not found` | `command -v node` | ติดตั้ง Node 20+ และเปิด shell ใหม่ |
| Node ต่ำกว่า 20 | `node --version` | ใช้ Node LTS ใหม่ผ่าน NVM หรือ package source |
| `gemini: command not found` | `npm prefix -g`; `command -v gemini` | ติดตั้ง global ใหม่และแก้ PATH ของ session |
| terminal ใช้ได้ แต่ UNIT หาไม่เจอ | เปิด UNIT จาก terminal | แก้ desktop-session PATH หรือใช้ system Node |
| `UNAUTHENTICATED` | รัน `gemini` | Sign in ใหม่หรือกำหนด `GEMINI_API_KEY` |
| OAuth เปิด browser ไม่ได้ | ตรวจว่า VM เป็น headless หรือไม่ | ใช้ API key หรือ Vertex AI credential |
| model not found/permission denied | `gemini -m MODEL -p "hi"` | เลือก model ที่บัญชีรองรับ |
| connection timeout | `gemini -p "hi"` | ตรวจ DNS, proxy, firewall, เวลาเครื่อง และบริการ Google |
| `EACCES` ตอนติดตั้ง global | `npm prefix -g` | ใช้ NVM/user-local Node; อย่ารัน UNIT เป็น root |
| untrusted directory | รัน `gemini` ใน directory นั้นหนึ่งครั้ง | ยืนยัน trust; UNIT ตั้ง `GEMINI_CLI_TRUST_WORKSPACE=true` ให้ subprocess ด้วย |

## 9. อัปเดตและถอน

```bash
# อัปเดต stable
npm install -g @google/gemini-cli@latest
gemini --version

# ถอนเฉพาะ package
npm uninstall -g @google/gemini-cli
```

การถอน npm package ไม่ลบ credential/cache อัตโนมัติ. ตรวจ `$HOME/.gemini` แยกก่อนลบ

## แหล่งอ้างอิง

- [Gemini CLI — Get started](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/index.md)
- [Gemini CLI — Installation](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/installation.mdx)
- [Gemini CLI repository และ authentication overview](https://github.com/google-gemini/gemini-cli)
- [NVM installation](https://github.com/nvm-sh/nvm#installing-and-updating)
- พฤติกรรมเฉพาะ UNIT: `pages/gemini.py:64-109,356-447`
