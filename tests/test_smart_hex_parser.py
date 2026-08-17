import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Tools.extra_tools import (
    _parse_input_bytes,
    detect_embedded_key,
    bitwise_mask,
)


CIPHER_HEX = (
    "2c 26 2b 2d 31 3a 25 3d "
    "2f 38 39 22 2f 26 26 15 "
    "32 25 38 15 22 23 2e 2e "
    "2f 24 15 39 25 15 2f 2b "
    "39 33 37"
)

EXPECTED = b"flag{powershell_xor_hidden_so_easy}"


def check(label, text, expected=EXPECTED):

    data, fmt = _parse_input_bytes(text)

    if data != expected:
        raise AssertionError(
            f"{label}: wrong bytes\n"
            f"format={fmt}\n"
            f"got={data!r}"
        )

    print(
        f"[PASS] {label:<28} "
        f"-> {fmt}"
    )


def main():

    print("=" * 70)
    print("UNIT P0.4A - SMART HEX / CTF INPUT PARSER")
    print("=" * 70)

    # -----------------------------------------------------
    # Plain hex
    # -----------------------------------------------------

    cipher, fmt = _parse_input_bytes(
        CIPHER_HEX
    )

    result = bytes(
        b ^ 0x4A
        for b in cipher
    )

    if result != EXPECTED:
        raise AssertionError(
            "Plain hex XOR failed"
        )

    print(
        "[PASS] plain hex -> "
        "flag{powershell_xor_hidden_so_easy}"
    )

    # -----------------------------------------------------
    # 0x list
    # -----------------------------------------------------

    tokens = CIPHER_HEX.split()

    ox = ",".join(
        "0x" + x
        for x in tokens
    )

    data, fmt = _parse_input_bytes(ox)

    assert (
        bytes(x ^ 0x4A for x in data)
        == EXPECTED
    )

    print(
        "[PASS] 0x byte array"
    )

    # -----------------------------------------------------
    # PowerShell
    # -----------------------------------------------------

    powershell = (
        "$key = 0x4A\n"
        "$data = @("
        + ox
        + ")\n"
        "$decoded = $data | "
        "ForEach-Object { "
        "[char]($_ -bxor $key) }"
    )

    data, fmt = _parse_input_bytes(
        powershell
    )

    decoded = bytes(
        x ^ 0x4A
        for x in data
    )

    if decoded != EXPECTED:
        raise AssertionError(
            "PowerShell parser failed"
        )

    print(
        "[PASS] PowerShell hex array"
    )

    # -----------------------------------------------------
    # Must NOT include $key byte
    # -----------------------------------------------------

    if data[0] != 0x2C:
        raise AssertionError(
            "Parser accidentally included "
            "$key value in ciphertext"
        )

    print(
        "[PASS] PowerShell key excluded "
        "from ciphertext"
    )

    # -----------------------------------------------------
    # Embedded key detection
    # -----------------------------------------------------

    key = detect_embedded_key(
        powershell
    )

    if not key:
        raise AssertionError(
            "Embedded key not detected"
        )

    if key["key"].lower() != "0x4a":
        raise AssertionError(
            f"Wrong key: {key}"
        )

    print(
        "[PASS] Embedded key detected: "
        f"{key['key']}"
    )

    # -----------------------------------------------------
    # Full real-style snippet through bitwise_mask()
    # -----------------------------------------------------

    output = bitwise_mask(
        powershell,
        key["key"],
        "xor"
    )

    if (
        "flag{powershell_xor_hidden_so_easy}"
        not in output
    ):
        raise AssertionError(
            "End-to-end XOR failed"
        )

    print(
        "[PASS] PowerShell snippet -> XOR "
        "-> FLAG"
    )

    # -----------------------------------------------------
    # Escaped hex
    # -----------------------------------------------------

    escaped = "".join(
        "\\x" + x
        for x in tokens
    )

    data, fmt = _parse_input_bytes(
        escaped
    )

    assert (
        bytes(x ^ 0x4A for x in data)
        == EXPECTED
    )

    print(
        "[PASS] escaped \\\\xNN format"
    )

    # -----------------------------------------------------
    # Raw text regression
    # -----------------------------------------------------

    raw, fmt = _parse_input_bytes(
        "hello world"
    )

    assert raw == b"hello world"
    assert fmt == "raw"

    print(
        "[PASS] normal ASCII remains raw"
    )

    print("=" * 70)
    print(
        "ALL P0.4A SMART HEX TESTS PASSED"
    )


if __name__ == "__main__":
    main()