import base64
import urllib.parse
import html

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE45 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def encode_data(text, algo="Base64"):
    raw = text.encode()

    if algo == "Base64":
        return base64.b64encode(raw).decode()

    elif algo == "Base32":
        return base64.b32encode(raw).decode()

    elif algo == "Base85":
        return base64.b85encode(raw).decode()

    elif algo in ("Hex", "Base16"):
        return base64.b16encode(raw).decode()

    elif algo == "Base45":
        return encode_base45(raw)

    elif algo == "Binary":
        return " ".join(format(b, "08b") for b in raw)

    elif algo == "Octal":
        return " ".join(format(b, "03o") for b in raw)

    elif algo == "Decimal":
        return " ".join(str(b) for b in raw)

    elif algo == "Base58":
        return encode_base_n(raw, BASE58)

    elif algo == "Base62":
        return encode_base_n(raw, BASE62)

    # =========================
    # NEW Encoding
    # =========================

    elif algo == "URL Encode":
        return urllib.parse.quote(text)

    elif algo == "URL-safe Base64":
        return base64.urlsafe_b64encode(raw).decode()

    elif algo == "HTML Entity":
        return html.escape(text)

    elif algo == "Unicode Escape":
        return text.encode("unicode_escape").decode()

    return text


def encode_base_n(data, alphabet):
    num = int.from_bytes(data, "big")
    base = len(alphabet)

    encoded = ""
    while num:
        num, rem = divmod(num, base)
        encoded = alphabet[rem] + encoded

    return encoded or alphabet[0]


# =========================
# Base45 Encoder
# =========================
def encode_base45(data: bytes) -> str:
    result = ""
    i = 0

    while i < len(data):
        if i + 1 < len(data):
            x = data[i] * 256 + data[i + 1]
            e = x // (45 * 45)
            d = (x // 45) % 45
            c = x % 45
            result += BASE45[c] + BASE45[d] + BASE45[e]
            i += 2
        else:
            x = data[i]
            d = x // 45
            c = x % 45
            result += BASE45[c] + BASE45[d]
            i += 1

    return result