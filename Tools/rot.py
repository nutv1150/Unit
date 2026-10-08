"""Shared ROT transforms; encode and decode both apply a forward shift."""


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
