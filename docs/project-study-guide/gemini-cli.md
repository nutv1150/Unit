# Gemini CLI integration และ ALLOW/DENY

หากต้องเตรียมเครื่องใหม่หรือ VM ก่อนอ่าน flow ภายในหน้านี้ ให้ทำตาม [คู่มือติดตั้ง Gemini CLI บน VM ใหม่](gemini-cli-fresh-vm.md)

## ขอบเขต

หน้านี้เป็น wrapperของ executable `gemini` ไม่ใช่ REST API (`pages/gemini.py`). งานตรวจนี้ไม่เชื่อม accountหรือส่งข้อมูลจริงออก. Model stringsเป็นค่าที่ sourceแสดง ไม่ใช่การรับรองว่า Gemini CLI/account ณ เวลาอ่านรองรับ:

1. `gemini-3.1-flash-lite` (default)
2. `gemini-2.5-flash`
3. `gemini-3.5-flash`
4. `gemini-2.5-pro`

## Controls

| UI | code/default | ผล |
|---|---|---|
| API_KEY | `api_entry`; ว่าง | ถ้ามี ใส่ทั้ง `GEMINI_API_KEY` และ `GOOGLE_API_KEY` ใน child env;ไม่ persistเอง |
| eye/lock | `toggle_api_visibility()` | เปลี่ยน masking UIเท่านั้น |
| CONNECT_CLI | `init_api()` | which→version→probe model/auth |
| model dropdown | `model_name`; รายการแรก | requestถัดไปใช้ modelใหม่;ไม่ reconnectบังคับ |
| input/Enter/EXECUTE | `send_message()` | requestเมื่อ connected/not busy |
| Browse | append quoted path | แค่ใส่ pathใน text; process_requestค่อยหา file |
| STOP | `request_stop()` | deny dialog, kill process group/process, set cancel flag |
| View Full Response | capture path | เปิดเมื่อ stdout/stderrเกิน preview |
| View Full Command Output | report path | outputเต็มจาก approved EXEC ล่าสุด |
| right-click chat | selected text | ส่งเฉพาะ selectionไป Data Hashingและ processทันที |

## Connection flow

1. `shutil.which('gemini')`; ไม่พบแสดง PATHและคำแนะนำ install
2. API keyช่องว่าง →ใช้ CLI authเดิม; มีค่า→child envสองชื่อ
3. run `['gemini','--version']`, stdin DEVNULL, cwd=`~`, timeout 20 s
4. run `['gemini','-m',MODEL,'-p','hi']`, timeout 60 s — **เป็น requestจริง** จึงอาจใช้ network/quota
5. parse textหา unauthenticated/trusted directory; nonzero fail; success disable API fieldและ set ready (`pages/gemini.py:356-446`)

`GEMINI_CLI_TRUST_WORKSPACE=true` ถูกเพิ่ม env แต่ codeยังมี handlingกรณี CLIไม่ยอม trust. Packaged Linuxล้าง bundled `LD_LIBRARY_PATH`ก่อนเรียก external CLI

## Prompt และข้อมูลที่ส่งออก

`send_message()` strip input, แสดงใน chat, clear field, spawn worker (`468-487`). `process_request()`:

1. split promptด้วย whitespace; แต่ละ token strip quoteหัวท้าย
2. ถ้า tokenเป็น existing file อ่านไม่เกิน 1 MiB+1
3. >1 MiB หรือ binary/non-UTF-8 → reject ทั้ง request ไม่มีการส่ง/truncateเงียบ
4. append file pathและเนื้อหา plain textเข้า prompt; contentรวมต้องไม่เกิน 4 MiB
5. `build_prompt_with_history()` ใส่ system instruction + recent historyสูงสุด 6 tuples + user
6. `call_gemini_cli()`ตรวจ UTF-8 promptรวม ≤4 MiB แล้วส่งผ่าน stdin

คำสั่ง CLI request:

```text
argv = ['gemini','-m',MODEL,'-p','Respond to the request above.']
stdin = complete system/history/user/file-content prompt bytes
cwd = expanded home directory
timeout = 300 seconds
```

ดังนั้นข้อมูลออกนอกเครื่องประกอบด้วยข้อความผู้ใช้, system prompt, historyล่าสุด และเนื้อหาไฟล์ทุก path tokenที่ตรวจพบ. Pathที่มี spaceจาก Browseถูกครอบ quoteแต่ `prompt.split()` จะแยก quoteหลาย token ทำให้ **BUG/RISK:** file pathมี spaceอาจไม่ถูกพบ/แนบ แม้ UIใส่ quotes

## Response/retry

`run_capture()`เก็บ outputลง disk, preview 128 KiB, capรวม 512 MiB. ตรวจ strings:

- authentication error → fail
- daily quota → failพร้อมแนะนำเปลี่ยน model
- model not found/unavailable → fail
- 503/UNAVAILABLE/high demand → retryสูงสุด 3 ครั้ง, wait 3×attempt seconds
- nonzero → failด้วย stderr

