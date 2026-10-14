# Pipeline: engine, node, mode และการส่งข้อมูล

## โมเดลข้อมูล

`PipelineEngine` อ่าน `Pipeline/custom_tools.json` เป็น category → list ของ tool. Tool ต้องมี `name`, `command`, `mode` (`text|file`); optional `params`, `options`, `input_mode`, `input_flag`, `description` (`Pipeline/pipeline_engine.py:41-157`). ชื่อ tool ห้ามซ้ำทั้งไฟล์

node ใน canvas เก็บ:

```json
{"name":"grep","params":"","user_description":"","options":[]}
```

`params` เป็น argument text ที่ parse ด้วย `shlex.split`; `options` เป็น definitions ไม่ใช่ค่าที่เลือกตอน run. ค่าที่กรอก/ติ๊กใน step windowไม่ persistกลับ node/saved pipeline. Saved pipeline เก็บ `pipeline_name` และ `steps` fields ข้างบน (`Pipeline/config_store.py:36-51`; `pages/pipeline.py:2198-2282`)

## สร้างและเรียงขั้น

- click tool ซ้าย → `_append_tool_node()`; Auto เพิ่มต่อท้าย, Step จะ Clear ก่อนเพื่อเริ่ม exploration ใหม่ (`pages/pipeline.py:342-382`)
- drag ใช้ x-position เรียง `self.nodes`; y ไม่มีผลต่อ execution (`394-413`)
- arrows วาดตาม list. Run All วน listตามลำดับ (`500-533`)
- Clear ลบ widget/nodes/logs, cleanup temp artifacts/captures และลืม original file; ไม่ลบ output file ที่ external toolสร้าง (`535-548`)

## Auto กับ Step

| พฤติกรรม | Auto | Step |
|---|---|---|
| ปุ่ม | Run All | Run Step |
| การเตรียม node | หลาย node, template หรือ saved pipeline | sidebarเลือกได้ครั้งละหนึ่งจุดเริ่ม |
| ลำดับ | x-position ก่อน run | เลือก next tool หลังแต่ละ success |
| หน้าต่าง | Step i/N; Run แล้ว Next | Step i; Run แล้ว Continue/Finish |
| เมื่อ fail | output None; ไป Next ไม่ได้ | Continue panelไม่แสดงจน success |
| load template/saved | บังคับเปลี่ยน Auto | workspace Step ถูกเก็บไว้ |

แต่ละ mode มี `nodes`, positions, count, run logs, original file และ temp artifacts แยกใน memoryระหว่าง session (`303-339`). สลับไม่ได้ขณะ run/window active

## Step window: input → command → output

### Input routing

File tool มีช่อง path, Browse และ source buttons:

- **PREVIOUS:** ใช้ previous output เมื่อเป็น existing path หรือ binary artifact
- **ORIGINAL:** path แรกที่ Browse หรือ SET ไว้
- **SET:** เลือก original ใหม่และใช้เป็น current input
- **Browse:** เลือก input; browse แรกตั้ง original หากยังไม่มี

`resolve_file_input()` (`Tools/artifact_bridge.py:63-145`) ตัดสิน:

1. bytes/string ที่ strip quotes แล้วเป็น existing file → `existing_path`
2. แปลงเป็น bytes; ถ้า valid UTF-8 และ printable ≥90% → `manual` (ไม่สร้างไฟล์)
3. binary → temp artifact `unit_*.ext`; extensionจาก magic 7z/ZIP/GZIP/PNG/JPEG/PDF/ELF/MZ มิฉะนั้น `.bin`

Text tool ส่ง input ทาง stdin. ถ้า userกรอกช่อง Input ใช้ UTF-8 bytes; ถ้าช่องว่างและ selected outputเป็น `Path` ส่ง Pathให้ `run_capture` เปิด stream; ถ้าช่องว่างและ previous bytes ส่ง bytes (`pages/pipeline.py:1555-1570`). Command Preview ต่อ textไว้เพื่อความอ่านง่ายเท่านั้น ตัว executionไม่เพิ่ม textเป็น argv

### Argument composition

ลำดับจริง (`pages/pipeline.py:1237-1284`):

```text
[command]
+ config params
+ node params
+ manual Before Input
+ preset/custom option flags+values
+ input ตาม input_mode (เฉพาะ file tool)
+ manual After Input
```

Preset option:

- checkbox true → `shlex.split(flag)` เพิ่ม token(s)
- text/file ที่มีค่า → `shlex.split(flag) + [value]`; flag ว่างจึงเพิ่มแค่ value
- default options กับ node custom optionsรวมกัน โดย flagซ้ำใช้รายการแรก

