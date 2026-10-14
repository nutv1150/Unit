# File Inspection

## ภาพรวมและ flow

หน้า `FileInspectionPage` รับหลายไฟล์ผ่าน Browse หรือ TkDND (`pages/file_inspection.py:343-356,560-587`) กรองเฉพาะ `os.path.isfile`, แสดงขนาด/นามสกุล และ MD5. การเลือกไฟล์ใหม่หรือเปลี่ยน tool เริ่ม analysis ทันที; ปุ่ม `[ EXECUTE ]` รันซ้ำ. งานอยู่ใน daemon thread และส่ง UI callback ผ่าน queue เพื่อไม่แตะ Tk จาก worker (`294-301,541-554,656-741`).

```text
Browse/Drop → validate paths → per-file ResultBox + metadata MD5
 → validate Max/regex → history Running ต่อไฟล์
 → operation implementation หรือ subprocess argument list
 → full output text ใน temp directory + preview ≤128 KiB
 → history finish + Dashboard event → View/Save/forward selection
```

analysis ใหม่เพิ่ม generation; งานเก่าถือว่าถูก supersede. External command poll cancellation ผ่าน generation. Temp full outputs มี owner ร่วมกับ viewer/result panels และถูก cleanup เมื่อไม่มี reference

## Controls และผลกระทบ

| UI | ค่าเริ่มต้น/ค่าที่รับ | ผล |
|---|---|---|
| Tool menu | 6 operations; เริ่มที่รายการแรกของ widget | เปลี่ยนแล้วรันทันทีเมื่อมีไฟล์ |
| `[ EXECUTE ]` | button | validate แล้วรันทุก selected file |
| `CFG_REGEX` | เปิดได้เฉพาะ Strings | เลือก built-in/custom regex; confirm แล้วรันใหม่ |
| `[X]` | Strings only | clear regex แล้วรันใหม่ |
| Max | `3000`; integer 1..100000 | จำนวนบรรทัด Strings สูงสุดที่แสดงต่อไฟล์; ไม่จำกัด full extraction |
| Search in output / Find | keyword | literal, case-insensitive, เฉพาะ visible preview ทุก result box |
| All Results / file | navigation | filter panels ไม่เปลี่ยนข้อมูล |
| Clear All | — | ล้าง textbox previews; ไม่ลบ source file |
| View Full Output | มี full path | เปิด paged text viewer |
| Save Full Output | destination | copy full output แบบ async; attach path เข้า History |
| context menu | selection | ส่ง selection ไป Data Hashing หรือ Gemini; ปลายทางประมวลผลทันที |

ตำแหน่ง UI `pages/file_inspection.py:358-455`; validation `656-706`; ResultBox `48-181`.

## Operations ทั้ง 6

### 1. `'file' Command`

- ประเภท: wrapper ของ Unix `file`
- input: existing file path ต่อไฟล์
- argument list จริง: `['file', path]` ไม่ผ่าน shell (`run_file_command`, `865-866`)
- stdin: ไม่มี; stdout/stderr capture ลง disk; timeout 5 s
- exit 0: log stdout และ stderr ถ้ามี; nonzero: log `EXIT n`, stdout/stderr; missing executable กลายเป็น analysis error
- output: คำอธิบายชนิดไฟล์จากฐาน magic ของโปรแกรมภายนอก ไม่ใช่นามสกุล
- ตรวจผล: เทียบ magic/header ด้วย Header Check หรือ `file` อีก implementation/version; ชนิดที่รายงานไม่รับรองว่า content ปลอดภัย

### 2. Header Check

- ประเภท: signature analysis ใน Python
- อ่าน 16 bytes แรก แล้วเทียบ prefix: `4D5A` Windows EXE, `7F454C46` ELF, `504B0304` ZIP/Office, `FFD8FF` JPEG, `89504E47` PNG, `25504446` PDF (`771-789`)
- ไม่ match → `puremagic.from_file(path)`; ยังไม่พบ → ถ้า 16 bytes decode UTF-8 ได้เรียก Plain Text ไม่เช่นนั้น Unknown Binary
- ข้อจำกัด: signature สั้นอาจเกิด false positive; ZIP ไม่แยก DOCX/APK/JAR; text decision ดูเพียง 16 bytes
- ตรวจผล: parse format structure เพิ่ม ไม่ใช่เชื่อ magic อย่างเดียว

