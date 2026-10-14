# คำถามทบทวนพร้อมเฉลย

## Data representation

1. `Man` เป็น Base64อย่างไรในระดับ bits?  
   **เฉลย:** UTF-8 `4D 61 6E` → `010011 010110 000101 101110` → indexes 19,22,5,46 → `TWFu`

2. Base64ต่างจาก encryptionอย่างไร?  
   **เฉลย:** ไม่มี secret keyและ decodeได้สาธารณะ; เป็น representation

3. ทำไม Base58 encoderต้องนับ leading zero bytes?  
   **เฉลย:** การแปลง byte string เป็น integer ทำให้ศูนย์ด้านหน้าหายไป จึงต้องเติม `alphabet[0]` กลับเพื่อให้ย้อนคืนได้

4. Base45 สอง bytesใช้สมการใด?  
   **เฉลย:** `x=a*256+b=c+45d+45²e`, output c,d,eตาม alphabet

5. Decode Binaryยอม `101`หรือไม่?  
   **เฉลย:** ไม่ ทุก tokenต้อง 8 bits

6. Hex custom alphabetต้องมีเงื่อนไขอะไร?  
   **เฉลย:** 16 symbolsไม่ซ้ำ, ไม่มี whitespace; inputจำนวน symbolคู่

7. ROT decodeใน UNITทำ inverseอัตโนมัติหรือไม่?  
   **เฉลย:** ไม่ ทั้ง encode/decode forward shift; ROT13 self-inverse แต่ nอื่นใช้ complementary shift

8. Auto Detectพิสูจน์ encodingได้หรือไม่?  
   **เฉลย:** ไม่ เป็น ordered heuristicจาก printable/flag; false positiveได้

## Hash/bitwise

9. Hash “ถอดกลับ”ได้หรือไม่?  
   **เฉลย:** ไม่ใช่ reversible mapping; ตรวจด้วย hash input candidateซ้ำ

10. SHA-256 preprocessingหลักคืออะไร?  
    **เฉลย:** append 1 bit, zeros, length, parse 512-bit blocks, schedule+64 roundsบน state

11. SHA-3ต่าง SHA-2ที่โครงสร้างหลักอย่างไร?  
    **เฉลย:** SHA-3ใช้ Keccak sponge absorb/permute/squeeze ไม่ใช่ SHA-2 compression chain

12. SHAKEปรากฏใน UIหรือไม่?  
    **เฉลย:** ไม่ backendมี `shake_128/256`; functionต้องเลือก output byte length

13. `41 42 43 XOR 20` ได้อะไร?  
    **เฉลย:** `61 62 63` หรือ `abc`

14. OR/ANDย้อนกลับด้วย keyเดิมได้หรือไม่?  
    **เฉลย:** ไม่ทั่วไป เพราะ OR/ANDลบข้อมูลของบาง bits; XORเท่านั้นที่ self-inverse

15. Save Rawใน Bitwiseมี caveatอะไร?  
    **เฉลย:** ปัจจุบัน save UTF-8 formatted report ไม่ใช่ transformed raw bytes

## File Inspection

16. Header Checkดูข้อมูลเท่าไร?  
    **เฉลย:** อ่าน 16 bytes; executable checkอ่าน 4 bytes

17. Stringsจัดการ valid UTF-8กับ binaryต่างกันอย่างไร?  
    **เฉลย:** valid UTF-8 copyทั้ง text; invalid scan printable ASCII runsยาว≥4

18. Regex countครอบคลุม full fileหรือไม่?  
    **เฉลย:** ไม่ ครอบคลุม displayed preview ≤128 KiB/Max lines

19. ทำไมพบ `MZ`ยังไม่พิสูจน์ว่าเป็น PEสมบูรณ์?  
    **เฉลย:** checkerดูแค่ prefix ไม่ parse PE header/sections

20. zstegหน้า File Inspectionตรวจอะไรล่วงหน้า?  
    **เฉลย:** แค่ extension `.png/.bmp`, แล้วรัน `['zsteg',path]`

21. Custom regex persistหรือไม่?  
    **เฉลย:** ไม่ อยู่ใน dict runtime sessionเท่านั้น

## Pipeline/external commands

22. Auto modeหมายถึงไม่มี interactionหรือไม่?  
    **เฉลย:** ไม่ แต่ละ nodeยังเปิด step windowให้ Run/Next

23. Node execution orderมาจากอะไร?  
    **เฉลย:** listที่ sortตาม x-positionหลัง drag; yไม่เกี่ยว

24. Text toolรับ inputอย่างไร? File toolอย่างไร?  
    **เฉลย:** textผ่าน stdin; fileเป็น positional/flag/keyvalue argvตาม config

25. Pipe `|` ใน manual argsทำงานหรือไม่?  
    **เฉลย:** ไม่ Pipelineใช้ shell=False; `|`เป็น literal argv

