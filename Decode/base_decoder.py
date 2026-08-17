import base64
import urllib.parse
import html
import codecs

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE45 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

def is_printable(text):
    return all(32 <= ord(c) <= 126 or c in "\n\r\t" for c in text)

def auto_detect_decode(data):
    text = data.decode(errors="ignore")

    candidates = [
        # Base encodings
        ("Base64", lambda d: base64.b64decode(d, validate=True)),
        ("Base32", lambda d: base64.b32decode(d)),
        ("Base85", lambda d: base64.b85decode(d)),
        ("Ascii85", lambda d: base64.a85decode(d)),
        ("Base16", lambda d: base64.b16decode(d)),
        ("Hex", lambda d: bytes.fromhex(text)),
        ("Base45", lambda d: decode_base45(text).encode()),
        ("Base58", lambda d: decode_base_n(text, BASE58).encode()),
        ("Base62", lambda d: decode_base_n(text, BASE62).encode()),
        ("Binary", lambda d: bytes(int(x, 2) for x in text.split())),
        ("Octal", lambda d: bytes(int(x, 8) for x in text.split())),
        ("Decimal", lambda d: bytes(int(x) for x in text.split())),

        # escape encodings และ Ciphers
        ("URL Decode", lambda d: urllib.parse.unquote(text).encode()),
        ("HTML Entity", lambda d: html.unescape(text).encode()),
        ("Unicode Escape", lambda d: codecs.decode(text, "unicode_escape").encode()),
        ("Reverse", lambda d: text[::-1].encode()), # เพิ่ม Reverse เข้ามาใน Auto Detect
        ("ROT13", lambda d: codecs.decode(text, "rot_13").encode()),
    ]

    for name, func in candidates:
        try:
            decoded = func(data)
            decoded_text = decoded.decode(errors="ignore")

            if decoded_text and is_printable(decoded_text):
                if decoded_text != text:   # สำคัญมาก: ผลลัพธ์ต้องเปลี่ยนไปจากเดิม
                    return name, decoded_text
        except Exception:
            pass

    return "Unknown", text # ถ้าหาไม่เจอจริงๆ ให้คืนค่าข้อความเดิมกลับไป

def decode_data(text, algo="Base64"):
    # (ฟังก์ชันนี้เหมือนเดิมของคุณเลยครับ)
    if algo == "Auto Detect":
        name, result = auto_detect_decode(text.encode())
        return result
    elif algo == "URL Decode":                     
        return urllib.parse.unquote(text)
    elif algo == "HTML Entity":                    
        return html.unescape(text)
    elif algo == "Unicode Escape":                 
        return codecs.decode(text, "unicode_escape")
    elif algo == "Base64":
        return base64.b64decode(text).decode(errors="ignore")
    elif algo == "Base32":
        return base64.b32decode(text).decode(errors="ignore")
    elif algo == "Base85":
        return base64.b85decode(text).decode(errors="ignore")
    elif algo == "Ascii85":
        return base64.a85decode(text).decode(errors="ignore")
    elif algo in ("Hex", "Base16"):
        return base64.b16decode(text).decode(errors="ignore")
    elif algo == "Base45":
        return decode_base45(text)
    elif algo == "Binary":
        return bytes(int(b, 2) for b in text.split()).decode(errors="ignore")
    elif algo == "Octal":
        return bytes(int(b, 8) for b in text.split()).decode(errors="ignore")
    elif algo == "Decimal":
        return bytes(int(b) for b in text.split()).decode(errors="ignore")
    elif algo == "Base58":
        return decode_base_n(text, BASE58)
    elif algo == "Base62":
        return decode_base_n(text, BASE62)
    elif algo == "Reverse":
        return text[::-1]
    elif algo == "ROT13":
        return codecs.decode(text, "rot_13")
    
    return text

