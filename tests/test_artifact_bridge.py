import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Tools.artifact_bridge import (
    create_temp_artifact,
    remove_temp_artifact,
)


def main():
    print("=" * 60)
    print("UNIT P0.3 - ARTIFACT BRIDGE")
    print("=" * 60)

    failed = 0

    # fake 7z binary
    data = (
        b"\x37\x7A\xBC\xAF\x27\x1C"
        + b"\x00" * 100
    )

    artifact = create_temp_artifact(data)

    print("[INFO]", artifact)

    path = artifact["path"]

    if os.path.exists(path):
        print("[PASS] Temporary artifact created")
    else:
        failed += 1
        print("[FAIL] Artifact was not created")

    if Path(path).suffix == ".7z":
        print("[PASS] Extension detected: .7z")
    else:
        failed += 1
        print("[FAIL] Wrong extension:", Path(path).suffix)

    if Path(path).read_bytes() == data:
        print("[PASS] Binary content preserved")
    else:
        failed += 1
        print("[FAIL] Binary content corrupted")

    if artifact["type"] == "7-Zip Archive":
        print("[PASS] Type detected: 7-Zip Archive")
    else:
        failed += 1
        print("[FAIL] Wrong type:", artifact["type"])

    remove_temp_artifact(path)

    if not os.path.exists(path):
        print("[PASS] Temporary artifact cleaned")
    else:
        failed += 1
        print("[FAIL] Artifact cleanup failed")

    print("=" * 60)

    if failed:
        raise SystemExit(f"{failed} TEST(S) FAILED")

    print("ALL ARTIFACT BRIDGE TESTS PASSED")


if __name__ == "__main__":
    main()
