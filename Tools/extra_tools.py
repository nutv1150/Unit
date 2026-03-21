# นำเข้า module สำหรับจัดการ Base64 encoding/decoding
import base64

# นำเข้า module สำหรับจัดการ HTML escape/unescape
import html

# นำเข้า module สำหรับจัดการ URL encode/decode
import urllib.parse


# =========================
# Search Highlight Tool
# =========================

# ฟังก์ชันสำหรับ highlight คำใน textbox
def highlight_text(textbox, keyword):
    """
    Highlight คำใน textbox (CustomTkinter / Tkinter)
    รองรับทั้งภาษาไทย อังกฤษ และตัวเลข
    """

    # ลบ highlight เก่าทั้งหมดออกจาก textbox
    textbox.tag_remove("highlight", "1.0", "end")

    # ถ้าไม่มี keyword (ค่าว่าง) ให้หยุดทำงานทันที
    if not keyword:
        return

    # กำหนดจุดเริ่มต้นของการค้นหาเป็นตำแหน่งแรกของ textbox
    start = "1.0"

    # วนลูปค้นหาคำไปเรื่อย ๆ
    while True:
        # ค้นหา keyword ใน textbox โดยไม่สนใจตัวพิมพ์เล็ก/ใหญ่
        pos = textbox.search(keyword, start, stopindex="end", nocase=True)

        # ถ้าไม่พบคำ → ออกจากลูป
        if not pos:
            break

        # คำนวณตำแหน่งจบของคำที่เจอ (pos + ความยาว keyword)
        end = f"{pos}+{len(keyword)}c"
        
        # เพิ่ม tag "highlight" ครอบช่วงคำที่เจอ
        textbox.tag_add("highlight", pos, end)

        # อัปเดต start ให้ไปต่อจากคำล่าสุด เพื่อค้นหาคำถัดไป
        start = end

    # ตั้งค่าสีของ highlight (พื้นหลัง + ตัวอักษร)
    textbox.tag_config("highlight", background="#FFCC00", foreground="black")


# =========================
# Bitwise Masking Tools
# =========================

# ฟังก์ชัน parse input เป็น bytes พร้อมบอกชนิด
def _parse_input_bytes(raw: str) -> tuple:
    """
    แปลง input เป็น bytes
    คืนค่า (bytes, ประเภทข้อมูล)
    """

    # ตัดช่องว่างหน้า-หลัง
    cleaned = raw.strip()

    # ลองแปลงเป็น hex โดยลบตัวคั่น
    hex_try = cleaned.replace(" ", "").replace(":", "").replace("-", "")

    # ตรวจว่าเป็น hex ถูกต้องไหม
    if (
        len(hex_try) >= 2 and                      # ต้องมีความยาวอย่างน้อย 2
        len(hex_try) % 2 == 0 and                  # ต้องเป็นเลขคู่
        all(c in "0123456789abcdefABCDEF" for c in hex_try)  # ต้องเป็น hex
    ):
        try:
            return bytes.fromhex(hex_try), "hex"   # แปลงเป็น bytes
        except ValueError:
            pass  # ถ้าแปลงไม่ได้ให้ข้าม

    # ถ้าไม่ใช่ hex → แปลงเป็น UTF-8
    try:
        return cleaned.encode("utf-8"), "raw"
    except Exception:
        # ถ้าแปลงไม่ได้ให้ error
        raise ValueError("❌ Input ไม่ถูกต้อง")