26. Artifact Bridgeสร้าง temp fileเมื่อใด?  
    **เฉลย:** previous outputเป็น non-printable/binary bytes; textปกติไม่สร้าง

27. Successของ Pipelineกำหนดอย่างไร?  
    **เฉลย:** return code 0; ไม่ตรวจ semantic correctness

28. `dd` inputแนบแบบใด?  
    **เฉลย:** keyvalue `if=FILE`; output `of=`ผู้ใช้เพิ่มเอง

29. ทำไม `gzip_decompress` อาจ compress?  
    **เฉลย:** `-d`เป็น checkboxไม่ใช่ hardcode; ไม่ติ๊ก argvคือ `gzip FILE`

30. ทำไม `steghide FILE`เป็นจุดผิดปกติ?  
    **เฉลย:** configไม่มี `extract/info` subcommandหรือ correct input flag

31. Saved pipelineไม่เก็บอะไรบ้าง?  
    **เฉลย:** runtime option values, input/original, positions, output, mode, cwd/env

32. Output file discoveryพิสูจน์ provenanceไหม?  
    **เฉลย:** ไม่ แค่ before/after metadata changeใน watched locations

## OpenSSL/AES

33. AES-128/192/256หมายถึง block sizeหรือ key size?  
    **เฉลย:** key size; block sizeทุกแบบ128 bits

34. จำนวน rounds?  
    **เฉลย:** 10/12/14ตามลำดับ

35. ECBใช้ IVหรือไม่ และมีปัญหาอะไร?  
    **เฉลย:** ไม่; plaintext blockซ้ำให้ ciphertextซ้ำ จึงเผย pattern

36. CBCต้อง paddingหรือไม่?  
    **เฉลย:** ปกติต้องสำหรับข้อมูลไม่เต็ม16 bytes; `enc`เติม standard paddingเว้น `-nopad`

37. CTR/OFB reuse nonce/IVกับ keyเดิมเป็นอย่างไร?  
    **เฉลย:** reuse keystream ทำให้ XOR ciphertextเผย relation plaintext;ร้ายแรง

38. GCMให้คุณสมบัติอะไรเพิ่ม?  
    **เฉลย:** authentication tag/integrity (AEAD) นอกจาก confidentiality

39. `openssl enc`รองรับ GCMหรือไม่?  
    **เฉลย:** ไม่ตาม docs 3.5และการรันตรวจ; library OpenSSLอาจรองรับผ่าน APIอื่น

40. `-K` CBCอย่างเดียวพอไหม?  
    **เฉลย:** ไม่ ต้อง `-iv`; หรือใช้ passphrase KDFที่ derive key/IV

41. Saltกับ IVเหมือนกันไหม?  
    **เฉลย:** ไม่ Saltใช้ KDF; IVใช้ mode state

42. `-a`เพิ่มความปลอดภัยไหม?  
    **เฉลย:** ไม่ เป็น Base64 wrapper

## Gemini/App Portal/state

43. Geminiส่ง fileเมื่อใด?  
    **เฉลย:** tokenใน promptเป็น existing path, ≤1 MiBและ UTF-8; contentถูกรวม prompt

44. Prompt capเท่าไร?  
    **เฉลย:** 4 MiBรวม history/attachments

45. Full responseยาวถูก parse EXEC/SAVEไหม?  
    **เฉลย:** ไม่ เพื่อป้องกัน actionจาก truncated preview

46. EXECสูงสุดกี่รอบและใช้อะไรรัน?  
    **เฉลย:** 2 รอบ;หลัง Allow ใช้ shell=True timeout30 s

47. SAVEเขียนแบบใด?  
    **เฉลย:** หลัง Allowใช้ text mode `w`, UTF-8, overwrite, ไม่ atomic

48. App Portalต่าง Pipelineเรื่อง shellอย่างไร?  
    **เฉลย:** Portalใช้ raw command `shell=True`; Pipelineใช้ argument list `shell=False`

49. Browse Installed Apps parse desktop fileครบ specificationไหม?  
    **เฉลย:** ไม่ อ่าน Name/Execแรก, ตัดหลัง `%`, tokenแรก, filter NoDisplay/Terminal

50. Dashboard Historyกับ Solve Historyเหมือนกันไหม?  
    **เฉลย:** ไม่ Dashboardเป็น analytics JSONหลายหน้า; Solve Historyเป็น bounded SQLiteละเอียดเฉพาะ 3หน้า

51. Challenge timerเกิดอะไรเมื่อ kill app?  
    **เฉลย:** running timestampยังอยู่;เปิดใหม่ elapsedรวมเวลาช่วงปิดจน pause/update

52. “flag found” หมายถึงอะไร?  
    **เฉลย:** regex pattern matchเท่านั้น ไม่ได้ submitหรือ verifyกับ CTF platform
