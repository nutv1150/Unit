### Slide Flow

**Shadow Council**

---

#### ขั้น 1 — เจออะไรในไฟล์

ภาพโจทย์ Shadow Council ให้ติดตามผู้ใช้ `d4ag0n` จาก Windows 10 triage image และหายอด BTC ใน ledger ที่เก็บไว้นอกเครื่อง ก่อนแปลงยอดทศนิยมหนึ่งตำแหน่งเป็น MD5
![[Screenshot 2026-08-15 154206.png]]

เริ่มด้วย **unzip และ 7-Zip ภายนอก** เพื่อดูรายการหลักฐาน:
```bash
mkdir -p /tmp/unit-shadow
cd /tmp/unit-shadow
unzip -p "/home/nutvv/Downloads/tctt2026.zip" "tctt2026/Shadow Council/ShadowCouncil-triage-v2.zip" > shadow-triage.zip
7z l shadow-triage.zip
```

`unzip -p` อ่าน ZIP ซ้อนออกมาเป็นไฟล์; `7z l` แสดงรายชื่อ ขนาด และชนิดข้อมูลโดยไม่แตกทุกไฟล์

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| Windows workstation / triage image | เป็นงานตรวจหลักฐานเครื่องผู้ใช้ | 7-Zip ดู archive แล้วใช้เครื่องมือ disk forensics |
| นามแฝง d4ag0n | ใช้ระบุข้อมูลบัญชีหรือบทสนทนาที่เกี่ยวข้อง | ค้นในหลักฐานที่กู้จาก image |
| ledger somewhere off the machine | ยอดเงินอาจไม่อยู่ในไฟล์ในเครื่องโดยตรง | หาเบาะแสจาก browser/chat ก่อนระบุ ledger |
| total BTC to one decimal place | ต้องรู้ยอดเงินจริงก่อนจัดรูปแบบ | จัดเป็นข้อความทศนิยมหนึ่งตำแหน่ง |
| TCTT2026{md5} | นำ digest มาห่อเป็น flag | UNIT → Data Hashing → Hash → md5 |

---

#### ขั้น 3 — ผลจากหลักฐานของเคส

archive มี VHDX disk image ขนาด **1,379,926,016 ไบต์** ขั้นคำนวณ MD5 ต้องใช้ยอด BTC จาก ledger เป็น input แต่ข้อมูลที่แนบของ Shadow ไม่มีข้อความ ledger หรือยอด BTC ให้คำนวณ

จึงแสดงผลได้ถึงรายการหลักฐาน VHDX และเงื่อนไขแปลงยอดเงินจากภาพโจทย์ ไม่ใช้ข้อมูล XOR/Scytale หรือ flag ของ Phantom Spartan มาแทนเคสนี้
![[shadow — รายการ VHDX และเงื่อนไขยอด BTC ในภาพโจทย์]]
