# Quick Reference ทุกคำสั่ง

## Pages และคำสั่ง UI

| หน้า | คำสั่งเร็ว | Input → Output/State |
|---|---|---|
| Dashboard | System Check, History, Pin/Open/Remove, Manage Categories, competition selector, Inspect recent | store/events/PATH → summaries/navigation/JSON state |
| Data Hashing | 4 modes, algorithm dropdown, quick chips, Browse, Find, Save Raw, View Full, History, send selection | UTF-8 text/file → text/digest/bytes/report |
| File Inspection | Browse/DnD, 6 tools, Execute, regex config/clear, Max, Find, Clear All, per-file filter, View/Save Full, forward | files → per-file text reports/temp output |
| Pipeline | Auto/Step, add/drag nodes, templates, Run, Clear, Add Tool/Pipeline, options, Preview, Cancel/Next/Continue/Finish, Save/View/Browse result, History | bytes/text/file → subprocess stdout/stderr/files |
| Gemini CLI | API key reveal, Connect, model, Browse, Execute, Stop, Allow/Deny, View Full, forward selection | prompt/files → external AI response/shell/save action |
| App Portal | Search, Launch, Add/Edit/Delete, Browse Installed Apps | launcher config → spawned shell process |
| My Tools | Search, New/Edit/Delete group, chip | group config → deep navigation |
| Challenge | Create, row/edit, Start/Pause, Save/Delete | tracker fields/time → JSON state |
| Solve History | filter/refresh/select/page/details/export/clear | SQLite → UI/HTML/delete records |

## Data Hashing algorithms

| Mode | รายการทั้งหมด | ค่าเพิ่ม |
|---|---|---|
| Encode (17) | Base64, Base32, Base45, Base85, Base16, Base58, Base62, Hex, Binary, Octal, Decimal, URL Encode, URL-safe Base64, HTML Entity, Unicode Escape, Reverse, ROT | ROT n + alpha/ascii |
| Decode (19) | Auto Detect, Base64, Base32, Base45, Base85, Base58, Base62, Ascii85, Base16, Hex, Binary, Octal, Decimal, URL Decode, URL-safe Base64, HTML Entity, Unicode Escape, Reverse, ROT | Custom Hex alphabet; ROT n/mode |
| Hash (12) | md5, sha1, sha224, sha256, sha384, sha512, sha3_224, sha3_256, sha3_384, sha3_512, blake2b, blake2s | no UI params |
| Bitwise (4) | XOR Mask, XOR Unmask, OR Mask, AND Mask | key explicit/embedded |
| backend only | shake_128, shake_256 | `length` bytes, default function arg 32 |

รวมรายการที่เลือกได้ใน UI 52 entries; `Hex` และ `Base16` เป็นคนละชื่อใน dropdown แม้ใช้ implementation เดียวกันบางส่วน ส่วน SHAKE 2 รายการอยู่ใน backend แต่ไม่ปรากฏใน dropdown

## File Inspection

| Tool | engine/argv | limit |
|---|---|---|
| `'file' Command` | `file FILE` | 5 s |
| Header Check | 16-byte signatures → puremagic → UTF-8 fallback | internal |
| Executable Check | 4-byte ELF/MZ classifier | internal |
| Strings | full UTF-8 หรือ printable ASCII runs ≥4 | preview128 KiB, Max lines |
| zsteg Analysis | `zsteg FILE`; `.png/.bmp` | 30 s |
| Exiftool | `exiftool FILE` | 10 s |
| Regex worker | Python isolated/frozen worker, ignorecase | 2 s, 10k matches |

Regex runtime: Thai mobile, email, Base64-looking, IPv4-looking, URL-looking, 32-hex/MD5-looking, universal flag

## Pipeline: tools 36 / preset options 20

