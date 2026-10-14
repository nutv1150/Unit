# Data Hashing: Encode, Decode, Hash และ Bitwise

## Flow ร่วม

`DataHashPage` สร้างรายการ algorithm และ controls ที่ `pages/data_hash.py:107-389` ทุกการแก้ input, เปลี่ยน mode/algorithm, ROT, custom Hex หรือ key จะเรียก `process_data()` (`553-634`) แล้วเดินทางดังนี้:

```text
UI text/file preview
  → _snapshot_source() เลือก text ที่เห็นหรือ full text ของไฟล์
  → validation/options snapshot
  → _compute_snapshot()
  → encode_data / decode_to_bytes / auto_detect_decode / hash_data / bitwise_*
  → output bytes + display text
  → preview 12,000 chars; full text temp fileเมื่อยาวกว่า
  → History + Dashboard event + Save Raw/View Full
```

input จากช่องข้อความรักษา whitespace ของผู้ใช้ ยกเว้น newline แฝงของ Tk (`end-1c`). Browse อ่านไฟล์เป็น bytes ไม่เกิน 64 MiB แล้วบังคับ UTF-8; binary/non-UTF-8 ถูกปฏิเสธ แม้ตัว decoder บางตัวจะให้ output เป็น binary ได้ (`pages/data_hash.py:672-734`). ตั้งแต่ 16 KiB ทำงานใน daemon worker; job ใหม่ยกเลิก job ที่ยังรอ แต่ job ที่กำลังคำนวณไม่ถูก kill เพียงผลเก่าถูกทิ้งด้วย generation number

output จริงเก็บใน `output_bytes`. หาก decode ได้ UTF-8 ที่ printable ≥90% แสดง text; มิฉะนั้นแสดง hex preview 65,536 bytes แต่ Save Raw ยังเก็บ bytes เต็ม (`Decode/base_decoder.py:195-220`; `pages/data_hash.py:471-484,636-656`). `Find` ค้นแบบไม่สนตัวพิมพ์ใน preview เท่านั้น. Right-click selection ส่งไป Gemini และทำให้หน้าปลายทางส่ง request ทันที

## ตัวเลือก UI ร่วม

| ชื่อ UI | ชื่อโค้ด | ชนิด/ค่าเริ่มต้น | ค่าที่รับ | ผล/ข้อผิดพลาด |
|---|---|---|---|---|
| Decode/Encode/Hash/Bitwise | `self.mode` | enum; Decode | 4 mode | เปลี่ยนรายการและ default: Auto Detect/Base64/sha256/XOR Mask |
| Algorithm | `algo_menu` | enum | ตามตารางด้านล่าง | ประมวลผลทันที |
| ROT n | `rotation` | integer text; 13 | alpha 1..25, ascii 1..93 | `parse_rot_algo()` ปฏิเสธนอกช่วง/ไม่ใช่ integer |
| alphabet | `rot_mode_var` | enum; `alpha (A-Z)` | alpha, ascii (33-126) | alpha เลื่อน A-Z/a-z; ascii เลื่อน code point 33..126 |
| KEY | `key` | text; ว่าง | `0x..`, decimal, hex bytes, UTF-8 text | ถ้าว่างลองหา key ฝัง; ไม่พบเป็น error |
| Hex alphabet | `alphabet` | text; `0123456789ABCDEF` | 16 symbols ไม่ซ้ำและไม่มี whitespace | map symbol ลำดับ 0..F; input ต้องจำนวนคู่ |
| Browse | `current_file_path` | file picker | UTF-8 ≤64 MiB | ไฟล์ใหญ่/invalid UTF-8 ไม่โหลด |
| Save Raw | `output_bytes` | file output | path ใดก็ได้ | binary write; Bitwise caveat ด้านล่าง |
| View Full | `_full_output_path` | temp text | เปิดเมื่อ display >12,000 chars | binary full view เป็น hex text ไม่ใช่ bytes |