# ฟังก์ชัน parse key
def _parse_key_bytes(key_str: str) -> tuple:

    # ตัดช่องว่าง
    k = key_str.strip()

    # ถ้า key ว่าง → error
    if not k:
        raise ValueError("❌ Key ว่าง")

    # ถ้าเป็นรูปแบบ 0x (hex number)
    if k.lower().startswith("0x"):
        val = int(k, 16)  # แปลงเป็น int base 16
        # แปลงเป็น bytes
        return val.to_bytes((val.bit_length() + 7) // 8 or 1, "big"), "hex number"

    # ถ้าเป็นตัวเลขล้วน (decimal)
    if k.isdigit():
        val = int(k)
        b = val.to_bytes((val.bit_length() + 7) // 8 or 1, "big")
        return b, "decimal"

    # ลองเป็น hex string
    hex_try = k.replace(" ", "").replace(":", "")

    if (
        len(hex_try) >= 4 and
        len(hex_try) % 2 == 0 and
        all(c in "0123456789abcdefABCDEF" for c in hex_try)
    ):
        return bytes.fromhex(hex_try), "hex string"

    # ถ้าไม่เข้าเงื่อนไข → ใช้เป็น ASCII
    return k.encode("utf-8"), "ascii"


# ทำ key ให้ยาวเท่าข้อมูล
def _repeat_key(key_bytes: bytes, length: int) -> bytes:

    # ถ้า key ว่าง → error
    if not key_bytes:
        raise ValueError("Key ว่าง")

    # ทำ key ซ้ำจนยาวพอ แล้วตัดให้เท่าขนาด data
    return (key_bytes * ((length // len(key_bytes)) + 1))[:length]


# ตรวจว่า printable ไหม
def _is_printable(b: bytes) -> bool:

    # เช็คทุก byte ว่าอยู่ในช่วง printable ASCII หรือ whitespace
    return all(0x20 <= byte < 0x7F or byte in (9, 10, 13) for byte in b)


# ตรวจ flag pattern
def _flag_hint(b: bytes) -> str:
    try:
        # decode เป็น string
        text = b.decode("utf-8", errors="ignore")

        # pattern ที่ใช้ตรวจ
        patterns = ["flag{", "CTF{", "picoCTF{"]

        # ตรวจทีละ pattern
        for p in patterns:
            if p in text:
                return f"พบ {p}"

    except:
        pass

    return ""


# ฟังก์ชัน format output
def _format_output(result: bytes, op_label: str, data_fmt: str,
                   key_raw: str, key_fmt: str, key_bytes: bytes) -> str:

    # แปลงเป็น hex
    hex_out = result.hex().upper()

    # แบ่ง hex ทีละ byte
    hex_space = " ".join(hex_out[i:i+2] for i in range(0, len(hex_out), 2))

    # แปลงเป็น ascii
    ascii_out = result.decode("utf-8", errors="replace")

    # เช็ค printable
    printable = "Printable" if _is_printable(result) else "Binary"

    # ตรวจ flag
    flag = _flag_hint(result)

    # รวมผลลัพธ์เป็น string
    return f"{op_label}\n{hex_space}\n{ascii_out}\n{printable}\n{flag}"


# ฟังก์ชันหลัก mask
def bitwise_mask(data: str, key: str, mode: str = "xor"):

    # parse input
    data_bytes, data_fmt = _parse_input_bytes(data)

    # parse key
    key_bytes, key_fmt = _parse_key_bytes(key)

    # ทำ key ให้ยาวเท่าข้อมูล
    key_rep = _repeat_key(key_bytes, len(data_bytes))

    # XOR
    if mode == "xor":
        result = bytes(a ^ b for a, b in zip(data_bytes, key_rep))
        label = "XOR"

    # OR
    elif mode == "or":
        result = bytes(a | b for a, b in zip(data_bytes, key_rep))
        label = "OR"

    # AND
    elif mode == "and":
        result = bytes(a & b for a, b in zip(data_bytes, key_rep))
        label = "AND"

    # mode ไม่ถูกต้อง
    else:
        raise ValueError("mode ผิด")

    # ส่ง output
    return _format_output(result, label, data_fmt, key, key_fmt, key_bytes)


# XOR unmask (เหมือน XOR ซ้ำ)
def bitwise_unmask(data: str, key: str):

    # เรียก XOR mask อีกครั้ง
    return bitwise_mask(data, key, "xor")


# =========================
# Encoding Tools
# =========================

# URL encode
def encode_url(text):
    return urllib.parse.quote(text)

# URL decode
def decode_url(text):
    return urllib.parse.unquote(text)

# Base64 encode
def encode_urlsafe_base64(text):
    return base64.urlsafe_b64encode(text.encode()).decode()

# Base64 decode
def decode_urlsafe_base64(text):
    return base64.urlsafe_b64decode(text).decode()

# HTML encode
def encode_html_entities(text):
    return html.escape(text)

# HTML decode
def decode_html_entities(text):
    return html.unescape(text)

# Unicode escape encode
def encode_unicode_escape(text):
    return text.encode("unicode_escape").decode()

# Unicode escape decode
def decode_unicode_escape(text):
    return text.encode().decode("unicode_escape")