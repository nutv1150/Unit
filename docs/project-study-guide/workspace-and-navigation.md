# Navigation, Dashboard, App Portal, My Tools และ Challenge

## Entry point และ sidebar

`app.py` ตั้ง appearance Light แต่หน้าหลักหลายหน้ากำหนดสีเข้มเอง, เรียก `initialize_user_data()`, เปิด TkDND, สร้าง store และ instantiateทั้ง 8 pagesทันที (`app.py:20-76`). Sidebarเรียง:

1. Dashboard
2. Data Hashing
3. File Inspection
4. Pipeline
5. Gemini CLI
6. App Portal
7. My Tools
8. Challenge

click → `Sidebar.on_click()` → `UNITApp.switch_page(name)`; ซ่อนทุกหน้า, เทียบชื่อแบบ strip+lower, gridหน้าเป้าหมาย, เรียก `on_show()`ถ้ามี และ update highlight (`sidebar.py:27-69`; `app.py:79-109`). Unknown nameเพียง print error

`navigate_to(name,sub)` รองรับ My Tools deep link:

- Data Hashing: sub `XOR` → Bitwise/XOR Mask; อื่น → Decodeและเลือก sub
- File Inspection: set toolและ `on_tool_change()` ซึ่งอาจรันทันทีถ้ามีไฟล์เดิม
- App Portal: set search text; **ไม่ launch**
- pageอื่น/sub None: แค่เปิดหน้า (`app.py:111-125`)

ปิดแอป: Challenge `pause_all()`ต้องบันทึกสำเร็จก่อน; cancel Pipeline/Gemini; History eventsที่ยัง activeถูก finish Failed; close SQLite; destroy (`app.py:126-144`)

## Dashboard

### สิ่งที่แสดง

`on_show()` refreshจาก `DashboardStore.get_snapshot()`:

- Operations = จำนวน events สูงสุด 2,000ที่ยังเก็บ
- Flags = ผลรวมรายการ pattern matchesที่แต่ละหน้า report; ไม่ใช่ unique/verified
- Files = จำนวน absolute file pathsไม่ซ้ำ
- Success Rate = round(success events / all events ×100)
- competition rows: ops/files/flags/successแยก active labelของ event
- Top 3 toolsด้วย count
- Recent filesไม่ซ้ำสูงสุด 6, พร้อม exists/missing; Inspectเปิด File Inspectionและรันทันที

CODE: `pages/dashboard.py:233-469`; aggregation `Tools/dashboard_store.py:407-495`.

### System Check

ปุ่มเปิดหน้าต่างและทำ read-only scan background (`pages/dashboard.py:45-71`; `Tools/system_check.py`). รายการเริ่มมี `file, exiftool, zsteg, gemini, node, x-terminal-emulator, bash, wireshark, ghidra, nmap, hashcat, burpsuite, msfconsole` แล้วเพิ่ม executableแรกของทุก Pipeline tool. `shutil.which`ให้ FOUND/MISSING; ไม่รัน, install, check version, authหรือfeature. Refresh scanซ้ำ. แสดง user data root

### History

เปิด Solve History filter `All`; Data Hashing/File Inspection/Pipelineเปิด filterของตัวเอง. ดู [persistence-and-history.md](persistence-and-history.md)

### Pin Tool

รายการสร้างสดจาก:

- ทุก pageยกเว้น Dashboard → `page:NAME`
- Pipeline registered tools → `pipeline_tool:NAME`
- saved pipelines → `pipeline_saved:NAME`
- App Portal tools → `portal:NAME`

เลือก categoryและ shortcut `None`, `Ctrl+1..9`, `Alt+1..9`. Save targetซ้ำคือ update; shortcutซ้ำถูกย้ายออกจาก favoriteเดิม (`pages/dashboard.py:476-607`; `Tools/dashboard_store.py:292-331`). Default stateเมื่อไม่มีไฟล์ pin Data Hashing Ctrl+1, File Inspection Ctrl+2, Pipeline Ctrl+3

