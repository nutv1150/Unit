# คำสั่งภายนอกและ internal CLI

## กติกาการอ่านตาราง

`FILE` คือ path ที่ engineแนบตาม input mode; `STDIN` คือ bytes/Path stream. `ARGS` คือ node params + manual before + preset options; `AFTER` คือ manual after. Execution ทุก Pipeline toolใช้ argument listและ `shell=False`; shell spellingเป็นเพียงตัวอย่าง. Timeout 30 s, cwdสืบทอด, environmentผ่าน `external_environment()`, stdout/stderr capture และ exit 0จึง success (`Pipeline/pipeline_engine.py:181-257`).

ตัวเลือกในตารางคือเฉพาะที่ UNIT hardcodeหรือเปิดเป็น preset; Advanced Optionsเปิดให้ผู้ใช้ส่ง argumentอื่นของโปรแกรมได้โดยตรง จึงต้องดู manualของเวอร์ชันติดตั้ง

## File Analysis

| Tool | argv template | Preset options | I/O และข้อสังเกต |
|---|---|---|---|
| `xxd` | `['xxd', ARGS..., FILE, AFTER...]` | `-r` reverse hex dump; `-p` plain continuous hex | file→stdout. `-r` ทำให้ชื่อ “analysis” เปลี่ยนเป็นเขียน binary stdout; เลือก Save Output/ส่งต่อ binaryได้ |
| `hexdump` | `['hexdump', ARGS..., FILE, AFTER...]` | `-C` canonical hex+ASCII | file→stdout text |

## Archive Extraction

| Tool | argv template | Preset | ผล/ความเสี่ยง |
|---|---|---|---|
| `7zip_extract` | `['7z','x',ARGS...,FILE,AFTER...]` | `-y` ตอบ yesและอาจ overwrite | output filesใน cwd/default archive folder; destinationปกติ `-oPATH` ผ่าน manual |
| `unzip` | `['unzip',ARGS...,FILE,AFTER...]` | ไม่มี | output cwd; manual `-d DIR` ถูก file discoveryรู้จัก |
| `tar_extract` | `['tar','-x',ARGS...,'-f',FILE,AFTER...]` | `-v` verbose; `-C VALUE` destination | input flag `-f`; `-C` เป็น type fileใน configแต่ UIใช้ text entry/ไม่บังคับ directory |

Archive extraction อาจสร้าง pathจำนวนมาก/overwriteตาม tool semantics; UNITแค่ตรวจ file changes ไม่ sandbox path traversal

## Steganography

| Tool | argv | Preset | หมายเหตุ |
|---|---|---|---|
| `zsteg` | `zsteg ARGS FILE AFTER` | ไม่มี | PNG/BMPโดยหลัก; Pipelineไม่ตรวจ extensionต่างจาก File Inspection |
| `zbarimg` | `zbarimg ARGS FILE AFTER` | ไม่มี | barcode/QR text stdout |
| `steghide` | `steghide ARGS FILE AFTER` | ไม่มี | **wrapperไม่ใส่ `extract`/`info`**; invocation defaultมีแนวโน้มไม่ทำงานตาม description. เติม subcommandก่อน inputด้วย manual Before เช่น `extract -sf` ยังต้องระวัง engine append FILEอีกครั้ง; configควรกำหนด input flagแต่ไม่ได้กำหนด |
| `binwalk_extract` | `binwalk ARGS FILE AFTER` | `-e` extract embedded | ถ้าไม่ติ๊กจะเป็น analysisธรรมดาแม้ชื่อ `_extract`; output directoryค้นผ่าน manual `-C/--directory` |

## Forensics

| Tool | argv | Preset/input | หมายเหตุ |
|---|---|---|---|
| `binwalk` | `binwalk ARGS FILE AFTER` | positional | signature analysis; ไม่มี auto `-e` |
| `foremost` | `foremost ARGS FILE AFTER` | optional `-i VALUE` | **RISK:** inputจริงยัง append positional จึงอาจได้ inputซ้ำ; ควรทดสอบ command previewและใช้ manualให้ตรง CLI |
| `exiftool` | `exiftool ARGS FILE AFTER` | positional | ไม่มี read-only flagบังคับ; Advanced argsอาจแก้ metadataได้ |
| `tshark` | `tshark ARGS -r FILE AFTER` | input flag `-r` | read capture; output capture `-w FILE` รองรับ discoveryเมื่อเพิ่ม manual |
| `dd` | `dd ARGS if=FILE AFTER` | keyvalue `if=` | ใช้ manual `bs=`, `skip=`, `count=`, `of=`; `of=` หลัง inputเหมาะสำหรับ output file. ผิด pathอาจ overwriteทันที |

## Cryptography/Text codecs

