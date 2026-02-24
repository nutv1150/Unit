import base64

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE45 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def is_printable(text):
    return all(32 <= ord(c) <= 126 or c in "\n\r\t" for c in text)


def auto_detect_decode(data):
    candidates = [
        ("Base64", lambda d: base64.b64decode(d)),
        ("Base32", lambda d: base64.b32decode(d)),
        ("Base45", lambda d: decode_base45(d.decode()).encode()),
        ("Base85", lambda d: base64.b85decode(d)),
        ("Base16", lambda d: base64.b16decode(d)),
        ("Hex", lambda d: bytes.fromhex(d.decode())),
        ("Base58", lambda d: decode_base_n(d.decode(), BASE58).encode()),
        ("Base62", lambda d: decode_base_n(d.decode(), BASE62).encode()),  # ✅ เพิ่มตรงนี้
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

    return text


def decode_base_n(text, alphabet):
    base = len(alphabet)
    num = 0

    for char in text:
        num = num * base + alphabet.index(char)

    return num.to_bytes((num.bit_length() + 7) // 8, "big").decode(errors="ignore")


# =========================
# Base45 Decoder
# =========================
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