หาก full responseเกิน preview `_full_response_path`มีค่า; UIต่อ warningและ **ไม่ parse EXEC/SAVE** เพื่อไม่กระทำจาก responseบางส่วน (`490-574,609-611`). Historyใน memoryเก็บ user/modelและตัดเหลือ 6 tuples ไม่ persistข้ามเปิดแอป. Chat widgetแสดง messageสูงสุด 128 KiBและตัดข้อความเก่าเมื่อเกิน 256 KiB (`738-751`)

## `[EXEC]` flow

regex `\[EXEC\](.*?)\[/EXEC\]` ไม่มี DOTALL จึง matchคำสั่งบรรทัดเดียวเป็นหลัก. วนสูงสุด 2 รอบต่อ user request (`617-670`):

```text
model responseมี EXEC
 → dialogแสดง raw command
 → DENY: แทน tagด้วยข้อความ denied แล้วหยุด loop
 → ALLOW: run_capture(raw string, shell=True, timeout=30)
     → stdout/stderr/exit code + full report
     → truncate feedbackบน promptที่ 4000 chars
     → ส่ง feedbackกลับ Gemini
     → modelอาจเสนอ EXECรอบ 2
```

ALLOWให้ system shellตีความ pipe, redirects, expansion, chaining และ command substitutionด้วยสิทธิ์ accountที่รัน UNIT. ไม่มี allowlist, cwd argumentหรือ sandbox. `run_capture` callนี้ไม่ส่ง `_build_env()`/`cwd`, จึงสืบทอด process environment/cwdของ UNIT (ต่างจาก Gemini CLI call). POSIX STOP kill process group; Windows kill processหลัก

Exit code `None`เมื่อ timeout/cancel/output cap; feedbackยังถูกสร้างจาก preview. Full command reportรวม exit codeและ full stdout/stderr; View buttonชี้ reportล่าสุด

## `[SAVE:path]` flow

regex `\[SAVE:(.*?)\](.*?)\[/SAVE\]` ใช้ DOTALL (`672-695`). parseหลัง EXEC loopเมื่อ:

- ไม่เคย execute; หรือ
- executeแล้วและ responseสุดท้ายไม่มี unexecuted EXEC tag

แต่ละ tagแสดง dialog path, byte size UTF-8, preview 200 chars. DENYแทน tagด้วย cancelled. ALLOW:

```python
with open(file_path, "w", encoding="utf-8") as f:
    f.write(clean_content)
```

จึงสร้างหรือ **overwrite** file, strip whitespaceรอบ content, ไม่ทำ atomic write, ไม่สร้าง parent directory, ไม่จำกัด pathให้อยู่ workspace, ไม่ preserve permission. User confirmationเป็น controlหลัก. หากยังมี unexecuted EXECหลังครบ loop Save tagsถูกแทนด้วย suspended message

## ALLOW/DENY และ Stop

Dialogถูกสร้างบน Tk thread; workerรอ `threading.Event`ทีละ0.1 s. ปิดหน้าต่างเท่ากับ Deny. Stop:

- set stop flag
- ถ้ามี confirm dialog set result Falseและปิด
- kill current process best-effort
- update UI cancelled

Raceที่ processจบพอดีอาจทำให้ killไม่มีผลแต่ stop flagยังทำให้ flowไม่ดำเนินต่อ. ปิด UNITเรียก `request_stop()` (`app.py:133-139`)

## Output และ activity

final response stripแล้วแสดง; status buttons reset. Dashboard eventบันทึก toolเป็น model, category Gemini CLI, successถ้า outputไม่เริ่ม `❌`, flag patternsใน displayed output และ response length (`pages/gemini.py:701-736`). Gemini requestsไม่ถูกเก็บใน Solve History SQLite; Dashboard storeอาจมี metadata/flagsแต่ไม่ full prompt

## ตัวอย่างปลอดภัย

- Theory promptไม่มี path: ส่ง system/history/text; system promptสั่งไม่ใช้ tagsถ้าไม่จำเป็น
- Text file `/tmp/sample.txt` <1 MiB: path tokenตรงหนึ่งคำ → contentถูกส่ง; ต้องถือว่าออกนอกเครื่อง
- Modelตอบ `[EXEC]file sample.bin[/EXEC]`: dialogให้ตรวจ. Denyไม่รัน. Allowรัน shell `file sample.bin`, ส่ง previewผลกลับ AI
- Modelตอบ `[SAVE:/tmp/note.txt]hello[/SAVE]`: Allow overwrite `/tmp/note.txt`; Denyไม่เขียน

## Checklist ก่อนใช้

- ตรวจว่าข้อความ/ไฟล์ไม่มี secretหรือหลักฐานที่ห้ามส่ง
- อย่าพึ่งชื่อ modelใน dropdown; เช็ก CLI/accountปัจจุบัน
- อ่าน commandทุกตัวรวม redirects/quotes/`;`/`&&`/substitutionก่อน Allow
- Save: ตรวจ absolute path, existing file, parentและ contentเต็ม
- Responseยาวที่มี View Fullจะไม่ execute/saveอัตโนมัติ—เป็น behaviorเพื่อความปลอดภัย
- “success” บน Dashboardหมายถึง wrapperไม่คืนข้อความขึ้นต้น error ไม่ใช่ยืนยันคำตอบ/ความปลอดภัย