| Tool | argv / stdin | Preset/hardcode | ความหมาย |
|---|---|---|---|
| `base64_decode` | `['base64','-d',ARGS...,AFTER...]`, STDIN | `-i` ignore invalid chars | `-d` hardcode; stdout bytes. `-i` อาจซ่อน inputเสีย |
| `base32_decode` | `['base32','-d',ARGS...,AFTER...]`, STDIN | `-i` ignore garbage | stdout bytes |
| `rot13` | `['tr','A-Za-z','N-ZA-Mn-za-m',ARGS...,AFTER...]`, STDIN | translation sets hardcode | byte-oriented locale-sensitive `tr`; self-inverseสำหรับ ASCII letters |
| `hex_decode` | `['xxd','-r','-p',ARGS...,AFTER...]`, STDIN | reverse + plain hardcode | hex text→binary stdout |
| `gzip_decompress` | `['gzip',ARGS...,FILE,AFTER...]` | checkbox `-d` | ถ้าไม่ติ๊ก default gzip compressและอาจแก้/ลบ inputตาม gzip semantics; ชื่อ toolอาจทำให้เข้าใจผิด |
| `url_decode` | `['python3','-I','-c',SCRIPT,ARGS...,AFTER...]`, STDIN | isolated mode; script `urllib.parse.unquote_to_bytes(sys.stdin.buffer.read())` | รับ bytes จาก stdin และคืน percent-decoded bytes; รันยืนยัน `A%20B` → `A B` บน Python 3.13.3 แล้ว. subprocess ใช้ `python3` ใน PATH ไม่ได้ผูกกับ project venv |
| `reverse` | `['rev',ARGS...,AFTER...]`, STDIN | ไม่มี | reverse แต่ละบรรทัด ไม่ใช่ reverseทั้ง stream; newlineคงแยกบรรทัด |
| `openssl enc` | `['openssl','enc',ARGS...,'-in',FILE,AFTER...]` | ไม่มี; input flag `-in` | ต้องเติม cipher, `-e/-d`, key/password/IV/outputเอง; ดู [openssl.md](openssl.md) |

## Pwnable

| Tool | argv | ความหมาย/ข้อจำกัด |
|---|---|---|
| `checksec` | `checksec ARGS FILE AFTER` | syntaxของ checksecแต่ละ distributionอาจต้อง `--file=FILE`; configใช้ positionalจึงต้องตรวจ `checksec --help` ของเครื่อง |
| `file` | `file ARGS FILE AFTER` | magic/type classifier |
| `md5sum` | `md5sum ARGS FILE AFTER` | stdout digest+filename; MD5ไม่ collision-safe |

## Mobile Security

| Tool | argv | Preset | หมายเหตุ |
|---|---|---|---|
| `apktool` | `apktool ARGS FILE AFTER` | checkbox token `d` | ต้องติ๊ก `d`เพื่อ decode; destination `-o/--output` manualและ discoveryรองรับ |
| `jadx` | `jadx ARGS FILE AFTER` | ไม่มี | decompile APK/DEX; output dir `-d/--output-dir` manual |
| `dex_strings` | `strings ARGS FILE AFTER` | ไม่มี | เหมือน GNU strings ไม่ใช่ DEX semantic parser |

## Programming

| Tool | argv/stdin | Presets | รายละเอียด |
|---|---|---|---|
| `grep` | `grep ARGS STDIN` | `-n` line numbers; `-v` invert; flagว่าง + pattern value | patternเป็น argv ไม่ผ่าน shell; regex syntaxของ grep. ถ้า patternว่าง commandมัก fail |
| `cut` | `cut ARGS STDIN` | `-d VALUE` delimiter; `-f VALUE` field | `-d` โดยทั่วไปต้องหนึ่ง character; `-f` listเช่น `1,3` |
| `sort` | `sort ARGS STDIN` | ไม่มี | localeมีผล; output file `-o` manualถูก discoveryรู้จัก |
| `uniq` | `uniq ARGS STDIN` | ไม่มี | รวมเฉพาะ adjacent duplicate lines; ใช้ `sort`ก่อนถ้าต้องการทั้งชุด |
| `awk` | `awk ARGS STDIN` | flagว่าง + script value | scriptเป็น argv stringเดียว; ไม่ผ่าน shellแต่ awk languageเองมีความสามารถ I/O/systemตาม implementation |

## Reverse Engineering และ Network

| Tool | argv | Preset | หมายเหตุ |
|---|---|---|---|
| `strings` | `strings ARGS FILE AFTER` | `-n VALUE` minimum length | external version; ต่างจาก File Inspection Stringsที่ใช้ UTF-8/ASCII ≥4 |
| `objdump` | `objdump ARGS FILE AFTER` | `-d` disassemble | ไม่เลือก architecture/sectionเป็น preset |
| `tcpdump` | `tcpdump ARGS -r FILE AFTER` | `-r` hardcode | offline capture; advanced filtersวาง Before ก่อน `-r` ซึ่ง syntaxบางแบบต้องหลัง file จึงใช้ Afterได้ |

## File Inspection external commands

แยกจาก Pipelineและไม่มี manual args:

| UI | argument list | timeout | validation |
|---|---|---:|---|
| `'file' Command` | `['file', path]` | 5 s | existing selected file |
| zsteg Analysis | `['zsteg', path]` | 30 s | extension `.png/.bmp` |
| Exiftool | `['exiftool', path]` | 10 s | existing selected file |

## App Portal shell commands

App Portalตรวจ `shutil.which(check)` แล้ว `Popen(cmd, shell=True, stdout/stderr DEVNULL)`. 50 msต่อมาตรวจ `poll()`; processยังอยู่ = “running (not verified)”, exit 0 = launcher exitแต่ appไม่ verified (`pages/app_portal.py:221-253`).

| Card | check | shell command ตามโค้ด |
|---|---|---|
| Wireshark | `wireshark` | `wireshark` |
| Burp Suite | `burpsuite` | `burpsuite` |
| Ghidra | `ghidra` | `ghidra` |
| Nmap | `nmap` | เปิด `x-terminal-emulator -e bash -c ...`, read lineเริ่ม `nmap ` แล้ว `eval "$cmd"`; `exec bash` |
| Metasploit | `msfconsole` | terminal → `msfconsole; exec bash` |
| Hashcat | `hashcat` | terminal → read lineเริ่ม `hashcat ` → `eval "$cmd"`; `exec bash` |
| CyberChef | `firefox` | `firefox https://gchq.github.io/CyberChef/` |
| Terminal | `x-terminal-emulator` | `x-terminal-emulator` |

เพราะ `shell=True`, quoting/expansion/pipe/redirectionทำโดย system shell. Nmap/Hashcatเพิ่ม shellชั้นในและ `eval` inputจาก terminal. Scopeคือสิทธิ์ OSของผู้ใช้ที่เปิด UNIT ไม่ใช่ sandbox/rootโดยอัตโนมัติ. Custom toolรับ `check` และ `cmd` อิสระ; แอปไม่ parse placeholderและไม่จำกัด command language

## Gemini CLI และ AI shell

argument list fixed:

- connection: `['gemini','--version']`, timeout 20 s, stdin DEVNULL
- auth/model probe: `['gemini','-m',MODEL,'-p','hi']`, timeout 60 s
- request: `['gemini','-m',MODEL,'-p','Respond to the request above.']`, promptจริงผ่าน stdin, timeout 300 s
- approved `[EXEC]`: raw stringเข้า `run_capture(..., shell=True)`, timeout 30 s

รายละเอียด environment/retry/ALLOW/DENYอยู่ [gemini-cli.md](gemini-cli.md)

## Packaged executable internal commands

`packaging/launcher.py:18-52` dispatchก่อน import GUI:

| argument | function | I/O/ผล |
|---|---|---|
| `--check-tools` | `Tools.system_check.main()` | stdout FOUND/MISSING; read-only PATH discovery |
| `--smoke-test` | `Tools.package_smoke.main()` | isolated packaged GUI smoke; JSON/result stdout |
| `--install-shortcut` | `Tools.desktop_install.main()` | frozen only; สร้าง `unit-toolkit.desktop` แบบ exclusive, ไม่ sudo |
| `--unit-regex-worker` | `Tools.regex_runner.main()` | JSON stdin → spans JSON stdout; internal |
| `-h`, `--help` | print usage | exit 0 |
| unknown first arg | error stderr | exit 2 |

source `python app.py` ไม่ผ่าน launcher; built executableไม่มี argsจึงสร้าง private workspaceและเปิด GUI

## Build/release commands

`python packaging/build.py [--output-root PATH] [--version VALUE] [--no-archive]` เรียก argument list:

```text
[sys.executable, '-m', 'PyInstaller', '--noconfirm',
 '--distpath', STAGING, '--workpath', WORKPATH, 'packaging/unit.spec']
```

รองรับ Linux x86_64/amd64เท่านั้น, ไม่ overwrite target/archive, versionยอม `[A-Za-z0-9][A-Za-z0-9._+-]{0,63}`, default archive tar.gz (`packaging/build.py:52-105`).

`python packaging/verify_release.py ARCHIVE` แตกใน tempแบบ data filter, ตรวจไม่มี sensitive extensions/state, รัน:

1. `[UNIT,'--check-tools']` timeout 10
2. `[install-user.sh]` timeout 10
3. `['xvfb-run','-a',UNIT,'--smoke-test']` timeout 45

นี่เป็น developer/release flow ไม่ปรากฏ GUI

## ความต่าง OS

- Pipeline command definitionsส่วนใหญ่เป็น Unix CLI; Windowsจะหา commandไม่พบเว้นติดตั้ง/ปรับ config
- `shlex.split` ใช้ POSIX-style parsingโดย default แม้รัน Windows
- run_capture POSIXใช้ session/process-group kill; Windows killเฉพาะ process object
- App Portal defaultsพึ่ง `x-terminal-emulator`, `bash`, Firefox และ `.desktop` picker Linux
- packaged data pathใช้ XDGบน Linux; source checkoutเขียนที่ repoเว้น `UNIT_DATA_HOME`