Open:

- page → navigate
- pipeline tool → เปิด Pipelineและ add node (modeปัจจุบันมีผล; Stepอาจ clear)
- saved pipeline → เปิด/โหลด Auto
- portal → launchทันทีและปล่อย Portalเป็นผู้บันทึก status

shortcut parseยอม Ctrl/Control/Alt/Shiftก่อน key แต่ popupเสนอเพียง Ctrl/Altตัวเลข (`pages/dashboard.py:766-865`)

### Manage Categories/Competitions

Categories: addชื่อ non-empty; Coreลบไม่ได้; ลบ categoryย้าย favoritesกลับ Core. Competition popupเพิ่มชื่อและตั้ง active; competitionที่เคยใช้ไม่มี delete UI. Active competition selectorอยู่ในสถิติของหน้าและ `change_competition()`บันทึก store (`609-756`). Dashboard “competition” สำหรับจัดกลุ่ม activityต่างจากหน้า Challenge timer

## App Portal

### Default cards

| Card | จุดประสงค์ตาม UI | launch behavior |
|---|---|---|
| Wireshark | packet GUI | `wireshark` |
| Burp Suite | web security GUI | `burpsuite` |
| Ghidra | reverse engineering | `ghidra` |
| Nmap | interactive CLI | terminal + bash `read` + `eval` |
| Metasploit | framework console | terminal `msfconsole; exec bash` |
| Hashcat | interactive CLI | terminal + bash `read` + `eval` |
| CyberChef | web app | Firefoxเปิด official GitHub Pages URL |
| Terminal | terminal | `x-terminal-emulator`; description “root shell”ไม่ถูกยืนยันจาก command |

Search match name/description case-insensitive. Launchตรวจ `which(check)`, spawn `shell=True`, discard output; 50 msต่อมา poll. Processยังอยู่หรือ launcher exit 0ไม่ถือว่า appทำงานสำเร็จ—statusระบุ not verified (`pages/app_portal.py:142-253`). รายละเอียด commandตรง [external-tools.md](external-tools.md)

### Custom tool

schema list:

| field | required | default UI | ใช้ตรงไหน |
|---|---|---|---|
| `name` | non-empty string | — | display/search/activity |
| `desc` | string | `Custom Module` | search/card |
| `icon` | string | 🛠️ | card |
| `check` | non-empty string | — | `shutil.which(check)`; ต้องเป็น executable/path ไม่ใช่ command line |
| `cmd` | non-empty string | terminal shell template | ส่งทั้ง stringให้ system shell |

Add/Edit/Deleteใช้ atomic temp+fsync+replace; invalid JSON/schemaทำหน้า read-onlyและไม่ overwrite original (`pages/app_portal.py:94-140`). Deleteไม่มี confirmationใน code. Browse Installed Apps scan `/usr/share/applications/*.desktop` และ `~/.local/share/applications/*.desktop`, อ่าน Name/Execแรก, ตัด field codeหลัง `%`, เลือก executable tokenแรก, ข้าม NoDisplay/Terminal. Parserนี้ไม่ใช่ desktop-entry parserเต็มและ pathมี space/quoted complexอาจถูกตัด (`418-507`)

Custom `cmd` ไม่มี placeholder substitution; shellจัด quoting/env/glob/pipe. อย่าใส่ untrustedโจทย์ต่อ commandโดยไม่ตรวจ

## My Tools

หน้าเป็น organizer/deep links ไม่ใช่ registryของ executable. Built-in chip choices 9 (`pages/my_tools.py:5-15`):

