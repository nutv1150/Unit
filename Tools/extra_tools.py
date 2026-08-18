# นำเข้า module สำหรับจัดการ Base64 encoding/decoding
import base64

# นำเข้า module สำหรับจัดการ HTML escape/unescape
import html

# นำเข้า module สำหรับจัดการ URL encode/decode
import urllib.parse
import re

from Tools.flag_detector import find_first_flag

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
    Smart CTF byte parser.

    รองรับ:
    - 2c 26 2b
    - 2c:26:2b
    - 2c-26-2b
    - 0x2c, 0x26, 0x2b
    - @(0x2c,0x26,...)
    - $data = @(0x2c,...)
    - data = [0x2c, ...]
    - unsigned char data[] = {0x2c, ...}
    - \\x2c\\x26\\x2b
    - raw text fallback
    """

    cleaned = raw.strip()

    if not cleaned:
        raise ValueError("❌ Input ว่าง")

    # =====================================================
    # 1. Variable/array assignment
    #
    # สำคัญ: ถ้ามีทั้ง:
    #
    # $key  = 0x4A
    # $data = @(0x2c,...)
    #
    # ต้อง extract เฉพาะ $data
    # ห้ามเอา 0x4A มาปนใน ciphertext
    # =====================================================

    assignment_patterns = [
        # PowerShell
        r"(?is)\$(?:data|bytes|payload|encoded|ciphertext)"
        r"\s*=\s*@\((.*?)\)",

        # Python / generic [...]
        r"(?is)(?:data|bytes|payload|encoded|ciphertext)"
        r"\s*=\s*\[(.*?)\]",

        # C / generic {...}
        r"(?is)(?:data|bytes|payload|encoded|ciphertext)"
        r"[^\n=]*=\s*\{(.*?)\}",
    ]

    for pattern in assignment_patterns:
        match = re.search(pattern, cleaned)

        if match:
            body = match.group(1)

            tokens = re.findall(
                r"(?i)0x([0-9a-f]{1,2})\b",
                body
            )

            if tokens:
                return (
                    bytes(int(x, 16) for x in tokens),
                    "hex array"
                )

    # =====================================================
    # 2. Escaped hex
    #
    # \x2c\x26\x2b
    # =====================================================

    escaped = re.findall(
        r"(?i)\\x([0-9a-f]{2})",
        cleaned
    )

    if escaped:
        return (
            bytes(int(x, 16) for x in escaped),
            "escaped hex"
        )

    # =====================================================
    # 3. 0xNN byte list
    #
    # 0x2c,0x26,0x2b
    # @(0x2c,0x26,...)
    # =====================================================

    hex_tokens = re.findall(
        r"(?i)\b0x([0-9a-f]{1,2})\b",
        cleaned
    )

    if len(hex_tokens) >= 2:
        return (
            bytes(int(x, 16) for x in hex_tokens),
            "hex byte array"
        )

    # =====================================================
    # 4. Plain hex
    #
    # 2c 26 2b
    # 2c:26:2b
    # 2c-26-2b
    # 2c262b
    # =====================================================

    hex_try = (
        cleaned
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace(":", "")
        .replace("-", "")
        .replace(",", "")
    )

    if (
        len(hex_try) >= 2
        and len(hex_try) % 2 == 0
        and all(
            c in "0123456789abcdefABCDEF"
            for c in hex_try
        )
    ):
        try:
            return bytes.fromhex(hex_try), "hex"
        except ValueError:
            pass

    # =====================================================
    # 5. Raw text fallback
    # =====================================================

    try:
        return cleaned.encode("utf-8"), "raw"

    except Exception:
        raise ValueError("❌ Input ไม่ถูกต้อง")

def detect_embedded_key(raw: str):
    """
    Detect key ที่ฝังอยู่ใน CTF snippets.

    ตัวอย่าง:
        $key = 0x4A
        key = 74
        xor_key = "secret"
    """

    text = raw.strip()

    if not text:
        return None

    # -----------------------------------------------------
    # HEX key
    # $key = 0x4A
    # key = 0x41
    # xor_key = 0xFF
    # -----------------------------------------------------

    match = re.search(
        r"(?im)"
        r"(?:\$?key|xor[_\s-]?key)"
        r"\s*=\s*"
        r"(0x[0-9a-f]+)",
        text
    )

    if match:
        return {
            "key": match.group(1),
            "type": "hex",
            "source": match.group(0),
        }

    # -----------------------------------------------------
    # Decimal
    # key = 74
    # -----------------------------------------------------

    match = re.search(
        r"(?im)"
        r"(?:\$?key|xor[_\s-]?key)"
        r"\s*=\s*"
        r"([0-9]+)",
        text
    )

    if match:
        return {
            "key": match.group(1),
            "type": "decimal",
            "source": match.group(0),
        }

    # -----------------------------------------------------
    # Quoted ASCII
    # key = "secret"
    # key = 'J'
    # -----------------------------------------------------

    match = re.search(
        r"""(?im)
        (?:\$?key|xor[_\s-]?key)
        \s*=\s*
        ["']([^"']+)["']
        """,
        text,
        re.VERBOSE
    )

    if match:
        return {
            "key": match.group(1),
            "type": "ascii",
            "source": match.group(0),
        }

    return None


# ฟังก์ชัน parse key
def _parse_key_bytes(key_str: str) -> tuple:
    """
    Parse XOR/bitwise key.

    รองรับ:
    0x4A        -> hex number -> b'\x4a'
    74          -> decimal    -> b'\x4a'
    4A4B        -> hex string -> b'\x4a\x4b'
    4A:4B       -> hex string
    hello       -> ASCII
    """

    k = key_str.strip()

    if not k:
        raise ValueError("❌ Key ว่าง")

    # =====================================================
    # 1. HEX NUMBER
    # เช่น 0x4A, 0xff, 0X4142
    # =====================================================
    if k.lower().startswith("0x"):
        hex_part = k[2:].strip()

        if not hex_part:
            raise ValueError("❌ Invalid hex key")

        if not all(c in "0123456789abcdefABCDEF" for c in hex_part):
            raise ValueError(f"❌ Invalid hex key: {k}")

        # bytes.fromhex ต้องจำนวน hex เป็นเลขคู่
        if len(hex_part) % 2 != 0:
            hex_part = "0" + hex_part

        return bytes.fromhex(hex_part), "hex number"

    # =====================================================
    # 2. DECIMAL NUMBER
    # 74 -> 0x4A
    # =====================================================
    if k.isdigit():
        val = int(k, 10)

        if val < 0:
            raise ValueError("❌ Key must be positive")

        size = max(1, (val.bit_length() + 7) // 8)

        return val.to_bytes(size, "big"), "decimal"

    # =====================================================
    # 3. HEX BYTE STRING
    # เช่น:
    # 4A4B
    # 4A 4B
    # 4A:4B
    # 4A-4B
    # =====================================================
    hex_try = (
        k.replace(" ", "")
         .replace(":", "")
         .replace("-", "")
    )

    if (
        len(hex_try) >= 2
        and len(hex_try) % 2 == 0
        and all(c in "0123456789abcdefABCDEF" for c in hex_try)
    ):
        return bytes.fromhex(hex_try), "hex string"

    # =====================================================
    # 4. ASCII STRING
    # =====================================================
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
    flag = find_first_flag(b)

    if flag:
        return f"🚩 FLAG DETECTED: {flag}"

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
     # รวมเป็นกล่อง
    lines = [
        "╔══════════════════════════════════════════",
        f"║  Operation : {op_label}",
        f"║  Input     : {data_fmt}  ({len(result)} bytes)",
        f"║  Key       : {key_raw!r}  [{key_fmt}]"
        + (f"  → repeating {len(key_bytes)} byte(s)" if len(key_bytes) > 1 else ""),
        "╠══════════════════════════════════════════",
        "║  [HEX]",
        f"║  {hex_space}",
        "╠══════════════════════════════════════════",
        "║  [ASCII / UTF-8]",
        f"║  {ascii_out}",
        "╠══════════════════════════════════════════",
        f"║  Printable : {printable}",
    ]
    if flag:
        lines.append(f"║  {flag}")
    lines.append("╚══════════════════════════════════════════")
    return "\n".join(lines)


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