Advanced Options มีสวิตช์ Before/After; แต่ละ rowเป็น No Param (`flag`) หรือ With Param (`flag value`). stringรวมถูก `shlex.split` อีกครั้ง. Toolที่ไม่มี preset optionsเปิด Advanced panelอัตโนมัติ (`1315-1476`)

`input_mode`:

| mode | ตัวอย่าง | attach logic |
|---|---|---|
| positional (default) | `file path` | append path |
| flag | `tshark -r path` | ถ้ามี flagเดิมและไม่มี value แทรก path; valueคนละ path = conflict |
| keyvalue | `dd if=path` | append `flag=path`; existingคนละ path = conflict |

ไฟล์ที่มี spaceปลอดภัยเพราะ executionใช้ list; `shlex.join` ใน preview/shell exampleเท่านั้น (`Pipeline/pipeline_engine.py:121-188`).

### Run, cancel, timeout และผล

Run สร้าง command, validate existing file, เปิด History แล้ว daemon threadเรียก `_run_command(... detailed=True)` (`pages/pipeline.py:1621-1688`). Engine snapshot locationsก่อน run, เรียก `run_capture`, แล้วเมื่อ return code 0 snapshotอีกครั้งเพื่อหาไฟล์ใหม่/เปลี่ยน (`Pipeline/pipeline_engine.py:209-239`).

- timeout 30 s
- stdout+stderrรวมสูงสุด 512 MiB; เกินแล้ว killและถือ fail
- preview streamละ 128 KiB; full streamอยู่ temp files
- Cancel: POSIX kill process group; non-POSIX kill process
- `returncode == 0` เท่านั้นคือ success; cancelled/timeout/oversize returncode `None`
- working directoryสืบทอด process cwd; ไม่มี per-node cwd UI
- environmentสืบทอด OS; packaged Linuxล้าง injected `LD_LIBRARY_PATH`

ผล success:

- stdoutมี → forward stdoutได้
- changed filesมี → radioเลือกไฟล์ได้
- มีทั้งสอง → ต้องเลือกก่อน Next/Continue
- quiet command/no discovered file → Browse result file
- fail → stdout/stderrยังแสดง/เก็บ แต่ไม่ forwardเป็น success

การตรวจ output fileดู cwd, input parent และ output flagsที่รู้จัก: OpenSSL `-out`, unzip `-d`, 7z `-o`, tar `-C`, steghide `-xf`, foremost `-o`, binwalk `-C`, apktool `-o`, jadx `-d`, tshark `-w`, sort `-o`, dd `of=` (`Pipeline/output_files.py:23-53`). scan ≤20,000 paths, ไม่ตาม symlinkและข้าม `.git/.venv/venv/node_modules/__pycache__`; incompleteแจ้ง Browseเอง. นี่เป็น change detection ไม่ใช่ content validation

## Templates

| Template | Nodes ตามลำดับ | หมายเหตุ |
|---|---|---|
| Basic Recon | `file → strings → uniq` | `file` stdoutเป็น text; `strings` เป็น file tool จึงไม่รับ stdout textอัตโนมัติ ผู้ใช้ต้องเลือก original/ไฟล์ |
| Find Flag | `strings → grep` | grep text toolรับ stdoutของ strings |
| Decode Base64 | `strings → grep → base64_decode` | grepต้องกรอก pattern; Base64 decodeรับ stdin |
| Stego Scan | `file → zsteg → strings` | ทั้ง zsteg/stringsเป็น file tools; ต้องเลือก source fileในแต่ละขั้น |
| Forensics Scan | `file → binwalk → strings` | เช่นเดียวกัน; templateไม่กระจาย fileให้ทุก toolอัตโนมัติ |

ดังนั้น template คือ node sequence/prompting aid ไม่ใช่ fully parameterized batch recipe (`pages/pipeline.py:1785-1805`)

## Tool/Pipeline persistence

### Add Tool

UI รับ Tool Name, Linux Command และ mode text/file (`pages/pipeline.py:2301-2344`). `save_custom_tool()` เก็บ `command` เป็น executable stringเดียว ไม่มี params/options/input_mode (`Pipeline/pipeline_engine.py:273-293`). หากกรอก `python3 -c ...` ทั้งก้อนเป็น command จะพยายามหา executableชื่อนั้น; ต้องกรอกเฉพาะ executable แล้วใช้ wizard params/optionsภายหลัง. duplicate nameถูก schema validatorปฏิเสธหลัง append

