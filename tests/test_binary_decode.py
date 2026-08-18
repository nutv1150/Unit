import sys
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Decode.base_decoder import (
    decode_to_bytes,
    detect_magic_bytes,
    describe_decoded_data,
)


def main():

    print("=" * 60)
    print("UNIT P0.2 - BINARY SAFE DECODE TEST")
    print("=" * 60)

    failed = 0

    # ======================================================
    # TEST 1 - Normal text Base64
    # ======================================================

    encoded = base64.b64encode(
        b"hello UNIT"
    ).decode()

    result = decode_to_bytes(
        encoded,
        "Base64"
    )

    if result == b"hello UNIT":
        print("[PASS] Base64 -> text bytes")
    else:
        failed += 1
        print("[FAIL] Base64 text:", result)

    # ======================================================
    # TEST 2 - ZIP binary
    # ======================================================

    fake_zip = (
        b"PK\x03\x04"
        + b"\x00" * 100
    )

    encoded_zip = base64.b64encode(
        fake_zip
    ).decode()

    result = decode_to_bytes(
        encoded_zip,
        "Base64"
    )

    magic = detect_magic_bytes(result)

    if (
        result == fake_zip
        and magic
        and magic["type"] == "ZIP Archive"
    ):
        print("[PASS] Base64 -> ZIP binary")
        print("       magic:", magic)
    else:
        failed += 1
        print("[FAIL] ZIP binary")

    # ======================================================
    # TEST 3 - 7ZIP binary
    # ======================================================

    fake_7z = (
        b"\x37\x7A\xBC\xAF\x27\x1C"
        + b"\x00" * 100
    )

    encoded_7z = base64.b64encode(
        fake_7z
    ).decode()

    result = decode_to_bytes(
        encoded_7z,
        "Base64"
    )

    magic = detect_magic_bytes(result)

    if magic and magic["type"] == "7-Zip Archive":
        print("[PASS] Base64 -> 7-Zip binary")
        print(
            "       magic:",
            magic["magic"]
        )
    else:
        failed += 1
        print("[FAIL] 7-Zip magic")

    # ======================================================
    # TEST 4 - Binary description
    # ======================================================

    info = describe_decoded_data(fake_7z)

    if (
        info["magic"]
        and info["magic"]["extension"] == ".7z"
    ):
        print("[PASS] Binary artifact description")
    else:
        failed += 1
        print("[FAIL] Binary description")

    # ======================================================
    # TEST 5 - Reverse
    # ======================================================

    data = "FEDCBA"

    result = decode_to_bytes(
        data,
        "Reverse"
    )

    if result == b"ABCDEF":
        print("[PASS] Reverse -> bytes")
    else:
        failed += 1
        print("[FAIL] Reverse:", result)

    print("=" * 60)

    if failed:
        raise SystemExit(
            f"{failed} TEST(S) FAILED"
        )

    print("ALL BINARY DECODE TESTS PASSED")


if __name__ == "__main__":
    main()