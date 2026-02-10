import base64

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def is_printable(text):
    return all(32 <= ord(c) <= 126 or c in "\n\r\t" for c in text)

def auto_detect_decode(data):
    candidates = [
        ("Base64", lambda d: base64.b64decode(d)),
        ("Base32", lambda d: base64.b32decode(d)),
        ("Base85", lambda d: base64.b85decode(d)),
        ("Hex", lambda d: bytes.fromhex(d.decode())),
        ("Binary", lambda d: bytes(int(x, 2) for x in d.decode().split())),
        ("Octal", lambda d: bytes(int(x, 8) for x in d.decode().split())),
        ("Decimal", lambda d: bytes(int(x) for x in d.decode().split())),
    ]

    for name, func in candidates:
        try:
            decoded = func(data)
            decoded_text = decoded.decode(errors="ignore")

            if decoded_text and is_printable(decoded_text):
                return name, decoded_text

        except Exception:
            pass

    return "Unknown", "Decode failed"

def decode_data(text, algo="Base64"):
    if algo == "Auto Detect":
        name, result = auto_detect_decode(text.encode())
        return result
    
    elif algo == "Base64":
        return base64.b64decode(text).decode(errors="ignore")

    elif algo == "Base32":
        return base64.b32decode(text).decode(errors="ignore")

    elif algo == "Base85":
        return base64.b85decode(text).decode(errors="ignore")

    elif algo == "Hex":
        return bytes.fromhex(text).decode(errors="ignore")

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

    return text


def decode_base_n(text, alphabet):
    base = len(alphabet)
    num = 0

    for char in text:
        num = num * base + alphabet.index(char)

    return num.to_bytes((num.bit_length() + 7) // 8, "big").decode(errors="ignore")
