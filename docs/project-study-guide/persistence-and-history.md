# Persistence, Solve History, output viewers และ paths

## Source checkout กับ packaged app

`Tools/app_paths.py` กำหนด:

- sourceปกติ: `data_root()` = repository root
- ถ้า frozen: `$XDG_DATA_HOME/unit` หรือ `~/.local/share/unit`
- ถ้ามี `UNIT_DATA_HOME`: ต้องเป็น absolute pathและชนะค่าอื่น

`initialize_user_data()`ทำเฉพาะ packaged/override: สร้าง rootและ publish defaultsสามไฟล์ (`Pipeline/custom_tools.json`, `Pipeline/saved_pipelines.json`, `custom_tools.json`) เฉพาะเมื่อ targetยังไม่มี ผ่าน temp file + hard link; ไม่ migrate/overwrite user data (`Tools/app_paths.py:14-62`)

| ข้อมูล | writable path | format |
|---|---|---|
| Dashboard | `data/dashboard_state.json` | JSON object schema v1, events ≤2000 |
| Solve History | `data/solve_history.sqlite3` | SQLite WAL, new files chmod 0600 best-effort |
| Pipeline tools | `Pipeline/custom_tools.json` | category object → tool lists |
| Saved pipelines | `Pipeline/saved_pipelines.json` | object `saved_pipelines` |
| App Portal custom | `custom_tools.json` | list |
| My Tools | `config/my_tools_groups.json` | list + unique IDs |
| Challenge | `config/challenges.json` | list + unique IDs |

## Solve History lifecycle

เฉพาะ Data Hashing, File Inspection และ Pipelineใช้ Solve History. `history_hooks.begin()`เรียก store, เพิ่ม event IDเข้า `root.history_active`; `finish()` updateและเอาออก; failureของ storeถูกเก็บใน `history_error`แทนทำ operationหลักพัง (`Tools/history_hooks.py`).

SQLite schema (`Tools/solve_history.py:250-280`):

| field | ความหมาย |
|---|---|
| `id` | UUID primary key |
| `seq` | monotonic visible order |
| `category` | Data Hashing/File Inspection/Pipeline |
| `tool` | operation name |
| `status` | Running/Success/Failed |
| `input`, `options`, `output`, `error` | bounded text |
| `files` | JSON string list |
| `group_id` | batch/pipeline run relation |
| `parent_id` | source operation relation |

`begin()`ใช้ `BEGIN IMMEDIATE`, increment `next_seq` และ insert Running; `finish()` transaction update. ปิด appทำ active IDsเป็น Failed “Application closed…” ก่อน close DB (`app.py:139-143`)

## Bounded serialization และ redaction

- text fieldสูงสุด 16 KiBรวม truncation marker
- bytes: ลอง UTF-8 printable; ไม่ได้จึงเก็บ bounded `hex:` sample ไม่ hexทั้งก้อน
- file listสูงสุด 128 items, itemละ4 KiB, JSONรวม16 KiB
- mapping key/argv flagที่คล้าย pass/password/secret/token/api key/access key/private key/key หรือ `-k/-K/-p` ถูกแทน `[REDACTED]`
- regexยัง mask common `key=value`, JSON-like `key: value`, flag+value

นี่เป็น best-effort: content secretที่ไม่มี label, stdout, flag valueรูปแบบแปลก หรือข้อมูลใน source fileไม่อาจรับประกันว่าปิดบัง (`Tools/solve_history.py:22-201`). Storeไม่เปิด/copy/delete pathใน `files`

## History UI ทุกคำสั่ง

| Control | behavior |
|---|---|
| filter | All/Data Hashing/File Inspection/Pipeline; reset page 0 |
| Refresh | count + summary page; autoทุก 1 s |
| table selection | extended Ctrl/Shift; selection IDsรักษาข้าม page |
| details | โหลด full bounded recordแรกที่เลือก; แสดง source/group/input/options/output/error/files |
| Previous/Next | PAGE_SIZE 100; page index clampตอน refresh |
| Select Page | select visible rows |
| Export Selected | iterate eventsทั้งหมดแล้วกรอง IDs; HTML |
| Export All | current categoryทั้งหมด; HTML |
| Clear History | confirmation; current filter; ไม่ลบ source/output files |