## Encode และ Decode ทุกรายการ

ทุก Encode เริ่มด้วย `text.encode()` ซึ่งเท่ากับ UTF-8; ทุก Base/number format จึงทำกับ UTF-8 bytes ไม่ใช่ Unicode code points โดยตรง (`Encode/base_encoder.py:12-66`).

| UI | ประเภท | Encode | Decode/validation | คืนกลับได้เมื่อใด |
|---|---|---|---|---|
| Base64 | encoding | 3 bytes → 4 chars, alphabet RFC 4648 | ตัด whitespace, `validate=True`, padding ต้องถูก | คืน bytes เดิม |
| URL-safe Base64 | encoding | Base64 แต่ `+ /` เป็น `- _` | `altchars=b"-_"`, strict | คืน bytes เดิม |
| Base32 | encoding | 5 bytes → 8 chars A-Z2-7 | ตัด whitespace; Python strict padding/case | คืน bytes เดิม |
| Base45 | encoding | 2 bytes → 3 chars; 1 byte → 2 chars | ห้ามความยาว mod 3 = 1; space เป็น digit | คืน bytes เดิมถ้าค่ากลุ่ม valid |
| Base85 | encoding | Python RFC 1924-style `b85` | ไม่ตัด whitespaceเอง | คืน bytes เดิม |
| Ascii85 | encoding | ไม่มีใน Encode UI | Python `a85decode` | decode-only ใน UI |
| Base16 | encoding | uppercase hex ผ่าน `b16encode` | standard hex; whitespace/colon ยอมรับ | คืน bytes เดิม |
| Hex | encoding | implementation เดียวกับ Base16 | เปิด custom alphabet panel; standard default | คืน bytes เดิมถ้า symbols คู่ |
| Base58 | integer-base encoding | alphabet ตัด `0OIl`; รักษา leading zero bytes ด้วย alphabet[0]=`1` | ตัด whitespace; unknown char error | คืน bytes เดิมรวม leading zero |
| Base62 | integer-base encoding | `0-9A-Za-z`; leading zero เป็น `0` | ตัด whitespace | คืน bytes เดิมรวม leading zero |
| Binary | byte notation | byte ละ 8 bits คั่น space | ทุก token ต้องยาว 8; `int(...,2)` | คืน bytes เดิม |
| Octal | byte notation | byte ละอย่างน้อย 3 octal digits | split whitespace; Python `bytes()` บังคับ 0..255 | คืน bytes เดิม |
| Decimal | byte notation | ค่า 0..255 คั่น space | explicit range 0..255 | คืน bytes เดิม |
| URL Encode/Decode | percent encoding | `urllib.parse.quote(text)`; default `/` ไม่ถูก escape | `unquote_to_bytes` | คืน UTF-8 bytesเมื่อ sequence ถูกต้อง; `%` ที่ไม่สมบูรณ์อาจคงเดิม |
| HTML Entity | escaping | `html.escape`: `& < >` และ quote | `html.unescape` รองรับ named/numeric refs | คืนข้อความทั่วไป; entity normalization อาจเปลี่ยน spelling |
| Unicode Escape | textual escape | Python `unicode_escape` | `codecs.decode(...,"unicode_escape")` แล้ว UTF-8 | เหมาะ Python-style escapes; backslash literalอาจถูกตีความ |
| Reverse | transform | reverse Python characters | bytes input reverse bytes; UI text reverse charactersแล้ว UTF-8 | ใช้ซ้ำสองครั้งคืนเดิม |
| ROT | substitution | forward shift | decode ก็ forward shiftเหมือนกัน | ROT13 คืนด้วยตัวเอง; ROT n ทั่วไปต้องใช้ inverse `26-n`/`94-n` ไม่ใช่เลือก n เดิม |