| หมวด | Tools | Presets |
|---|---|---|
| File Analysis | xxd; hexdump | xxd `-r/-p`; hexdump `-C` |
| Archive Extraction | 7zip_extract; unzip; tar_extract | `x`, `-y`; tar `-x/-f`, `-v/-C` |
| Steganography | zsteg; zbarimg; steghide; binwalk_extract | binwalk `-e` |
| Forensics | binwalk; foremost; exiftool; tshark; dd | foremost `-i`; tshark `-r`; dd `if=` |
| Cryptography | base64_decode; base32_decode; rot13; hex_decode; gzip_decompress; url_decode; reverse; openssl enc | base `-d/-i`; tr maps; xxd `-r -p`; gzip `-d`; Python `-I -c`; OpenSSL `enc/-in` |
| Pwnable | checksec; file; md5sum | positional |
| Mobile Security | apktool; jadx; dex_strings | apktool `d` |
| Programming | grep; cut; sort; uniq; awk | grep `-n/-v/pattern`; cut `-d/-f`; awk script |
| Reverse Engineering | strings; objdump | `-n`; `-d` |
| Network | tcpdump | `-r` |

`options 20` นับ option objectsใน JSON ไม่รวม hardcoded `params`/input flags/manual Advanced rows

Templates:

- Basic Recon: file → strings → uniq
- Find Flag: strings → grep
- Decode Base64: strings → grep → base64_decode
- Stego Scan: file → zsteg → strings
- Forensics Scan: file → binwalk → strings

Argument order: command → config/node/manual-before/presets → file input → manual-after. Text inputผ่าน stdin

## OpenSSL card

```text
Encrypt: openssl enc -aes-256-cbc -e -salt -pbkdf2 -iter N -pass SOURCE -in IN -out OUT
Decrypt: openssl enc -aes-256-cbc -d       -pbkdf2 -iter N -pass SOURCE -in IN -out OUT
Raw key: add -K KEYHEX and (non-ECB) -iv IVHEX
Base64 wrapper: -a; one line: -A
No padding: -nopad (ECB/CBC input multiple 16 bytes)
```

AES block = 128 bitsทุก key size; AES-128/192/256 = 10/12/14 rounds. `openssl enc` 3.5.1ที่ตรวจมี AES ECB/CBC/CFB/CFB1/CFB8/OFB/CTR รวม 21 namesสำหรับ 3 key sizes; ไม่มี GCM/CCM

## App Portal

| Tool | check → command |
|---|---|
| Wireshark | wireshark → `wireshark` |
| Burp | burpsuite → `burpsuite` |
| Ghidra | ghidra → `ghidra` |
| Nmap | nmap → terminal/bash/read/eval |
| Metasploit | msfconsole → terminal/msfconsole |
| Hashcat | hashcat → terminal/bash/read/eval |
| CyberChef | firefox → Firefox URL |
| Terminal | x-terminal-emulator → same |

ทุก `cmd`ใช้ `shell=True`; spawnไม่ได้พิสูจน์ appทำงาน

## Gemini caps/commands

| รายการ | ค่า |
|---|---:|
| attachment | 1 MiB/file, UTF-8 text |
| prompt+history | 4 MiB |
| history | 6 role/text tuples |
| Gemini timeout | 300 s |
| retries | 3; delay 3×attemptเมื่อ overload |
| EXEC loops | 2 |
| approved shell timeout | 30 s |
| capture total | 512 MiB |
| visible stream preview | 128 KiB |

CLI: `gemini --version`; `gemini -m MODEL -p hi`; request `gemini -m MODEL -p 'Respond...'` + prompt stdin

## Persistence caps

| Store | cap/behavior |
|---|---|
| Dashboard | 2,000 events; details 500 chars |
| Solve History | field 16 KiB; files 128/item4 KiB/total16 KiB; 100/page |
| Pipeline discovery | 20,000 paths |
| Data Hash file | 64 MiB UTF-8 |
| Data Hash preview | 12,000 chars; background ≥16 KiB |
| File Inspection preview | 128 KiB + Max lines |

## สถานะความสำเร็จ

- subprocess: `returncode == 0`
- Dashboard: callerส่ง status `success`เท่านั้น
- History: operation caller finish Success
- flag: regex patternพบเท่านั้น
- App Portal: process spawn/runningไม่ verified
- AI: final outputไม่ขึ้นต้น `❌`

ไม่มีข้อใดเท่ากับ “คำตอบ CTFถูกต้อง”
