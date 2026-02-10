import base64

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def decode_data(text, algo="Base64"):
    if algo == "Base64":
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
