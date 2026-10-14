# Inventory และ checklist หลัก

สถานะเข้าถึง: **UI** = เปิดใช้จาก GUI, **conditional** = ต้องมีข้อมูล/โปรแกรม/credential, **backend** = มีโค้ดแต่ไม่มี UI โดยตรง, **internal** = worker/build command. สถานะเอกสาร `done` หมายถึงมีรายละเอียดในไฟล์ปลายทางที่ระบุ

| หมวด | หน้า/แท็บ | คำสั่ง/เครื่องมือ | ตัวเลือก/โหมด | ไฟล์และฟังก์ชัน | เข้าถึง | เอกสาร |
|---|---|---|---|---|---|---|
| Shell | Sidebar | เปลี่ยนหน้า 8 หน้า | ชื่อเทียบ case-insensitive | `sidebar.py:27-69`; `app.py:79-125` | UI | [done](workspace-and-navigation.md) |
| Dashboard | Main | Refresh on show, System Check, History | All history; PATH discovery | `pages/dashboard.py:45-90,233-254`; `Tools/system_check.py:9-63` | UI | [done](workspace-and-navigation.md) |
| Dashboard | Stats | operations, flags, files, success rate, competition stats, top 3, recent files | recent limit 6; success = status string | `pages/dashboard.py:92-209`; `Tools/dashboard_store.py:407-495` | UI | [done](workspace-and-navigation.md) |
| Dashboard | Favorites | pin/open/remove, category add/delete, shortcut | page/pipeline tool/saved pipeline/portal; Core; None, Ctrl/Alt+1..9 | `pages/dashboard.py:256-345,476-865` | UI | [done](workspace-and-navigation.md) |
| Data Hashing | Decode | Auto Detect; Base64/32/45/85/58/62/Ascii85/16; Hex; Binary/Octal/Decimal; URL-safe Base64; URL Decode; HTML Entity; Unicode Escape; Reverse; ROT | custom Hex alphabet; ROT n; alpha/ascii | `pages/data_hash.py:140-149,461-501`; `Decode/base_decoder.py` | UI | [done](data-hashing.md) |
| Data Hashing | Encode | Base64/32/45/85/16/58/62; Hex; Binary/Octal/Decimal; URL Encode; URL-safe Base64; HTML Entity; Unicode Escape; Reverse; ROT | ROT n; alpha/ascii | `pages/data_hash.py:130-138`; `Encode/base_encoder.py` | UI | [done](data-hashing.md) |
| Data Hashing | Hash | MD5, SHA-1, SHA-224/256/384/512, SHA3-224/256/384/512, BLAKE2b/s | ไม่มี digest length ใน UI | `pages/data_hash.py:151-157`; `Hashing/hash_utils.py:3-33` | UI | [done](data-hashing.md) |
| Data Hashing | Hash backend | SHAKE128, SHAKE256 | `length=32` bytes default API | `Hashing/hash_utils.py:19-31` | backend | [done](data-hashing.md) |
| Data Hashing | Bitwise | XOR Mask/Unmask, OR Mask, AND Mask | key explicit/embedded; smart byte formats | `pages/data_hash.py:159-165,489-500`; `Tools/extra_tools.py:61-473` | UI | [done](data-hashing.md) |
| Data Hashing | Common | Browse, live process, Find, Save Raw, View Full, send selection to Gemini, History | 64 MiB file cap; 16 KiB background threshold; 12,000-char preview | `pages/data_hash.py:302-384,503-734` | UI | [done](data-hashing.md) |
| File Inspection | Input/nav | Browse, multi-file DnD, All/per-file result | valid files only; automatic run on load/tool change | `pages/file_inspection.py:343-587` | UI | [done](file-inspection.md) |
| File Inspection | Analyze | `'file' Command`, Header Check, Executable Check, Strings, zsteg Analysis, Exiftool | Max 1..100000; regex only Strings | `pages/file_inspection.py:374-424,624-741` | conditional | [done](file-inspection.md) |
| File Inspection | Regex/search | 7 runtime presets + custom, clear, preview search | ignore case; worker timeout 2 s; 10,000 matches | `pages/file_inspection.py:185-290,309-332,831-862`; `Tools/regex_runner.py` | UI/internal | [done](file-inspection.md) |
| File Inspection | Output | Clear All, Find, View/Save Full, forward selection to Hashing/Gemini | 128 KiB visible preview | `pages/file_inspection.py:48-181,426-558` | UI | [done](file-inspection.md) |
| Pipeline | Canvas | add, drag/reorder, clear, Auto/Step, Run All/Run Step | workspace แยกตาม mode | `pages/pipeline.py:42-550` | UI | [done](pipeline.md) |
| Pipeline | Templates | Basic Recon, Find Flag, Decode Base64, Stego Scan, Forensics Scan | fixed node sequences | `pages/pipeline.py:1785-1805` | UI | [done](pipeline.md) |
| Pipeline | Step window | Browse; Previous/Original/Set; preset/manual args; Run/Cancel/Next/Close; Continue/Finish | before/after input; stdout/file selection | `pages/pipeline.py:558-1782` | UI | [done](pipeline.md) |
| Pipeline | Persistence | Add Tool; Add Pipeline wizard; save/load pipeline | text/file; params; custom checkbox/text options | `pages/pipeline.py:1808-2344`; `Pipeline/config_store.py` | UI | [done](pipeline.md) |
| Pipeline | File Analysis | xxd, hexdump | `-r`, `-p`, `-C` | `Pipeline/custom_tools.json:2-34` | conditional | [done](external-tools.md) |
| Pipeline | Archive Extraction | 7zip_extract, unzip, tar_extract | `x`, `-y`, `-x`, `-f`, `-v`, `-C` | `Pipeline/custom_tools.json:35-81` | conditional | [done](external-tools.md) |
| Pipeline | Steganography | zsteg, zbarimg, steghide, binwalk_extract | `-e` | `Pipeline/custom_tools.json:82-122` | conditional | [done](external-tools.md) |
| Pipeline | Forensics | binwalk, foremost, exiftool, tshark, dd | `-i`; `-r`; `if=` | `Pipeline/custom_tools.json:123-171` | conditional | [done](external-tools.md) |
| Pipeline | Cryptography | base64/base32 decode, rot13, hex decode, gzip decompress, URL decode, reverse, openssl enc | `-d`, `-i`, `-r -p`, `-I -c`, manual OpenSSL | `Pipeline/custom_tools.json:172-270` | conditional | [done](external-tools.md), [OpenSSL](openssl.md) |
| Pipeline | Pwnable | checksec, file, md5sum | positional file | `Pipeline/custom_tools.json:271-299` | conditional | [done](external-tools.md) |
| Pipeline | Mobile | apktool, jadx, dex_strings | `d` checkbox | `Pipeline/custom_tools.json:300-333` | conditional | [done](external-tools.md) |
| Pipeline | Programming | grep, cut, sort, uniq, awk | `-n`, `-v`, pattern; `-d`, `-f`; awk script | `Pipeline/custom_tools.json:334-393` | conditional | [done](external-tools.md) |
| Pipeline | Reverse Engineering | strings, objdump | `-n`, `-d` | `Pipeline/custom_tools.json:394-420` | conditional | [done](external-tools.md) |
| Pipeline | Network | tcpdump | `-r` | `Pipeline/custom_tools.json:421-430` | conditional | [done](external-tools.md) |
| Gemini CLI | Connection | reveal key, Connect CLI, model select | 4 model strings; API key optional | `pages/gemini.py:64-109,272-446` | conditional | [done](gemini-cli.md) |
| Gemini CLI | Request | Browse path, Execute, Stop, View Full Response/Command Output, forward selection | 1 MiB/attachment, 4 MiB prompt, 6 recent turns, 3 retries | `pages/gemini.py:120-250,468-615` | conditional | [done](gemini-cli.md) |
| Gemini CLI | Agent tags | `[EXEC]`, `[SAVE:path]`, ALLOW/DENY | max 2 EXEC rounds; shell 30 s; Gemini 300 s | `pages/gemini.py:617-699` | conditional | [done](gemini-cli.md) |
| App Portal | Default | Wireshark, Burp, Ghidra, Nmap, Metasploit, Hashcat, CyberChef, Terminal | fixed `check` and shell `cmd` | `pages/app_portal.py:28-39,221-253` | conditional | [done](workspace-and-navigation.md) |
| App Portal | Custom | search, add/edit/delete/launch, browse installed GUI apps | name/desc/icon/check/cmd | `pages/app_portal.py:94-507` | UI/conditional | [done](workspace-and-navigation.md) |
| My Tools | Groups | search, new/edit/delete group, open chip | 9 built-in chip choices; ≥1 tool | `pages/my_tools.py:5-170`; `app.py:111-125` | UI | [done](workspace-and-navigation.md) |
| Challenge | Tracker | create/edit/delete, Start/Pause, Save | total ≥1; solved 0..total | `pages/challenge.py`; `Tools/workspace_store.py:46-124` | UI | [done](workspace-and-navigation.md) |
| Solve History | Viewer | filter, refresh, select, page, export selected/all, clear | All/Data Hashing/File Inspection/Pipeline; 100/page | `pages/solve_history.py`; `Tools/solve_history.py` | UI | [done](persistence-and-history.md) |
| Packaged CLI | launcher | `--check-tools`, `--smoke-test`, `--install-shortcut`, `--unit-regex-worker`, `-h/--help` | unknown arg → 2 | `packaging/launcher.py:18-52` | internal | [done](external-tools.md) |
| Build/release | scripts | PyInstaller build, verify release | output root/version/no-archive | `packaging/build.py`; `packaging/verify_release.py` | internal | [done](external-tools.md) |

