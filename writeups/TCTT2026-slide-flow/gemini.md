### Slide Flow

**Gemini Cryptography**

---

#### ขั้น 1 — เจออะไรในไฟล์

ใช้ **Archive Manager** เปิด `/home/nutvv/Downloads/tctt2026.zip` → กด **Extract** → เลือกโฟลเดอร์ปลายทาง แล้วเข้าโฟลเดอร์โจทย์ `Gemini_Cryptography`

เปิด `Gemini_Cryptography.png` ด้วยโปรแกรมดูภาพ พบข้อความ Base64 และ hint ให้หมุนอักขระ ASCII 47 ตำแหน่ง
![[Gemini_Cryptography.png]]

```text
Nz0yOExIRTRFRVw1NEA1Nlw+MkRFNkNcYV9hZE4
```

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| ข้อความมีชุดอักขระ Base64 | ต้องถอด Base64 ก่อน | UNIT → Data Hashing → Decode → Base64 |
| ความยาว 39 ตัว | Base64 ชุดนี้ขาด padding 1 ตัว | เติม `=` ท้ายข้อความให้ครบ 40 ตัว |
| ASCII rotation 47 | เลื่อนอักขระช่วง 33–126 | UNIT → ROT, n=47, mode=ascii |

Base64 เป็นชั้นนอก ส่วน ROT47 อยู่ด้านใน จึงถอดตามลำดับนี้

---

#### ขั้น 3 — ถอด Base64 ด้วย UNIT

**Step 1 — เตรียม input**

เติม `=` ที่ท้ายแล้ววางข้อความนี้ลง INPUT_STREAM:
```text
Nz0yOExIRTRFRVw1NEA1Nlw+MkRFNkNcYV9hZE4=
```

**Step 2 — เลือกเครื่องมือ**

ใน UNIT เปิด **Data Hashing → Decode → Base64** ผลปรากฏใน OUTPUT_STREAM โดยอัตโนมัติ:
```text
7=28LHE4EE\54@56\>2DE6C\a_adN
```

เครื่องหมาย `\` ทุกตัวเป็นข้อมูลจริง ต้องคัดลอกติดไปด้วย
![[gemini — UNIT Base64 input และ output]]

---

#### ขั้น 4 — ถอด ROT47 ด้วย UNIT

คัดลอก OUTPUT จากขั้นก่อนมาแทน INPUT เลือก **ROT** แล้วตั้งค่า:
```text
n = 47
mode = ascii (33-126)
```

โหมด `ascii` หมุนทั้งตัวอักษร ตัวเลข และเครื่องหมาย ไม่ใช้โหมด `alpha` ที่หมุนเฉพาะ A–Z/a–z

ผลใน OUTPUT_STREAM:
```text
flag{wtctt-dcode-master-2025}
```

![[gemini — UNIT ROT 47 ascii และ flag]]

---

#### ขั้น 5 — ปิดเคส

**🚩 Flag = `flag{wtctt-dcode-master-2025}`**
