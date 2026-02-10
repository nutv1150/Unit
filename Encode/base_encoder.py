import base64


BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def encode_data(text, algo="Base64"):
    raw = text.encode()

    if algo == "Base64":
        return base64.b64encode(raw).decode()

    elif algo == "Base32":
        return base64.b32encode(raw).decode()

    elif algo == "Base85":
        return base64.b85encode(raw).decode()

    elif algo == "Hex":
        return raw.hex()

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

    return text


def encode_base_n(data, alphabet):
    num = int.from_bytes(data, "big")
    base = len(alphabet)

    encoded = ""
    while num:
        num, rem = divmod(num, base)
        encoded = alphabet[rem] + encoded

    return encoded or alphabet[0]