ตำแหน่ง: รายการ UI `pages/data_hash.py:130-149`; encode implementation `Encode/base_encoder.py:12-113`; decode implementation `Decode/base_decoder.py:96-146,223-319`; ROT `Tools/rot.py:4-38`.

### Base64 แบบ bit ต่อ bit

**GENERAL.** Base64 เป็น encoding ไม่ใช่ encryption: ไม่มี secret key และทุกคนย้อนกลับได้. UTF-8 ของ `Man` คือ hex `4D 61 6E`:

```text
M        a        n
01001101 01100001 01101110            24 bits
010011 010110 000101 101110            แบ่ง 6 bits
19     22     5      46                ดัชนี
T      W      F      u                 Base64 alphabet
```

เหลือ 1 byte จะมี 8 data bits + zero เติมเป็น 12 bits → 2 symbols + `==`; เหลือ 2 bytes → 3 symbols + `=`. Padding บอกความยาวกลุ่มสุดท้าย ไม่ได้เพิ่ม security. UNIT encode ใช้ `base64.b64encode`; decode ลบ whitespaceแล้ว strict รวม padding (`Decode/base_decoder.py:249-256`). **RUN:** `Man → TWFu → b'Man'`.

### Base45

**CODE/GENERAL.** bytes คู่ `[a,b]` สร้าง `x=a×256+b`; แล้ว `c=x mod 45`, `d=floor(x/45) mod 45`, `e=floor(x/2025)` และ output alphabet[c], alphabet[d], alphabet[e]. byteสุดท้ายใช้ c,d. ลำดับ least-significant digit ออกก่อนเป็นข้อแตกต่างสำคัญ (`Encode/base_encoder.py:94-113`, [RFC 9285](https://www.rfc-editor.org/rfc/rfc9285.html)). ไม่มี `=` padding. **RUN:** `Man → 9Z9K2`.

### Base58/Base62

**CODE.** UNIT มอง byte string ทั้งก้อนเป็น unsigned big-endian integer แล้วหารซ้ำด้วยฐาน; ไม่ใช่การแปลงทีละ byte. Leading `00` จะหายจาก integer จึงนับและเติม digit ศูนย์ของ alphabet กลับ (`Encode/base_encoder.py:69-88`). Decode คูณสะสม `num=num×base+index` แล้วคืน leading zeros (`Decode/base_decoder.py:109-121`). ไม่มี checksum จึงไม่ใช่ Bitcoin Base58Check.

### Binary/Octal/Decimal และ Custom Hex

เป็น notation ของ byte ไม่ใช่เลข Unicode: `M` คือ decimal 77, octal 115, binary `01001101`, hex `4D`. Custom Hex alphabet เป็น substitution ของ nibble 0..15: symbol ตัวที่ i แทน hex digit i. ตัวพิมพ์มีความหมายสำหรับ custom alphabet; standard alphabetถูก uppercase. whitespace ถูก strip, standard Hex ยอม colon, จำนวน symbol ต้องคู่ (`Decode/base_decoder.py:16-32,240-267`).

### Auto Detect

`auto_detect_decode()` บังคับ input เป็น UTF-8 แล้วลอง candidate ตามลำดับ Base64, Base32, Base85, Ascii85, Base16, Hex, Base45, Base58, Base62, Binary, Octal, Decimal, URL, HTML, Unicode Escape, Reverse (`Decode/base_decoder.py:38-64`). candidate ต้อง decode เป็น UTF-8 printable ASCII/whitespace และต่างจากต้นฉบับ. ถ้าพบ flag pattern คืนทันที; มิฉะนั้นจำ printable candidate แรก. จากนั้นลอง ROT alpha 1..25 และ ascii 1..93 เฉพาะเพื่อหา flag; ถ้าไม่พบคืน fallback หรือ `Unknown` กับ input เดิม (`70-94`).

ผลจึงเป็น “คำเดา” ไม่ใช่ type proof. สตริงที่บังเอิญ valid Base64 อาจชนะ URL/Reverse. **RUN:** `TWFu` ถูกเลือกเป็น Base64 และได้ `Man`.

## Hash ทุกรายการ

UI ส่ง UTF-8 bytes เข้า constructor จาก Python `hashlib` แล้วแสดง lowercase hex digest (`Hashing/hash_utils.py:3-33`). Hash เป็น one-way digest ไม่มี decrypt; ตรวจผลด้วยคำนวณซ้ำจาก input bytes/encoding เดียวกัน.

| UI | family | block/state ภาพรวม | digest ที่ UNIT คืน | หมายเหตุ |
|---|---|---|---|---|
| md5 | Merkle–Damgård, 32-bit | block 512 bits, 4-word state | 128 bits / 32 hex | collision แตกแล้ว; ใช้ fingerprint/CTF legacy ไม่ใช้ security |
| sha1 | SHA-1 | block 512, 5×32-bit state, 80 rounds | 160 bits / 40 hex | collision แตกแล้ว |
| sha224 | SHA-2 | SHA-256 core, IV ต่าง, truncate | 224 bits / 56 hex | |
| sha256 | SHA-2 | block 512, 8×32-bit, 64 rounds | 256 bits / 64 hex | default UI |
| sha384 | SHA-2 | SHA-512 core, IV ต่าง, truncate | 384 bits / 96 hex | |
| sha512 | SHA-2 | block 1024, 8×64-bit, 80 rounds | 512 bits / 128 hex | |
| sha3_224/256/384/512 | Keccak sponge | state 1600 bits; absorb → permute → squeeze | ตาม suffix | padding/domain separation ต่าง SHA-2 |
| blake2b | BLAKE2 | 64-bit words, 12 rounds | default 64 bytes / 128 hex | UI ไม่เปิด key/salt/person/digest_size |
| blake2s | BLAKE2 | 32-bit words, 10 rounds | default 32 bytes / 64 hex | UI ไม่เปิด parameters |
| shake_128/256 | SHA-3 XOF | sponge outputยาวเลือกได้ | backend `length` bytes → 2×length hex | **backend only**, default API 32 bytes |

SHA-1/SHA-2 preprocessing ตามหลักคือ append bit `1`, zero padding และความยาวเดิมให้เต็ม block; แตก block เป็น words, ขยาย message schedule แล้ว update chaining state ด้วย rotate/shift/boolean/add modulo. SHA-3 ใช้ sponge: XOR message blocks เข้า rate portion ของ 1600-bit state, ทำ Keccak-f permutation, แล้ว squeeze output; SHAKE เลือก output lengthได้. BLAKE2 ผสม state/message/counter/final flag ด้วย G function และ permutation. UNIT ไม่ implement rounds เอง—`hashlib` รับผิดชอบทั้งหมด; แอปเลือก UTF-8 input, algorithm defaults และ hex formatting.

**RUN:** SHA-256 ของ ASCII/UTF-8 `abc` ตรง standard vector `ba7816…15ad`. เปลี่ยน `abc` เป็น `abc\n` จะได้ digest คนละค่า เพราะ whitespace ไม่ถูก strip. อ้างอิง [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final), [FIPS 202](https://csrc.nist.gov/pubs/fips/202/final), [RFC 7693](https://www.rfc-editor.org/info/rfc7693/), [Python hashlib](https://docs.python.org/3/library/hashlib.html).

## Bitwise

### Input parser

ลำดับ parser มีผล (`Tools/extra_tools.py:61-201`):

1. assignment ชื่อ `data|bytes|payload|encoded|ciphertext` ใน PowerShell `@(...)`, Python `[...]`, C `{...}`; ดึงเฉพาะ `0xNN` ใน body เพื่อไม่ปน `$key`
2. escaped hex `\x2c\x26`
3. อย่างน้อย 2 token `0xNN`
4. plain hex หลังลบ space/newline/tab/colon/hyphen/comma; ต้องคู่
5. fallback เป็น raw UTF-8 ของข้อความที่ strip แล้ว

ช่องว่างหัวท้ายจึงหายใน Bitwise ต่างจาก Hash/Encode. Input ว่าง error.

### Key parser

| spelling | การตีความ |
|---|---|
| `0x4A`, `0X4142` | hex integer; odd nibble เติม `0` ด้านหน้า |
| `74` | decimal integer, big-endian bytes ขนาดน้อยสุด |
| `4A4B`, `4A 4B`, `4A:4B`, `4A-4B` | hex byte string |
| อื่น ๆ เช่น `secret` | UTF-8 bytes |

หากช่อง key ว่าง `detect_embedded_key()` หา assignment `key`/`xor_key` ตามลำดับ hex, decimal, quoted ASCII (`Tools/extra_tools.py:203-283`). key bytes ถูก repeat แล้วตัดให้เท่าข้อมูล (`365-372`).

### Operations

ต่อ byte i ด้วย key byte `k[i mod len(k)]`:

- XOR: `r_i = d_i ⊕ k_i`; ทำซ้ำ key เดิมอีกครั้งคืนข้อมูลเดิม จึง Mask/Unmask ใช้ function เดียวกัน
- OR: `r_i = d_i ∨ k_i`; bit ที่ถูกตั้งเป็น 1 แยกไม่ออกว่าเดิมมาจาก data หรือ key จึงย้อนกลับทั่วไปไม่ได้
- AND: `r_i = d_i ∧ k_i`; bit ที่ key เป็น 0 ถูกลบทิ้ง จึงย้อนกลับทั่วไปไม่ได้

output formatter แสดง HEX, UTF-8 ด้วย replacement character, Printable/Binary และ flag hint (`393-431`). **RUN:** `41 42 43 XOR 0x20 → 61 62 63 → abc`.

**BUG/RISK:** `output_bytes` ใน Bitwise คือ UTF-8 ของ report ที่จัดรูปแบบ ไม่ใช่ `result` bytes (`pages/data_hash.py:496-501`). “SAVE RAW” จึงไม่ควรใช้เป็น ciphertext/plaintext raw สำหรับ Bitwise; คัดค่า HEX แล้วแปลงต่อแทนจนกว่าโค้ดจะถูกแก้

## การใช้ในโจทย์และการตรวจผล

- เห็น `=` ท้ายและ alphabet A-Za-z0-9+/ → ลอง Base64 แต่ตรวจด้วย decode แล้ว re-encode เทียบ canonical form ไม่ใช่ดูว่าไม่ error
- เห็นเฉพาะ hex และความยาวคู่ → Hex; ระวังข้อความธรรมดาอย่าง `deadbeef` ก็ valid hex
- ตัวเลข 0..255 คั่นช่อง → Decimal bytes; ตรวจ UTF-8/known magic หลัง decode
- ROT ใช้เมื่อ frequency/word shape ยังคล้ายภาษา; ROT13 self-inverse เฉพาะ alphabet mode
- Hash ใช้เทียบ equality/integrity ไม่ใช้ “ถอด hash”; MD5/SHA-1 ไม่เหมาะ collision resistance
- XOR single/repeating key มักพบจาก code snippet; ตรวจด้วย XOR ซ้ำและ known plaintext/flag structure
- URL → HTML Entity → Base64 เป็น chain ที่พบได้; ต้องย้อนลำดับตรงข้ามกับการ encode

ข้อผิดพลาดบ่อย: สับสน text `41` กับ byte `0x41`; ลืม UTF-8 multi-byte; ตัด/เพิ่ม newline; ใช้ wrong Base85 variant; เรียก Auto Detect เป็น proof; คิด OR/AND ย้อนกลับได้; ใช้ Save Raw ของ Bitwise เป็น bytes จริง