### 3. Executable Check

- อ่าน 4 bytes (`761-769`)
- เท่ากับ `7f 45 4c 46` → Linux ELF; สอง byteแรก `MZ` → Windows EXE; อื่น → Non-Executable
- ไม่ตรวจ execute permission, architecture, PE header offset, script shebang หรือความสมบูรณ์ จึงเป็น classifier เบื้องต้น

### 4. Strings

`Tools/inspection_stream.py:23-73` ทำสอง pass แบบ memory-bounded (chunk 64 KiB):

1. ลอง incremental UTF-8 strict ทั้งไฟล์; ถ้าถูกต้องคัดลอกข้อความทั้งหมดตาม chunk
2. ถ้า invalid UTF-8 เปิด output ใหม่แล้ว scan printable ASCII `0x20..0x7E`; เขียน run ยาวอย่างน้อย 4 bytes โดย prefix สองช่อง

ไม่ใช้ external `strings`. Full extraction ลง temp text. GUI อ่าน 128 KiB แรก, split lines และแสดงไม่เกิน Max. Regex และ `find_flags()` ทำกับ `display` เท่านั้น (`pages/file_inspection.py:831-862`) ดังนั้นข้อความ “FOUND n MATCHES” และ flags เป็นจำนวนใน preview ไม่ใช่ทั้งไฟล์. บรรทัดยาวยังอยู่ครบใน full output แม้ preview ถูกตัด

ตรวจผล: เปิด/บันทึก Full Output และค้นทั้งไฟล์ด้วยเครื่องมือที่ตั้งใจ scan ครบ; อย่าใช้ count ใน GUI เป็น count ทั้ง source

### 5. zsteg Analysis

- ตรวจ extension แบบ case-insensitive ต้อง `.png` หรือ `.bmp`; ไม่ดู magic (`822-826`)
- argument list: `['zsteg', path]`; timeout 30 s; no shell
- output เป็นการ scan channels/bit planes ของ zsteg; UNIT ไม่ parse ความน่าเชื่อถือ
- extensionผิด log error แต่ function return โดยไม่ raise; `_worker_context.failed` ถูกตั้งจาก error tag ผ่าน `safe_log`

### 6. Exiftool

- argument list: `['exiftool', path]`; timeout 10 s (`828-829`)
- แสดง metadata stdout; stderr ก็แสดง; UNIT ไม่ normalize fields หรือแก้ source
- metadata ขาดไม่ได้แปลว่าไม่มีข้อมูลซ่อน และ metadata อาจปลอมได้

## External runner

`_external_analysis(command,path,timeout)` เรียก `run_capture()` (`802-820`). `run_capture`:

- `Popen(argument_list, stdin=tempfile, stdout=file, stderr=file)`; `external_environment()` คืน PATH ปกติและถ้า frozen Linux เอา bundled `LD_LIBRARY_PATH` ออก
- working directory ไม่ถูกกำหนด จึงสืบทอด process cwd
- POSIX สร้าง session ใหม่และ kill process group เมื่อ cancel/timeout/เกิน output; Windows kill process หลัก
- safety cap stdout+stderr 512 MiB; preview streamละ 128 KiB
- timeoutตามรายการข้างบน; cancelled/timeout/oversize ทำ `returncode=None` และเพิ่มเหตุผลใน stderr

## Regex presets และ parser

runtime database จริง (`pages/file_inspection.py:309-318`) มี 7 รายการ:

