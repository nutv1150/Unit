import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Tools.flag_detector import find_flags, find_first_flag


def test_flag_detector():

    positive_cases = [
        "flag{hello_world}",
        "FLAG{HELLO}",
        "CTF{test}",
        "picoCTF{test_flag}",
        "HTB{owned}",
        "THCTT{hello}",
        "TCTT2026{poisoned_package_exfil_c2_tunnel}",
        "IT_MSU_ANNIV25{i_am_password}",
    ]

    negative_cases = [
        "body{color:red}",
        "html{background:black}",
        "abc{hello}",
        "function test() { return true; }",
        "no flag here",
    ]

    print("=" * 60)
    print("UNIT P0.1 - UNIVERSAL FLAG DETECTOR")
    print("=" * 60)

    failed = 0

    for value in positive_cases:
        result = find_first_flag(value)

        if result == value:
            print(f"[PASS] {value}")
        else:
            failed += 1
            print(f"[FAIL] {value}")
            print(f"       result = {result}")

    for value in negative_cases:
        result = find_first_flag(value)

        if result is None:
            print(f"[PASS] rejected: {value}")
        else:
            failed += 1
            print(f"[FAIL] false positive: {value}")
            print(f"       result = {result}")

    # Bytes test
    raw = (
        b"random binary\x00\x01 "
        b"TCTT2026{real_binary_flag} "
        b"more data"
    )

    flags = find_flags(raw)

    if flags == ["TCTT2026{real_binary_flag}"]:
        print("[PASS] binary bytes input")
    else:
        failed += 1
        print("[FAIL] binary bytes input:", flags)

    print("=" * 60)

    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        raise SystemExit(f"{failed} TEST(S) FAILED")


if __name__ == "__main__":
    test_flag_detector()