def decode_base_n(text, alphabet):
    base = len(alphabet)
    num = 0
    for char in text:
        num = num * base + alphabet.index(char)
    return num.to_bytes((num.bit_length() + 7) // 8, "big").decode(errors="ignore")

def decode_base45(text):
    buf = []
    i = 0
    while i < len(text):
        if i + 2 < len(text):
            c = BASE45.index(text[i])
            d = BASE45.index(text[i + 1])
            e = BASE45.index(text[i + 2])
            x = c + d * 45 + e * 45 * 45
            buf.extend(divmod(x, 256))
            i += 3
        else:
            c = BASE45.index(text[i])
            d = BASE45.index(text[i + 1])
            x = c + d * 45
            buf.append(x)
            i += 2
    return bytes(buf).decode(errors="ignore")

# ============================================================
# P0.2 - BINARY SAFE DECODER
# ============================================================

import binascii


MAGIC_SIGNATURES = [
    (b"\x37\x7A\xBC\xAF\x27\x1C", "7-Zip Archive", ".7z"),
    (b"PK\x03\x04", "ZIP Archive", ".zip"),
    (b"\x1F\x8B", "GZIP Archive", ".gz"),
    (b"\x89PNG\r\n\x1a\n", "PNG Image", ".png"),
    (b"\xFF\xD8\xFF", "JPEG Image", ".jpg"),
    (b"%PDF", "PDF Document", ".pdf"),
    (b"\x7FELF", "ELF Executable", ".elf"),
    (b"MZ", "Windows Executable", ".exe"),
]


def detect_magic_bytes(data: bytes):
    """
    ตรวจ magic bytes จาก binary output

    return:
        {
            "type": "...",
            "extension": ".zip",
            "magic": "504B0304"
        }

    ถ้าไม่รู้จัก return None
    """

    if not isinstance(data, (bytes, bytearray)):
        return None

    for signature, file_type, extension in MAGIC_SIGNATURES:
        if data.startswith(signature):
            return {
                "type": file_type,
                "extension": extension,
                "magic": signature.hex().upper(),
            }

    return None


def is_probably_text(data: bytes) -> bool:
    """
    ใช้แค่ตัดสินว่าควร preview เป็น text หรือ binary
    ไม่ได้ใช้ตัด binary output ทิ้ง
    """

    if not data:
        return False

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False

    if not text:
        return False

    printable = 0

    for ch in text:
        if ch.isprintable() or ch in "\r\n\t":
            printable += 1

    ratio = printable / len(text)

    return ratio >= 0.90


def decode_to_bytes(text, algo="Base64") -> bytes:
    """
    Binary-safe decoder

    แตกต่างจาก decode_data():
    - ไม่บังคับ .decode()
    - output เป็น bytes เสมอ
    - archive/image/binary จะไม่สูญหาย
    """

    if isinstance(text, bytes):
        raw = text
        string_data = text.decode("utf-8", errors="ignore")
    else:
        string_data = str(text)
        raw = string_data.encode("utf-8")

    # ----------------------------------
    # Base encodings
    # ----------------------------------

    if algo == "Base64":
        cleaned = "".join(string_data.split())

        return base64.b64decode(
            cleaned,
            validate=False
        )

    elif algo == "Base32":
        cleaned = "".join(string_data.split())

        return base64.b32decode(cleaned)

    elif algo in ("Hex", "Base16"):
        cleaned = (
            string_data
            .replace(" ", "")
            .replace("\n", "")
            .replace("\r", "")
            .replace(":", "")
        )

        return bytes.fromhex(cleaned)

    elif algo == "Base85":
        return base64.b85decode(string_data)

    elif algo == "Ascii85":
        return base64.a85decode(string_data)

    # ----------------------------------
    # Text transforms
    # ----------------------------------

    elif algo == "Reverse":
        return raw[::-1]

    elif algo == "ROT13":
        result = codecs.decode(string_data, "rot_13")
        return result.encode("utf-8")

    elif algo == "URL Decode":
        result = urllib.parse.unquote_to_bytes(string_data)
        return result

    elif algo == "HTML Entity":
        result = html.unescape(string_data)
        return result.encode("utf-8")

    elif algo == "Unicode Escape":
        result = codecs.decode(string_data, "unicode_escape")
        return result.encode("utf-8")

    raise ValueError(f"Unsupported binary-safe decoder: {algo}")
def describe_decoded_data(data: bytes) -> dict:
    """
    สร้างข้อมูลสำหรับ GUI / Pipeline
    """

    magic = detect_magic_bytes(data)

    result = {
        "size": len(data),
        "is_text": is_probably_text(data),
        "magic": magic,
        "text_preview": None,
        "hex_preview": None,
    }

    if result["is_text"]:
        result["text_preview"] = data.decode(
            "utf-8",
            errors="replace"
        )[:2000]

    else:
        preview = data[:64]

        result["hex_preview"] = " ".join(
            f"{b:02X}" for b in preview
        )

    return result