import base64
import urllib.parse
import html
import codecs
from Tools.rot import rot_n, parse_rot_algo
from Tools.flag_detector import find_flags

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE45 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

STANDARD_HEX_ALPHABET = "0123456789ABCDEF"
CUSTOM_HEX_ALPHABET = "AJIHGFEDCBjihgfe"


def custom_hex_to_hex(text, alphabet=CUSTOM_HEX_ALPHABET):
    """แทนสัญลักษณ์ตามลำดับ 0–F โดยรักษาตัวพิมพ์ใหญ่เล็ก"""
    if len(alphabet) != 16 or len(set(alphabet)) != 16:
        raise ValueError("Hex alphabet ต้องมี 16 ตัวที่ไม่ซ้ำกัน")
    if any(c.isspace() for c in alphabet):
        raise ValueError("Hex alphabet ต้องไม่มีช่องว่าง")
    cleaned = "".join(text.split())
    # Hex ปกติรับ a–f ได้ด้วย แต่ตารางกำหนดเองต้องรักษาตัวพิมพ์
    if alphabet == STANDARD_HEX_ALPHABET:
        cleaned = cleaned.upper()
    mapping = dict(zip(alphabet, STANDARD_HEX_ALPHABET))
    unknown = next((c for c in cleaned if c not in mapping), None)
    if unknown is not None:
        raise ValueError(f"พบสัญลักษณ์ที่ไม่มีใน Hex alphabet: {unknown!r}")
    if len(cleaned) % 2:
        raise ValueError("Hex ต้องมีจำนวนสัญลักษณ์เป็นเลขคู่ (2 ตัวต่อ 1 byte)")
    return "".join(mapping[c] for c in cleaned)


def is_printable(text):
    return all(32 <= ord(c) <= 126 or c in "\n\r\t" for c in text)

def auto_detect_decode(data):
    # This heuristic works on text; never discard invalid source bytes to
    # manufacture a plausible match. Binary callers must choose a codec.
    text = data.decode("utf-8")

    candidates = [
        # Base encodings
        ("Base64", lambda d: base64.b64decode(d, validate=True)),
        ("Base32", lambda d: base64.b32decode(d)),
        ("Base85", lambda d: base64.b85decode(d)),
        ("Ascii85", lambda d: base64.a85decode(d)),
        ("Base16", lambda d: base64.b16decode(d)),
        ("Hex", lambda d: bytes.fromhex(text)),
        ("Base45", lambda d: decode_base45(text)),
        ("Base58", lambda d: decode_base_n(text, BASE58)),
        ("Base62", lambda d: decode_base_n(text, BASE62)),
        ("Binary", lambda d: bytes(int(x, 2) for x in text.split())),
        ("Octal", lambda d: bytes(int(x, 8) for x in text.split())),
        ("Decimal", lambda d: bytes(int(x) for x in text.split())),

        # escape encodings และ Ciphers
        ("URL Decode", lambda d: urllib.parse.unquote(text).encode()),
        ("HTML Entity", lambda d: html.unescape(text).encode()),
        ("Unicode Escape", lambda d: codecs.decode(text, "unicode_escape").encode()),
        ("Reverse", lambda d: text[::-1].encode()), # เพิ่ม Reverse เข้ามาใน Auto Detect

    ]

    # ลองทุก shift แต่ไม่ใช้ความ printable เพียงอย่างเดียวตัดสินค่า ROT
    rot_candidates = [
        (f"ROT:{n}:{mode}", rot_n(text, n, mode))
        for mode, limit in (("alpha", 25), ("ascii", 93))
        for n in range(1, limit + 1)
    ]
    fallback = None
    for name, func in candidates:
        try:
            decoded = func(data)
            decoded_text = decoded.decode("utf-8")

            if decoded_text and is_printable(decoded_text):
                if decoded_text != text:   # สำคัญมาก: ผลลัพธ์ต้องเปลี่ยนไปจากเดิม
                    if find_flags(decoded_text):
                        return name, decoded_text
                    if fallback is None:
                        fallback = (name, decoded_text)
        except Exception:
            pass

    for name, decoded_text in rot_candidates:
        if decoded_text != text and find_flags(decoded_text):
            return name, decoded_text
    if fallback is not None:
        return fallback
    return "Unknown", text # ถ้าหาไม่เจอจริงๆ ให้คืนค่าข้อความเดิมกลับไป