| Chip | destination/sub | ผล click |
|---|---|---|
| Base64 decode | Data Hashing/Base64 | Decode Base64และ process inputเดิม |
| ROT decode | Data Hashing/ROT | Decode ROT |
| Hex decode | Data Hashing/Hex | Decode Hex |
| XOR bitwise | Data Hashing/XOR | Bitwise XOR Mask |
| File Inspection | File Inspection/None | เปิดหน้า |
| zsteg | File Inspection/zsteg Analysis | เลือก zsteg; ถ้ามีไฟล์เดิมรันทันที |
| Pipeline | Pipeline/None | เปิดหน้า |
| Wireshark | App Portal/Wireshark | filter card; ไม่ launch |
| Burp Suite | App Portal/Burp Suite | filter card; ไม่ launch |

New/Edit dialogต้องชื่อ non-emptyและเลือกอย่างน้อยหนึ่ง. groupเก็บ UUID, name, colorจาก toolแรก, deep-link tool copies. Searchกรองชื่อ groupเท่านั้น. Layout 1/2/3 columnsตาม width. Deleteมี confirm. Custom entriesเดิมที่ไม่อยู่ built-in listยังคงแสดงใน editเพื่อไม่ทำข้อมูลหาย (`pages/my_tools.py:18-170`; `Tools/workspace_store.py:15-43`)

config invalid/missing IDs/duplicate IDsทำหน้า read-onlyและรักษา original. Saveเขียน `.tmp` แล้ว `os.replace`

## Challenge

หน้า Challengeเป็น local progress/timer ไม่สัมพันธ์โดยอัตโนมัติกับ Dashboard competitions

### Create

- Competition name stripแล้วต้องไม่ว่าง
- Total itemsรับ ASCII digitsและ integer ≥1
- recordใหม่ solved 0, elapsed 0, paused (`pages/challenge.py:21-65`; `Tools/workspace_store.py:94-100`)

### Table/editor

click Name/Time/Scoreหรือ editเปิด editor. `Solved` ต้อง ASCII integer 0..total. Start/Pauseเรียก store updateทันทีโดยใช้ solved valueเดิมจาก store—ข้อความ scoreที่แก้แต่ยังไม่ Saveไม่ถูกบันทึกตอน toggle. Saveเก็บ entry scoreและ running stateปัจจุบัน. Deleteทั้งแถว/editorมี confirmation (`pages/challenge.py:67-157`)

timer display updateทุก 1 s แต่ elapsedคำนวณจาก:

```text
elapsed_seconds + max(0, now - resume_timestamp)   เมื่อ running
```

ทุก update materialize elapsedถึง now, ตั้ง resume timestampใหม่ถ้ายัง runningแล้ว save. ปิด UNITเรียก `pause_all`: materializeทุกตัว, set paused/null timestamp. หาก processถูก kill, recordยัง runningพร้อม timestamp; เปิดใหม่จึงคำนวณช่วงที่ appปิดรวมไปด้วย จนกว่าจะ pause/save

### Persistence/error

configเป็น JSON listที่ IDs unique; name/total/solved/bool/finite nonnegative timer validateทั้งหมด (`Tools/workspace_store.py:70-124`). Invalid configทำหน้าไม่มี store, disable Create, ไม่ overwrite. การปิด appถ้า pause_all saveล้มเหลว แอปยกเลิกการปิดและพากลับหน้า Challenge (`app.py:126-132`)

## การเปลี่ยน state และข้อควรจำ

| Action | state/file |
|---|---|
| Dashboard event/pin/category/competition | `data/dashboard_state.json` source mode หรือ user data root packaged |
| My Tools group | `config/my_tools_groups.json` |
| Challenge create/update/delete/pause | `config/challenges.json` |
| App Portal custom | `custom_tools.json` |
| Pipeline tools/saves | `Pipeline/custom_tools.json`, `Pipeline/saved_pipelines.json` |

ทุกไฟล์ข้างต้นเป็น user state. คู่มือนี้ไม่แก้และไม่คัดค่าปัจจุบัน. ดู path selection/atomic behaviorเพิ่มใน [persistence-and-history.md](persistence-and-history.md)

