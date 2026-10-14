# OpenSSL ใน UNIT และ AES modes

## สิ่งที่โปรเจกต์ทำจริง

Pipeline config มี nodeชื่อ `openssl enc` เพียงรายการเดียว:

```json
{"name":"openssl enc","command":"openssl","params":["enc"],
 "input_mode":"flag","input_flag":"-in","mode":"file","options":[]}
```

ดังนั้น base argv คือ `['openssl','enc','-in',FILE]`; UI ไม่มี dropdown cipher/mode/key/operation. ผู้ใช้ต้องเพิ่มทุก argumentผ่าน Advanced Options. Arguments แบบ Before Inputอยู่ก่อน `-in FILE`; After Inputอยู่หลัง. Engineไม่ใช้ shell, key/passwordจึงเป็น tokenตรงตามที่กรอก แต่ command previewใช้ shell quoting (`Pipeline/custom_tools.json`; `Pipeline/pipeline_engine.py:159-188`; `pages/pipeline.py:1251-1476`)

syntax ที่ถูกต้องไม่ใช่ `openssl -e -d aes-128-ecb`. `enc` เป็น subcommand, เลือก encrypt **หรือ** decrypt และ cipherใช้ขีดหน้า

## ตัวอย่าง encrypt/decrypt ที่ตรง builder

### Raw key + IV, AES-128-CBC

Encrypt manual Before rows/params:

```text
-aes-128-cbc -e -K 000102030405060708090a0b0c0d0e0f
-iv 101112131415161718191a1b1c1d1e1f
```

manual After:

```text
-out /tmp/cipher.bin
```

argument listจริง:

```text
['openssl','enc','-aes-128-cbc','-e','-K',KEYHEX,'-iv',IVHEX,
 '-in','/tmp/plain.bin','-out','/tmp/cipher.bin']
```

Decryptเปลี่ยน `-e` เป็น `-d`, inputเป็น cipher และ outputเป็น plain:

```text
['openssl','enc','-aes-128-cbc','-d','-K',KEYHEX,'-iv',IVHEX,
 '-in','/tmp/cipher.bin','-out','/tmp/plain.out']
```

ห้ามใส่ `-e` และ `-d` พร้อมกัน. `-e` เป็น default OpenSSLแต่ควรระบุให้เจตนาชัด

### Passphrase + PBKDF2

```text
encrypt argv:
['openssl','enc','-aes-256-cbc','-e','-salt','-pbkdf2','-iter','200000',
 '-md','sha256','-pass','file:/tmp/pass.txt','-in',IN,'-out',OUT]

decrypt argv:
['openssl','enc','-aes-256-cbc','-d','-pbkdf2','-iter','200000',
 '-md','sha256','-pass','file:/tmp/pass.txt','-in',OUT,'-out',PLAIN]
```

decryptต้องใช้ KDF parameters/salt formatเดียวกับ encrypt. `-salt` เป็น defaultตอน encrypt; ระบุไว้เพื่ออ่านง่าย. อย่าใส่ passwordจริงใน manual argsหากไม่จำเป็น เพราะ process listing/historyอาจเห็น แม้ Solve Historyพยายาม redact best-effort; `-pass file:`/`env:` ก็มี trade-offของตัวเอง

### Base64 wrapper

เพิ่ม `-a` หรือ `-base64` เพื่อ Base64 ciphertextตอน encrypt/ถอดก่อน decrypt. `-A` ทำ Base64บรรทัดเดียว. นี่เป็น text encodingชั้นนอก ไม่ใช่ cipher mode

## Options ที่เกี่ยวกับ flowนี้