def decode_data(text, algo="Base64", alphabet=None):
    if algo == "Auto Detect":
        return auto_detect_decode(text if isinstance(text, bytes) else str(text).encode())[1]
    decoded = decode_to_bytes(text, algo, alphabet)
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        # Never silently discard/replace bytes in the legacy text API.  Hex is
        # an explicit, reversible display suitable for the GUI and callers
        # needing the original bytes should use decode_to_bytes().
        return decoded.hex()


def decode_base_n(text, alphabet):
    text = "".join(str(text).split())
    if not alphabet:
        raise ValueError("alphabet must not be empty")
    base = len(alphabet)
    num = 0
    for char in text:
        if char not in alphabet:
            raise ValueError(f"invalid character for base alphabet: {char!r}")
        num = num * base + alphabet.index(char)
    zero_count = len(text) - len(text.lstrip(alphabet[0]))
    size = (num.bit_length() + 7) // 8
    return (b"\0" * zero_count) + (num.to_bytes(size, "big") if size else b"")

def decode_base45(text):
    # Space is a valid Base45 digit, not ignorable formatting.
    text = str(text)
    if len(text) % 3 == 1:
        raise ValueError("Base45 length must not leave a single trailing symbol")
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
            if x > 255:
                raise ValueError("invalid Base45 final byte")
            buf.append(x)
            i += 2
    return bytes(buf)

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


def decode_to_bytes(text, algo="Base64", alphabet=None) -> bytes:
    """
    Binary-safe decoder

    แตกต่างจาก decode_data():
    - ไม่บังคับ .decode()
    - output เป็น bytes เสมอ
    - archive/image/binary จะไม่สูญหาย
    """

    if isinstance(text, bytes):
        raw = text
        string_data = text.decode("utf-8") if algo != "Reverse" else ""
    else:
        string_data = str(text)
        raw = string_data.encode("utf-8")

    if algo == "Custom Hex" or (algo == "Hex" and alphabet is not None):
        if alphabet is None:
            alphabet = CUSTOM_HEX_ALPHABET
        return bytes.fromhex(custom_hex_to_hex(string_data, alphabet))

    # ----------------------------------
    # Base encodings
    # ----------------------------------

    if algo in ("Base64", "URL-safe Base64"):
        cleaned = "".join(string_data.split())
        try:
            if algo == "URL-safe Base64":
                return base64.b64decode(cleaned, altchars=b"-_", validate=True)
            return base64.b64decode(cleaned, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError(f"invalid {algo} (including padding)") from exc

    elif algo == "Base32":
        cleaned = "".join(string_data.split())

        return base64.b32decode(cleaned)

    elif algo in ("Hex", "Base16"):
        # Colon-separated hex is a common hexdump spelling; it is only
        # accepted for the standard alphabet, never for a custom alphabet.
        cleaned = string_data.replace(":", " ")
        return bytes.fromhex(custom_hex_to_hex(cleaned, STANDARD_HEX_ALPHABET))

    elif algo == "Base85":
        return base64.b85decode(string_data)

    elif algo == "Ascii85":
        return base64.a85decode(string_data)

    elif algo == "Base45":
        return decode_base45(string_data)

    elif algo in ("Base58", "Base62"):
        return decode_base_n(string_data, BASE58 if algo == "Base58" else BASE62)

    elif algo == "Binary":
        tokens = string_data.split()
        if any(len(token) != 8 for token in tokens):
            raise ValueError("Binary values must be 8-bit groups")
        return bytes(int(token, 2) for token in tokens)

    elif algo == "Octal":
        return bytes(int(token, 8) for token in string_data.split())

    elif algo == "Decimal":
        values = [int(token, 10) for token in string_data.split()]
        if any(value < 0 or value > 255 for value in values):
            raise ValueError("Decimal byte values must be 0..255")
        return bytes(values)

    # ----------------------------------
    # Text transforms
    # ----------------------------------

    elif algo == "Reverse":
        return raw[::-1] if isinstance(text, bytes) else string_data[::-1].encode("utf-8")

    elif algo.startswith("ROT"):
        result = rot_n(string_data, *parse_rot_algo(algo))
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
