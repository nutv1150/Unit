import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Decode.base_decoder import (
    decode_to_bytes,
    detect_magic_bytes,
    describe_decoded_data,
)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            ".venv/bin/python tests/test_hidden_data_real.py "
            "/home/nutvv/Documents/GitHub/Unit/hidden.txt"
        )
        raise SystemExit(1)

    challenge_path = Path(sys.argv[1])

    if not challenge_path.exists():
        raise SystemExit(
            f"[ERROR] File not found: {challenge_path}"
        )

    print("=" * 65)
    print("UNIT REAL CTF BENCHMARK")
    print("Challenge: Hidden Data - TCTT2026")
    print("=" * 65)

    # ---------------------------------------------------------
    # STEP 1
    # อ่านแบบ utf-8-sig เพื่อตัด UTF-8 BOM อัตโนมัติ
    # ---------------------------------------------------------

    raw_text = challenge_path.read_text(
        encoding="utf-8-sig"
    ).strip()

    print(
        f"[+] Input text size: {len(raw_text):,} chars"
    )

    # ---------------------------------------------------------
    # STEP 2
    # Reverse
    # ---------------------------------------------------------

    raw_bytes = challenge_path.read_bytes()

    print(f"[+] Input file : {challenge_path.name}")
    print(f"[+] Input size : {len(raw_bytes):,} bytes")

    # ตัด UTF-8 BOM ถ้ามี
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raw_bytes = raw_bytes[3:]

    try:
        raw_text = raw_bytes.decode("utf-8").strip()

    except UnicodeDecodeError:
        print("[FAIL] This challenge expects TEXT input,")
        print("       but the selected file contains binary data.")

        print(
            "[HEX] First 32 bytes:",
            " ".join(f"{b:02X}" for b in raw_bytes[:32])
        )

        print()
        print("[HINT]")
        print("Hidden Data benchmark expects:")
        print("Challenge_Hidden_Data.txt")
        print()
        print("The selected file can still be used later")
        print("to test UNIT binary/file inspection workflows.")

        raise SystemExit(1)


    if len(raw_text) < 1000:
        print(
            f"[FAIL] Input text is suspiciously small: "
            f"{len(raw_text):,} chars"
        )

        print(
            "[HINT] Make sure this is the original "
            "Challenge_Hidden_Data.txt"
        )

        raise SystemExit(1)


    print(
        f"[PASS] Valid UTF-8 text input: "
        f"{len(raw_text):,} chars"
    )

    # ---------------------------------------------------------
    # STEP 3
    # Base64
    # ---------------------------------------------------------

    decoded = decode_to_bytes(
        reversed_bytes,
        "Base64"
    )

    print(
        f"[PASS] Base64 Decode -> {len(decoded):,} bytes"
    )

    # ---------------------------------------------------------
    # STEP 4
    # Magic detection
    # ---------------------------------------------------------

    magic = detect_magic_bytes(decoded)

    if not magic:
        print("[FAIL] Unknown binary format")
        print(
            "First 32 bytes:",
            decoded[:32].hex(" ")
        )
        raise SystemExit(1)

    print(
        f"[PASS] Magic detected: {magic['type']}"
    )

    print(
        f"       magic     = {magic['magic']}"
    )

    print(
        f"       extension = {magic['extension']}"
    )

    # ---------------------------------------------------------
    # EXPECTED REAL CHALLENGE RESULT
    # ---------------------------------------------------------

    if magic["type"] != "7-Zip Archive":
        raise SystemExit(
            f"[FAIL] Expected 7-Zip, got {magic['type']}"
        )

    if not decoded.startswith(
        b"\x37\x7A\xBC\xAF\x27\x1C"
    ):
        raise SystemExit(
            "[FAIL] Invalid 7-Zip signature"
        )

    # ---------------------------------------------------------
    # Artifact information
    # ---------------------------------------------------------

    info = describe_decoded_data(decoded)

    print("-" * 65)

    print("[ARTIFACT]")
    print(f"Type : {magic['type']}")
    print(f"Size : {info['size']:,} bytes")

    if info["hex_preview"]:
        print(
            f"HEX  : {info['hex_preview'][:100]} ..."
        )

    # ---------------------------------------------------------
    # Save layer 1
    # ---------------------------------------------------------

    artifact_dir = ROOT / "tests" / "artifacts"
    artifact_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output = (
        artifact_dir /
        "hidden_data_layer1.7z"
    )

    output.write_bytes(decoded)

    print(
        f"[PASS] Artifact saved: {output}"
    )

    print("=" * 65)
    print(
        "REAL HIDDEN DATA LAYER-1 TEST PASSED"
    )
    print("=" * 65)


if __name__ == "__main__":
    main()