### Add Pipeline wizard

รับชื่อ pipeline, เลือก registered tool หรือ Custom Tool text, user description และ optional definitionsแบบ No Param/With Param (`pages/pipeline.py:1968-2195`). Custom Toolต้องถูก Add/Register ก่อน Finish; wizardไม่บันทึก executableใหม่เอง. ชื่อ pipelineว่าง/ซ้ำถูกปฏิเสธ. JSON write atomic temp+fsync+replace; invalid existing JSONไม่ถูก overwrite (`Pipeline/config_store.py:8-29`)

### สิ่งที่ save จริง

save `name`, `params`, `user_description`, `options` ต่อ step; ไม่ save canvas position, selected runtime option values, input path, original file, stdout, mode, working directory หรือ environment. Load บังคับ Autoและวาง node xเพิ่มทีละ160 (`pages/pipeline.py:2233-2298`)

## ตัวอย่าง command build ที่รันยืนยัน

argument list (execution จริง) กับ shell display แยกกัน:

```text
file:
  argv = ['file', '/tmp/a b.bin']
  shell display = file '/tmp/a b.bin'

tar_extract + -v + -C /tmp/out:
  argv = ['tar','-x','-v','-C','/tmp/out','-f','/tmp/a.tar']

tshark:
  argv = ['tshark','-r','/tmp/a.pcap']

dd + params bs=1 skip=4 count=8 + after of=/tmp/out.bin:
  argv = ['dd','bs=1','skip=4','count=8','if=/tmp/a.bin','of=/tmp/out.bin']

OpenSSL AES-CBC encrypt:
  argv = ['openssl','enc','-aes-128-cbc','-e','-K',KEYHEX,'-iv',IVHEX,
          '-in','/tmp/plain.bin','-out','/tmp/cipher.bin']
```

## Pipeline ตัวอย่างที่ใช้งานได้จริง

### Text reversible

```text
input "TWFu\n"
→ base64_decode params [-d], stdin bytes
→ stdout b"Man"
→ rot13 params [A-Za-z, N-ZA-Mn-za-m], stdin b"Man"
→ stdout b"Zna"
```

ย้อนกลับ: ROT13อีกครั้งได้ `Man`; Base64 encodeไม่ใช่ nodeเริ่มต้น จึงต้องเพิ่ม custom text toolหรือใช้ Data Hashingเพื่อกลับ `TWFu`. ลำดับสำคัญ: ROTก่อน Base64 decodeจะทำ alphabetเปลี่ยนและ decodeผิด

### File → text → filter

```text
original sample.bin (Path)
→ strings [file tool] → stdout bytes
→ grep, option pattern "flag{" [text tool] → matching lines
→ uniq [text tool] → adjacent duplicates collapsed
```

ต้องเรียง `grep` ก่อน `uniq` ถ้าต้องการลดเฉพาะผล match; `uniq` ลบเฉพาะบรรทัดติดกัน ถ้าต้องการ global duplicatesใช้ `sort → uniq`

### Decrypt → inspect

```text
cipher.bin Path
→ openssl enc + cipher/mode/key/iv/-d/-out → decrypted.bin (selected file)
→ file → stdout type
→ strings โดยเลือก PREVIOUS/ORIGINAL ตามเป้าหมาย
```

ใช้ output file ไม่ใช่ stdoutเพราะ `openssl -out` ปกติ quiet. ขั้น decryptล้มเหลวต้องหยุด; exit 0 ยังไม่รับรอง plaintextถูก โดยเฉพาะ stream mode/no authentication

## ความผิดพลาดที่พบบ่อย

- คิดว่า Run All ไม่ต้อง interaction—จริงทุก nodeเปิด modalและต้อง Run/Next
- ใส่ shell pipe/redirectionใน manual args—engineไม่ใช้ shell จึงเป็น literal argument
- กรอก executableพร้อม spacesใน Add Tool—ไม่ถูก split
- ส่ง stdout textไป file toolแล้วคาดว่าจะสร้าง temp; artifact bridgeสร้างเฉพาะ non-text binary
- ลืมเลือก stdout/fileเมื่อมีหลาย choice
- คิดว่า Clearลบไฟล์ external output—ไม่ลบ
- ใช้ templateโดยไม่กรอก grep/awk/cut parameters
- เอา `returncode 0` เป็นหลักฐาน solveสำเร็จ—แค่ commandสำเร็จ

