"""
Extra Tools Module
รวมฟังก์ชัน:

- Search + Highlight text
- XOR / OR / AND Masking + Unmasking
- URL / HTML / Unicode Escape Encode Decode

ออกแบบให้ใช้ต่อกับ CustomTkinter textbox ได้ทันที
"""

import base64
import html
import urllib.parse


# =========================
# Search Highlight Tool
# =========================

def highlight_text(textbox, keyword):
    """
    Highlight คำใน textbox (CustomTkinter / Tkinter)
    รองรับทั้งภาษาไทย อังกฤษ และตัวเลข
    """
    # 1. เคลียร์ highlight เก่าออกก่อน
    textbox.tag_remove("highlight", "1.0", "end")

    if not keyword:
        return

    start = "1.0"
    while True:
        # ใช้ nocase=True เพื่อให้หาเจอทั้งตัวเล็กและตัวใหญ่
        pos = textbox.search(keyword, start, stopindex="end", nocase=True)

        if not pos:
            break

        # คำนวณจุดสิ้นสุดของคำที่เจอ: {ตำแหน่งที่เจอ} + {ความยาว keyword} characters
        end = f"{pos}+{len(keyword)}c"
        
        # ใส่ Tag highlight
        textbox.tag_add("highlight", pos, end)

        # สำคัญ: เลื่อนจุดเริ่มต้นไปที่จุดสิ้นสุดของคำที่เพิ่งเจอ เพื่อหาคำถัดไป
        start = end

    # ตั้งค่าสี (ทำครั้งเดียวหรือไว้ในตอนเริ่มต้นโปรแกรมก็ได้)
    textbox.tag_config("highlight", background="#FFCC00", foreground="black")


# =========================
# Bitwise Masking Tools (CTF-grade)
# =========================
#
# Input รองรับ:
#   - Hex string  เช่น "41 42 43", "414243", "41:42:43"
#   - Raw text    เช่น "Hello CTF"
#   (auto-detect อัตโนมัติ)
#
# Key รองรับ:
#   - decimal     เช่น "66"
#   - 0x hex      เช่น "0x42"
#   - hex string  เช่น "DEADBEEF"
#   - ASCII/text  เช่น "mykey"  → repeating key
#
# Output: multi-format (Hex / ASCII / Printable check / Flag hint)
# =========================


def _parse_input_bytes(raw: str) -> tuple:
    """
    Auto-detect และ parse input เป็น bytes
    คืน (bytes, format_name: str)
    format_name: "hex" | "raw"
    """
    cleaned = raw.strip()

    # ลอง Hex string: รองรับ "4142", "41 42", "41:42", "41-42"
    hex_try = cleaned.replace(" ", "").replace(":", "").replace("-", "")
    if (
        len(hex_try) >= 2
        and len(hex_try) % 2 == 0
        and all(c in "0123456789abcdefABCDEF" for c in hex_try)
    ):
        try:
            return bytes.fromhex(hex_try), "hex"
        except ValueError:
            pass

    # Fallback → Raw ASCII/UTF-8
    try:
        return cleaned.encode("utf-8"), "raw"
    except Exception:
        raise ValueError(
            "❌ Input Error: ไม่สามารถ parse input ได้\n"
            "รองรับ: Hex string (41 42 43) หรือ Raw text (Hello CTF)"
        )


