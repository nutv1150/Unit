import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Tools.artifact_bridge import (
    resolve_file_input,
    remove_temp_artifact,
)


def main():

    print("=" * 65)
    print("UNIT P0.3 - PIPELINE ARTIFACT COMPATIBILITY")
    print("=" * 65)

    failed = 0

    # =====================================================
    # TEST 1
    # ไม่มี previous output
    # ต้องให้ user browse เองเหมือนเดิม
    # =====================================================

    result = resolve_file_input(b"")

    if result["mode"] == "manual":
        print("[PASS] Empty input -> manual file selection")
    else:
        failed += 1
        print("[FAIL] Empty input:", result)

    # =====================================================
    # TEST 2
    # Text output ไม่ควรถูกสร้าง temp artifact
    # =====================================================

    result = resolve_file_input(
        b"hello from strings output"
    )

    if result["mode"] == "manual":
        print("[PASS] Text output -> no artifact")
    else:
        failed += 1
        print("[FAIL] Text output:", result)

    # =====================================================
    # TEST 3
    # Existing path ต้องใช้ไฟล์เดิม
    # =====================================================

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".txt"
    ) as f:
        f.write(b"UNIT TEST")
        real_path = f.name

    try:

        result = resolve_file_input(
            real_path.encode()
        )

        if (
            result["mode"] == "existing_path"
            and result["path"] == real_path
        ):
            print("[PASS] Existing path preserved")
        else:
            failed += 1
            print("[FAIL] Existing path:", result)

    finally:
        os.remove(real_path)

    # =====================================================
    # TEST 4
    # Binary 7z -> artifact
    # =====================================================

    fake_7z = (
        b"\x37\x7A\xBC\xAF\x27\x1C"
        + b"\x00" * 100
    )

    result = resolve_file_input(fake_7z)

    if (
        result["mode"] == "artifact"
        and result["extension"] == ".7z"
        and os.path.exists(result["path"])
    ):
        print("[PASS] Binary -> 7z artifact")

        remove_temp_artifact(
            result["path"]
        )

    else:
        failed += 1
        print("[FAIL] Binary artifact:", result)

    print("=" * 65)

    if failed:
        raise SystemExit(
            f"{failed} TEST(S) FAILED"
        )

    print("ALL PIPELINE COMPATIBILITY TESTS PASSED")


if __name__ == "__main__":
    main()