| ชื่อ | pattern/ความหมาย | สิ่งที่ไม่รับรอง |
|---|---|---|
| THAI_MOBILE_NUM | `0` หรือ `+66`, prefix 6/8/9 และรูปแบบหลัก | ไม่ validate หมายเลขจริงทุกกฎ |
| EMAIL_ADDR | local/domain/TLD pattern | ไม่ใช่ RFC email parser ครบ |
| BASE64_STRING | กลุ่ม Base64 ยาวขั้นต่ำประมาณ 20 chars พร้อม boundary | ไม่ decode/validate semantics |
| IPv4_ADDR | 4 กลุ่ม 1..3 digits | ยอม 999.999.999.999 |
| URL_LINK | HTTP(S) แบบจำกัด chars | อาจตัด query/path; ไม่ parse URL เต็ม |
| MD5_HASH | hex 32 ตัว | ไม่ยืนยันว่าเป็น MD5 จริง; match substringถ้าไม่มี boundary |
| UNIVERSAL_CTF_FLAG | known/generic CTF prefixes + `{1..256 chars}` | pattern detection ไม่ submit/verify flag |

หมายเหตุ: `regex_previews` มี key ตัวอย่างบางแบบ (`FLAG\{.*?\}`, multi-CTF) ที่ไม่อยู่ใน `smart_db`; จึงไม่ปรากฏ radio เว้นแต่ database ถูกเปลี่ยน. Base64 preview key ยังไม่ตรงกับ runtime patternตัวเต็ม. เอกสารนับเฉพาะ 7 runtime choices

Custom Regex fields: optional name/description และ required pattern; `re.compile()` ผ่านจึงเพิ่ม radio ใน dict ของหน้า **เฉพาะ session** ไม่มี persistence (`185-290`). Exception ใน Add ถูกกลืน ทำให้ invalid patternไม่แสดง error. Clear ใน popupเพียง deselect; Confirm ส่ง patternว่างกลับหน้า

การ match จริงแยก process (`Tools/regex_runner.py`): request JSON ผ่าน stdin → Python executable ปัจจุบัน `-I Tools/regex_runner.py` หรือ frozen executable `--unit-regex-worker` → `re.finditer(..., re.IGNORECASE)` → JSON spans. timeout 2 s, สูงสุด 10,000 matches; timeout/nonzero แปลงเป็น ValueError. สิ่งนี้จำกัด catastrophic backtracking ไม่ให้ GUI process ค้างถาวร แต่ worker ยังรับ preview textทั้งก้อนสูงสุด 128 KiB

## Metadata และ MD5

ไฟล์เดียว: `os.path.getsize`, extension จาก path และ MD5 streaming chunk 4096 ใน background (`594-622`). หลายไฟล์: รวมขนาด, ไม่คำนวณ MD5รวม. MD5 card เป็น checksum convenience; collision resistance ไม่ปลอดภัยและไม่ได้ hash metadata/path

## ตัวอย่างการใช้

1. ใช้ไฟล์จำลอง PNG: Header Check ควรพบ PNG จาก `89504E47`; `'file' Command` ควรรายงาน image; Exiftoolดู metadata; zsteg scan bit planes. ผลทั้งสี่ตอบคนละคำถาม
2. ไฟล์ UTF-8 log: Strings คัดลอกทั้งไฟล์; เลือก EMAIL regex; count แสดงเฉพาะ preview. View Full เพื่อยืนยันบรรทัดหลัง 128 KiB
3. executable ปลอมที่เริ่ม `MZ` แต่ไม่มี PE structure: Executable Check ยังบอก Windows EXE; ใช้ `file`, PE parser หรือ disassemblerตรวจต่อ
4. invalid regex `(a+)+$` บน inputซับซ้อนอาจ timeoutใน 2 s; UI ควรรายงานให้ลด pattern

เบาะแสที่มักทำให้เข้าใจผิด: extension `.png` ไม่รับรอง magic; magic ไม่รับรอง structure; printable string ไม่รับรองว่าใช้จริง; flag-like stringไม่รับรองคำตอบ; EXIF timestampแก้ได้; MD5เท่ากันไม่ควรใช้เป็นหลักฐาน adversarial