def _parse_key_bytes(key_str: str) -> tuple:
    """
    Parse key เป็น bytes รองรับหลายรูปแบบ
    คืน (bytes, format_name: str)

    - "0x41"     → hex number  → b'A'
    - "66"       → decimal     → b'B'
    - "DEADBEEF" → hex string  → 4 bytes
    - "mykey"    → ASCII       → b'mykey'
    """
    k = key_str.strip()
    if not k:
        raise ValueError(
            "❌ Key Error: กรุณาใส่ Key\n\n"
            "รูปแบบที่รองรับ:\n"
            "  decimal    เช่น  66\n"
            "  0x hex     เช่น  0x42\n"
            "  hex string เช่น  DEADBEEF\n"
            "  ASCII text เช่น  mykey"
        )

    # 0x prefix → hex number
    if k.lower().startswith("0x"):
        try:
            val = int(k, 16)
            return val.to_bytes((val.bit_length() + 7) // 8 or 1, "big"), f"0x hex ({k})"
        except ValueError:
            raise ValueError(
                f"❌ Key Error: '{k}' ไม่ใช่ hex number ที่ถูกต้อง\n"
                "ตัวอย่าง: 0x41, 0xFF, 0xDEAD"
            )

    # ตัวเลข decimal ล้วน
    if k.isdigit():
        val = int(k)
        b = val.to_bytes((val.bit_length() + 7) // 8 or 1, "big")
        return b, f"decimal ({val} = 0x{val:X})"

    # Hex string ล้วน (ไม่มี 0x, ยาวคู่, อย่างน้อย 4 ตัว = 2 bytes)
    hex_try = k.replace(" ", "").replace(":", "")
    if (
        len(hex_try) >= 4
        and len(hex_try) % 2 == 0
        and all(c in "0123456789abcdefABCDEF" for c in hex_try)
    ):
        try:
            return bytes.fromhex(hex_try), f"hex string ({len(hex_try)//2} bytes)"
        except ValueError:
            pass

    # ASCII string fallback → repeating key
    return k.encode("utf-8"), f"ASCII string '{k}'"


def _repeat_key(key_bytes: bytes, length: int) -> bytes:
    """ทำ key ให้ยาวเท่า data โดย repeat (XOR repeating-key)"""
    if not key_bytes:
        raise ValueError("❌ Key Error: Key ว่างเปล่า")
    return (key_bytes * ((length // len(key_bytes)) + 1))[:length]


def _is_printable(b: bytes) -> bool:
    """ตรวจว่า bytes อ่านได้เป็น text ทั้งหมดไหม"""
    return all(0x20 <= byte < 0x7F or byte in (0x09, 0x0A, 0x0D) for byte in b)


def _flag_hint(b: bytes) -> str:
    """ตรวจว่ามี flag pattern ทั่วไปใน CTF ไหม"""
    try:
        text = b.decode("utf-8", errors="ignore")
        patterns = [
            "flag{", "FLAG{", "CTF{", "ctf{",
            "THCTT", "thctt",
            "picoCTF{", "HTB{", "THM{", "DUCTF{",
        ]
        for p in patterns:
            if p in text:
                return f"🚩 FLAG DETECTED: พบ pattern '{p}'"
    except Exception:
        pass
    return ""


def _format_output(result: bytes, op_label: str, data_fmt: str,
                   key_raw: str, key_fmt: str, key_bytes: bytes) -> str:
    """สร้าง output แบบ multi-format สำหรับแสดงผล"""
    hex_out   = result.hex().upper()
    hex_space = " ".join(hex_out[i:i+2] for i in range(0, len(hex_out), 2))
    ascii_out = result.decode("utf-8", errors="replace")
    printable = (
        "✅ Printable (likely text)"
        if _is_printable(result)
        else "⚠️  Non-printable (binary data)"
    )
    flag = _flag_hint(result)

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


def bitwise_mask(data: str, key: str, mode: str = "xor") -> str:
    """
    XOR / OR / AND masking แบบ CTF-grade

    Args:
        data  → input string (Hex string หรือ Raw text — auto-detect)
        key   → key string (decimal / 0xHex / HexStr / ASCII — auto-detect)
        mode  → "xor" | "or" | "and"

    Returns:
        output string แบบ multi-format (Hex + ASCII + Printable)
    """
    data_bytes, data_fmt = _parse_input_bytes(data)
    key_bytes,  key_fmt  = _parse_key_bytes(key)
    key_rep = _repeat_key(key_bytes, len(data_bytes))

    if mode == "xor":
        result = bytes(a ^ b for a, b in zip(data_bytes, key_rep))
        label  = "XOR"
    elif mode == "or":
        result = bytes(a | b for a, b in zip(data_bytes, key_rep))
        label  = "OR"
    elif mode == "and":
        result = bytes(a & b for a, b in zip(data_bytes, key_rep))
        label  = "AND"
    else:
        raise ValueError(f"❌ mode ไม่ถูกต้อง: '{mode}'  (ใช้ xor | or | and)")

    return _format_output(result, label, data_fmt, key, key_fmt, key_bytes)


def bitwise_unmask(data: str, key: str) -> str:
    """
    XOR Unmask — เหมือน XOR Mask ทุกอย่าง (XOR ซ้ำกลับได้เสมอ)
    OR/AND ไม่ reversible จึงไม่มี OR/AND Unmask

    Args:
        data → ciphertext (Hex string หรือ Raw text)
        key  → key เดิมที่ใช้ตอน mask
    """
    return bitwise_mask(data, key, "xor")


# =========================
# Escape Encoding Tools
# =========================

def encode_url(text):
    """URL Percent Encode"""
    return urllib.parse.quote(text)


def decode_url(text):
    """URL Percent Decode"""
    return urllib.parse.unquote(text)


def encode_urlsafe_base64(text):
    """URL Safe Base64 Encode"""
    return base64.urlsafe_b64encode(text.encode()).decode()


def decode_urlsafe_base64(text):
    """URL Safe Base64 Decode"""
    try:
        return base64.urlsafe_b64decode(text).decode()
    except Exception:
        raise ValueError("URL-safe Base64 decode failed")


def encode_html_entities(text):
    """HTML Entity Encode"""
    return html.escape(text)


def decode_html_entities(text):
    """HTML Entity Decode"""
    return html.unescape(text)


def encode_unicode_escape(text):
    """Unicode Escape Encode"""
    return text.encode("unicode_escape").decode()


def decode_unicode_escape(text):
    """Unicode Escape Decode"""
    try:
        return text.encode().decode("unicode_escape")
    except Exception:
        raise ValueError("Unicode escape decode failed")