อ้างอิง [OpenSSL 3.5 `enc`](https://docs.openssl.org/3.5/man1/openssl-enc/). UNITไม่จำกัด options แต่รายการต่อไปนี้คือชุดสำคัญที่สัมพันธ์กับ wrapper:

| Flag | ชนิด/เงื่อนไข | ผล |
|---|---|---|
| `enc` | subcommandบังคับจาก config | symmetric cipher frontend |
| `-aes-128-cbc` ฯลฯ | cipher option ต้องเลือก | algorithm+key size+mode |
| `-e` / `-d` | เลือกหนึ่ง; encrypt default | direction |
| `-in FILE` | UNIT hardcodeจาก input | input file |
| `-out FILE` | optional manual After | output file; UNIT discover pathนี้ |
| `-K HEX` | exact raw key | ต้องมี hex lengthตรง cipher; ถ้าใช้ keyอย่างเดียว modeที่ต้อง IVต้อง `-iv` |
| `-iv HEX` | exact IV/counter initial value | CBC/CFB/OFB/CTRต้องมี; ECBไม่ใช้ |
| `-pass ARG` | passphrase source | ใช้ KDFสร้าง key/IV; ดีกว่า legacy `-k` |
| `-k PASS`, `-kfile FILE` | legacy | superseded by `-pass` |
| `-salt` | default encryptเมื่อ passphrase | random saltสำหรับ KDF; ไม่ใช่ IVและไม่ต้อง secret |
| `-nosalt` | test/ancient compatibility | ทำ password guesses precomputeได้; ไม่แนะนำ |
| `-S HEX` | explicit salt | decryptต้องรู้ค่า; OpenSSL version formatมีผล |
| `-pbkdf2` | KDF selector | PBKDF2; default iterations 10,000ถ้าไม่มี `-iter` |
| `-iter N` | positive count | เปิด PBKDF2และกำหนดรอบ; มากขึ้นช้าทั้ง user/attacker |
| `-md NAME` | default SHA-256 ใน 3.5 | PRF/digestใน password derivation ไม่ใช่ hash ciphertext |
| `-saltlen N` | PBKDF2 only | default 8, max 16ใน docs 3.5; decryptต้องตรง |
| `-nopad` | block modes | ปิด standard block padding; inputต้อง multiple blockสำหรับ ECB/CBC |
| `-a`/`-base64` | optional wrapper | Base64 output/inputตาม direction |
| `-A` | ใช้กับ Base64 | one-line Base64 |
| `-p` | diagnostic | print salt/key/IVและทำงานต่อ; secretรั่ว stdout/historyได้ |
| `-P` | diagnostic | printแล้ว exit ไม่ encrypt/decrypt |
| `-bufsize N[k]` | integer | I/O buffer;ไม่เปลี่ยน cryptographic result |
| `-v`/`-debug` | diagnostic | เพิ่ม output;อาจเปิดเผยรายละเอียด |
| `-z` | buildต้องรองรับ zlib | compressหลัง encrypt / decompressก่อน decryptตาม OpenSSL flow; ไม่ใช่ทุก build |
| provider options | advanced | `-provider`, `-provider-path`, `-propquery`, `-provparam` เปลี่ยน implementation/availability |

ลำดับทั่วไปของ OpenSSL optionsยืดหยุ่น แต่ UNITต้องวาง `-out` หลัง inputหากใช้ “After”; engineรู้ทั้งรูป `-out value` และ `-out=value` สำหรับ discovery. ค่าที่มี spaceต้องเป็น value rowเดียวหรือ quotedใน paramsเพื่อให้ `shlex.split` คืน tokenเดียว

## AES: key schedule และ rounds

**GENERAL.** AES มี block sizeคงที่ 128 bits = 16 bytes ไม่ว่าชื่อ AES-128/192/256; ตัวเลขคือ key size:

| Variant | key | Nk 32-bit words | rounds Nr | expanded round keys |
|---|---:|---:|---:|---:|
| AES-128 | 16 bytes | 4 | 10 | 11 × 16-byte |
| AES-192 | 24 bytes | 6 | 12 | 13 × 16-byte |
| AES-256 | 32 bytes | 8 | 14 | 15 × 16-byte |

key expansionเริ่มจาก key words แล้วสร้าง wordsเพิ่มด้วย `RotWord`, `SubWord` (S-box), round constant XOR และ XORกับ wordก่อนหน้า; AES-256มี SubWordเพิ่มทุกตำแหน่งบางช่วง. Encryption stateเป็น 4×4 bytes column-major:

1. initial AddRoundKey (XOR round key)
2. Nr−1 full rounds: SubBytes → ShiftRows → MixColumnsใน GF(2^8) → AddRoundKey
3. final roundไม่มี MixColumns

Decryptใช้ inverse transforms/round keysย้อนลำดับ. OpenSSL libraryรับผิดชอบ AESทั้งหมด; UNITเพียงประกอบ argvและส่ง file

## Mode เปรียบเทียบ

ให้ `E_K` เป็น AES encryption, `P_i` plaintext block, `C_i` ciphertext, `IV` initial value, `T_i` counter

| Mode | สมการ/flow | IV/nonce | Padding | parallel | integrity / reuse risk |
|---|---|---|---|---|---|
| ECB | `C_i=E_K(P_i)` | ไม่มี | ต้องเต็ม block; enc default pad | ทั้งคู่ | blockซ้ำ→cipherซ้ำ;ไม่ integrity |
| CBC | `C_i=E_K(P_i XOR C_{i-1})`, `C_0=IV` | random/unpredictable 16 bytes | ต้อง padding | decrypt parallel; encrypt chain | IVซ้ำเผย relationของ blockแรก; malleable |
| CFB | encrypt feedbackสร้าง keystream, XOR plaintext | unique/unpredictable IV | ไม่ต้อง | จำกัดโดย feedback | IV reuseเผย XOR; bit errorกระทบบางช่วง;ไม่ integrity |
| OFB | `O_i=E_K(O_{i-1})`; XOR data | unique IV | ไม่ต้อง | keystream precomputeแต่ chain | reuse keystream catastrophic; bit flipตรงตำแหน่ง |
| CTR | `C_i=P_i XOR E_K(T_i)` | nonce/counter pairห้ามซ้ำ | ไม่ต้อง | encrypt/decrypt parallel | reuse key+counterเผย XOR plaintext; malleable |
| GCM | CTR encryption + GHASH tag | nonceห้ามซ้ำ; 96-bit common | ไม่ต้อง | parallel | authenticated encryption; reuse nonce catastrophicและทำลาย tag security |

CFB/OFB/CTR encryption/decryptionต่างกันเพียง XOR direction/feedback; AES primitiveมักใช้ encryptทั้งสองทิศ. ECB/CBCต้องจัด blocksและ padding. GCM outputมี authentication tag; decryptต้อง verifyก่อนยอมรับ plaintext

## สี่ขอบเขตที่ต้องแยก

1. **หลักการทั่วไป:** NIST SP 800-38A กำหนด ECB/CBC/CFB/OFB/CTR; GCMอยู่ SP 800-38D. ดู [NIST block-cipher modes](https://csrc.nist.gov/Projects/block-cipher-techniques/bcm)
2. **OpenSSL library/versionบนเครื่อง:** OpenSSL 3.5.1อาจรองรับ AES-GCMผ่าน EVP/คำสั่งอื่น แม้ `enc`ไม่รองรับ
3. **`openssl enc` บนเครื่องที่ตรวจ:** `openssl enc -list` ณ 2026-10-14 แสดง 144 cipher-name tokensทั้งหมด. ในขอบเขต AES-128/192/256 × `{cbc,cfb,cfb1,cfb8,ctr,ecb,ofb}` มี **21 ชื่อ**; ไม่มี `aes-*-gcm`
4. **UNIT:** เปิดเพียง generic `openssl enc`; ไม่มี whitelist/dropdown mode. ผู้ใช้พิมพ์ cipherเอง. ดังนั้น “โปรเจกต์เปิด AES 21 modes” เป็นข้อความผิด—โปรเจกต์เปิด argumentอิสระหนึ่ง wrapper และผลขึ้นกับ executable

OpenSSL docsระบุชัดว่า `enc` ไม่รองรับ authenticated modesเช่น CCM/GCM เพราะ streaming outputก่อน tag validationและความเสี่ยง nonce management. จึงห้ามเสนอ `openssl enc -aes-256-gcm` เป็นคำสั่งใช้งาน

## Padding และการตรวจว่าถูก

OpenSSL `enc` ใช้ standard block padding (PKCS#7-style): ถ้าขาด n bytesเติม byteค่า n; ถ้าข้อมูลเต็ม blockเติม blockเต็มค่า `0x10`. Decryptตรวจ paddingปลายทาง แต่ paddingผ่านไม่ใช่ authentication—wrong keyอาจบังเอิญผ่านและ CBCถูกดัดแปลงได้. `-nopad` ปิดกลไกและ ECB/CBC inputต้อง multiple 16 bytes

วิธีตรวจที่ดีกว่า:

- decryptแล้วเปรียบเทียบ hash/known magic/format parser
- ถ้าต้องการ integrityใช้ authenticated design (เช่น GCMผ่าน APIที่รองรับ) หรือ Encrypt-then-MAC; ไม่อาศัย exit code/padding
- round-tripด้วย synthetic file: encrypt → decrypt → `cmp`/SHA-256; อย่าทดสอบด้วยหลักฐานผู้ใช้

## Salt, IV, nonce ต่างกันอย่างไร

- **key:** secretที่ AESใช้โดยตรง
- **passphrase:** human secret; ต้องผ่าน KDF
- **salt:** public random valueต่อ password derivation ป้องกัน precomputation/same-password same-key; ไม่แทน IV
- **IV:** mode initial state; ขนาด/ความต้องการตาม mode, ปกติไม่ secret
- **nonce:** number used once; CTR/GCMห้ามซ้ำกับ keyเดียวกัน
- **PBKDF2:** ทำ PRFซ้ำด้วย passphrase+salt+iterationsเพื่อ derive material; iterationสูงทำ brute forceแพงขึ้นแต่ไม่เพิ่ม entropy password

อย่า reuse IV/nonceเพราะ “ไม่ secret”; requirementหลักคือ uniqueness/unpredictabilityตาม mode

## คำถามตรวจตนเองสั้น

1. AES-256 blockใหญ่กว่า AES-128หรือไม่? — ไม่ ทั้งคู่ 128-bit block; key/roundsต่าง
2. `-a` เข้ารหัสเพิ่มหรือไม่? — ไม่ แค่ Base64 wrapper
3. `-K`อย่างเดียวพอสำหรับ CBCหรือไม่? — ไม่ ต้อง `-iv`ด้วย
4. GCMอยู่ใน `openssl enc` 3.5หรือไม่? — ไม่
5. decrypt CBC exit 0พิสูจน์ integrityหรือไม่? — ไม่
6. ทำไม encrypt/decryptต้องคนละ argv? — operation flag, input/output role และ directionต่าง; ห้ามรวม `-e -d`