## รายการที่มีชื่อแต่สถานะจำกัด

| รายการ | สถานะจากโค้ด |
|---|---|
| `show_startup_popup()` / `check_pipeline_status()` | มี implementation แต่ constructor ระบุว่าตัด popup บังคับออกและไม่มี call path ปกติ (`pages/pipeline.py:225-227,1891-1951`) |
| `PipelinePage.write_temp_file()` | helper มีอยู่แต่ flow ปัจจุบันใช้ `Tools/artifact_bridge.py`; ไม่พบ caller (`pages/pipeline.py:550-555`) |
| `PipelineEngine.run_text_tool()` / `run_file_tool()` | public helpers มี tests/เรียกได้จากโค้ด แต่ GUI ใช้ `_run_command()` ผ่าน command ที่ build แล้ว (`pages/pipeline.py:1656-1659`) |
| SHAKE128/SHAKE256 | backend รองรับ แต่ `hash_algos` UI ไม่ใส่ (`Hashing/hash_utils.py:19-31`; `pages/data_hash.py:151-157`) |
| helper encode/decode ใน `Tools/extra_tools.py:481-510` | ซ้ำกับ codec engine และไม่พบ UI caller ปัจจุบัน |
| `desktop_install.py` | เข้าถึงผ่าน packaged `--install-shortcut` เท่านั้น ไม่ใช่ source `app.py` |

