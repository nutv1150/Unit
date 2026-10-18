"""Shared ROT transforms; encode and decode both apply a forward shift."""


# หน้าที่: หมุนอักขระตามจำนวนตำแหน่งในชุดตัวอักษรหรือ printable ASCII
# ที่มา: Decode/base_decoder.py::auto_detect_decode.iter_rot_candidates (เรียกตรง)
# ที่มา: Decode/base_decoder.py::decode_to_bytes (เรียกตรง)
# ที่มา: Encode/base_encoder.py::encode_data (เรียกตรง)
# Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: n (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: mode (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def rot_n(text, n=13, mode="alpha"):
    if mode not in ("alpha", "ascii"):
        raise ValueError("ROT mode must be alpha or ascii")
    if not isinstance(n, int):
        raise ValueError("ROT n must be an integer")
    result = []
    for c in text:
        value = ord(c)
        if mode == "ascii" and 33 <= value <= 126:
            c = chr(33 + (value - 33 + n) % 94)
        elif mode == "alpha":
            if "A" <= c <= "Z":
                c = chr(65 + (value - 65 + n) % 26)
            elif "a" <= c <= "z":
                c = chr(97 + (value - 97 + n) % 26)
        result.append(c)
    return "".join(result)


# หน้าที่: แยกชื่อ ROT เป็นจำนวนตำแหน่งและชนิด alphabet
# ที่มา: Decode/base_decoder.py::decode_to_bytes (เรียกตรง)
# ที่มา: Encode/base_encoder.py::encode_data (เรียกตรง)
# Input: algo (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def parse_rot_algo(algo):
    if algo in ("ROT", "ROT13"):
        return 13, "alpha"
    parts = algo.split(":")
    if len(parts) not in (2, 3) or parts[0] != "ROT":
        raise ValueError("Use ROT:n or ROT:n:alpha/ascii")
    try:
        n = int(parts[1])
    except ValueError:
        raise ValueError("ROT n must be an integer") from None
    mode = parts[2] if len(parts) == 3 else "alpha"
    if mode not in ("alpha", "ascii"):
        raise ValueError("ROT mode must be alpha or ascii")
    limit = 25 if mode == "alpha" else 93
    if not 1 <= n <= limit:
        raise ValueError(f"ROT n must be 1–{limit} for {mode}")
    return n, mode
