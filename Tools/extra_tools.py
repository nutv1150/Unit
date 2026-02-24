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
# Bitwise Masking Tools
# =========================

def bitwise_mask(data, key, mode="xor"):
    """
    XOR / OR / AND masking

    Args:
        data -> string input
        key -> integer key เช่น 0xFF หรือ 23
        mode -> xor | or | and
    """

    try:
        key = int(key)
    except ValueError:
        raise ValueError("Key ต้องเป็นตัวเลขเท่านั้น")

    raw = data.encode()

    result = bytearray()

    for b in raw:

        if mode == "xor":
            result.append(b ^ key)

        elif mode == "or":
            result.append(b | key)

        elif mode == "and":
            result.append(b & key)

        else:
            raise ValueError("mode ไม่ถูกต้อง")

    return result.decode(errors="ignore")


def bitwise_unmask(data, key, mode="xor"):
    """
    XOR reversible แต่ OR/AND ไม่ reversible
    ฟังก์ชันนี้รองรับ XOR เท่านั้น
    """

    if mode != "xor":
        raise ValueError("OR/AND ไม่สามารถ Unmask ได้")

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