## จุดผิดปกติที่บันทึก ไม่แก้

1. **BUG/RISK — Bitwise Save Raw ไม่ใช่ raw transformed bytes.** `bitwise_mask()` คืน report string ที่มีกรอบ/HEX/ข้อความ แล้ว `_compute_snapshot()` encode report เป็น UTF-8 (`pages/data_hash.py:496-501`) ดังนั้น Save Raw ใน Bitwise บันทึกรายงาน ไม่ใช่ bytes ผล XOR/OR/AND โดยตรง
2. **BUG/RISK — Auto Detect มี false positive ตามลำดับ candidate.** URL Decode/HTML Entity/Reverse ถูกลองหลัง base encodings และ fallback แรกที่ printable ชนะถ้าไม่มี flag (`Decode/base_decoder.py:43-94`); คำว่า detect จึงเป็น heuristic
3. **BUG/RISK — steghide wrapper ไม่มี subcommand.** config สร้าง `steghide <file>` ซึ่งโดยทั่วไปเป็น help/error มากกว่า extract; ผู้ใช้ต้องเติม manual args/subcommand และอาจต้องจัดตำแหน่ง input (`Pipeline/custom_tools.json` รายการ `steghide`)
4. **BUG/RISK — `foremost -i` อาจซ้ำ input.** preset `-i` เป็น option ขณะ tool ใช้ positional input โดย default ถ้ากรอก option แล้ว engine ยังต่อ file path อีกครั้ง
5. **BUG/RISK — App Portal “Terminal” description บอก root shell แต่ command คือ `x-terminal-emulator`; ไม่มี `sudo` หรือ privilege escalation (`pages/app_portal.py:38`)
6. **RISK — App Portal/Nmap/Hashcat ใช้ `eval "$cmd"`.** เป็น command shell อิสระตามเจตนา launcher ไม่ใช่ parser แบบ argument-list; input ผู้ใช้มีอำนาจของ account ที่รัน UNIT
7. **RISK — Gemini SAVE เขียนทับ path.** มี ALLOW/DENY แต่เมื่อ allow ใช้ `open(..., "w")` (`pages/gemini.py:684-690`)
8. **RISK — Custom regex อยู่ใน memory เท่านั้น.** Add ใน popup อัปเดต dict runtime ไม่ persist ลง config (`pages/file_inspection.py:255-274`)

## ผลเทียบกลับกับ source ก่อนส่งมอบ

| ขอบเขตที่นับ | พบใน source/config | มีใน inventory/เอกสาร | ผล |
|---|---:|---:|---|
| หน้า sidebar | 8 | 8 | ครบ |
| หน้าต่างเสริมที่มี flow แยก (Solve History, System Check) | 2 | 2 | ครบ |
| Data Hashing dropdown entries | 52 = 17 Encode + 19 Decode + 12 Hash + 4 Bitwise | 52 | ครบ |
| Hash backend-only | 2 SHAKE variants | 2 | ครบและติดป้าย backend |
| File Inspection operations / runtime regex presets | 6 / 7 | 6 / 7 | ครบ |
| Pipeline categories / tools / preset option objects | 10 / 36 / 20 | 10 / 36 / 20 | ครบ |
| Pipeline templates / run modes | 5 / 2 | 5 / 2 | ครบ |
| App Portal defaults | 8 | 8 | ครบ |
| My Tools built-in destinations | 9 | 9 | ครบ |
| Gemini model strings / action-tag families | 4 / 2 (`EXEC`, `SAVE`) | 4 / 2 | ครบ; availability ยัง conditional |
| Packaged action flags / help entry | 4 / 1 | 4 / 1 | ครบ |

การนับ Data Hashing มาจาก AST ของ assignment จริงใน `pages/data_hash.py`; การนับ Pipeline มาจาก parse `Pipeline/custom_tools.json` โดยตรง ไม่ได้นับจากชื่อที่คัดลอกลงเอกสาร. ตัวตรวจพบชื่อ Pipeline tools ทั้ง 36 ชื่อใน [external-tools.md](external-tools.md), และตรวจ relative links ของเอกสารแล้วไม่พบ target ที่หายไป (ข้อความ regex รูป `[EXEC](.*?)` ไม่ใช่ Markdown link).