Running recordที่ไม่อยู่ `history_active` แสดง “Unfinished” แต่ database statusยัง Running (`pages/solve_history.py:133-136`). Clearถูก blockถ้ามี active operationใน scopeหรือ exportกำลังทำ. เมื่อ DBว่าง reset visible sequenceเป็น1; UUIDไม่ reuse (`Tools/solve_history.py:469-491`)

## Export HTML

destinationต้อง `.html/.htm`, ต้องไม่ตรง pathใดใน history files และไม่ overwrite SQLite file (ตรวจ magic). ถ้ามากกว่า100 eventsทำ background. `export_html()` escapeทุก field/path, stream one record at a timeเข้า temp, chmod0600, fsyncและ atomic replace (`pages/solve_history.py:168-239`; `Tools/solve_history.py:514-569`).

แม้ redactตอน storeแล้ว ผู้ใช้ควรอ่าน reportก่อนแชร์ เพราะ outputอาจมี secret/flag/path

## Dashboard persistence

`DashboardStore` validate schemaก่อนใช้. Invalid JSON/schema → default stateใน memory + read-only + notice; ไม่ overwrite. Mutations deepcopyก่อน, temp write+fsync+replace, rollback in-memoryเมื่อ write fail (`Tools/dashboard_store.py:59-219`). Event normalize statusเป็น successเฉพาะ stringตรง `success`, อื่นเป็น failed; detailsตัด 500 chars; file path absolute; flags uniqueต่อ event (`352-405`)

Dashboard historyกับ Solve Historyเป็นคนละระบบ:

- Dashboard: lightweight analyticsของหลายหน้า รวม Gemini/App Portal
- Solve History: detailed bounded reproducibility recordsเฉพาะ 3 categories

## Generic JSON stores

`Tools/workspace_store.save_records()`เขียน sibling `.tmp` แล้ว replace แต่ไม่มี fsync (`28-33`). App Portalและ Pipeline configมี temp+fsync+replaceของตัวเอง. ทุก loaderเมื่อ invalidพยายามเข้าสู่ read-only/แสดง error ไม่ “ซ่อม”ด้วยการ overwrite

## Full output viewers

`Tools/text_view.py` เปิด text fileแบบ paged/chunk viewerและ Save copy async. Data Hashing large result, File Inspection full outputs, Pipeline large stdout/stderr และ Gemini capturesต่างเก็บ temp fileแล้วเปิดผ่าน helperนี้. Temp file lifetimeผูก owner/reference; userต้อง Saveหากต้องการถาวร

ข้อแตกต่าง:

- Data Hashing Save Rawเขียน `output_bytes`; View Fullเป็น text/hex rendering
- File Inspection Save Fullเป็น extraction/tool textทั้งหมด
- Pipeline Save Outputใช้ stdout bytesหรือ Path captureเต็ม
- Gemini View Full Response/Command Outputเป็น capture/report ไม่ใช่ chat history persistence

## External output discovery/preservation

Pipeline temp artifactsและ capture filesถูก cleanupที่ Clear/next run/object cleanup แต่ไฟล์ที่ external commandสร้าง เช่น extract/output destinationไม่ถูกลบ. `changed_files()` exclude input pathแต่ไม่รับรอง provenance; processอื่นอาจแก้ fileพร้อมกัน. History attachเพียง path reference

## ความปลอดภัยและ recovery

- ห้ามถือ Dashboard/Historyว่าเป็น evidence copy; เก็บเพียง bounded snapshots/paths
- sourceถูกลบภายหลัง Recent Filesแสดง MISSING และ History pathยังอยู่
- invalid stateควร backup/ซ่อมนอกแอป; appจงใจไม่ overwrite
- abrupt killอาจทิ้ง Running Historyเป็น Unfinished และ Challenge timerยัง running
- atomic replaceลด partial JSONแต่ไม่แทน backup/versioning
- `Clear History`ถาวรสำหรับ DB recordsใน scope แต่ source/output filesกู้ได้ตาม filesystemและไม่ถูกแตะ

