import os
import tempfile

from Decode.base_decoder import detect_magic_bytes
from Decode.base_decoder import is_probably_text


def create_temp_artifact(data: bytes) -> dict:
    """
    Convert binary pipeline output into a temporary file.

    Returns:
    {
        "path": "/tmp/unit_xxxxx.zip",
        "type": "ZIP Archive",
        "extension": ".zip",
        "size": 1234
    }
    """

    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("Artifact data must be bytes")

    data = bytes(data)

    magic = detect_magic_bytes(data)

    if magic:
        extension = magic.get("extension", ".bin")
        file_type = magic.get("type", "Binary Data")
    else:
        extension = ".bin"
        file_type = "Unknown Binary"

    tmp = tempfile.NamedTemporaryFile(
        prefix="unit_",
        suffix=extension,
        delete=False
    )

    try:
        tmp.write(data)
        tmp.flush()
    finally:
        tmp.close()

    return {
        "path": tmp.name,
        "type": file_type,
        "extension": extension,
        "size": len(data),
        "magic": magic,
    }


def remove_temp_artifact(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass

def resolve_file_input(data):
    """
    ตัดสินใจว่า previous pipeline output ควรถูกส่งเข้า file tool แบบไหน

    return:
        {
            "mode": "existing_path" | "artifact" | "manual",
            "path": str | None,
            ...
        }
    """

    if data is None or data == b"" or data == "":
        return {
            "mode": "manual",
            "path": None,
            "reason": "No previous output"
        }

    # =====================================================
    # 1. เช็กก่อนว่า previous output คือ path จริงหรือไม่
    # =====================================================

    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = None
    else:
        text = str(data).strip()

    if text:
        # รองรับ output แบบ:
        # /tmp/file.zip
        # "/tmp/file.zip"
        # '/tmp/file.zip'

        possible_path = text.strip("\"'")

        if os.path.isfile(possible_path):
            return {
                "mode": "existing_path",
                "path": possible_path,
                "reason": "Previous output is an existing file path"
            }

    # =====================================================
    # 2. แปลงเป็น bytes
    # =====================================================

    if isinstance(data, bytes):
        raw = data

    elif isinstance(data, bytearray):
        raw = bytes(data)

    else:
        raw = str(data).encode("utf-8")

    # =====================================================
    # 3. ถ้าเป็น text ปกติ ไม่สร้าง artifact อัตโนมัติ
    #
    # เพื่อรักษา behavior เดิม และป้องกัน UNIT สร้าง
    # temp file จาก stdout / grep / strings โดยไม่จำเป็น
    # =====================================================

    if is_probably_text(raw):
        return {
            "mode": "manual",
            "path": None,
            "reason": "Previous output is text, not a file path"
        }

    # =====================================================
    # 4. Binary -> Artifact Bridge
    # =====================================================

    artifact = create_temp_artifact(raw)

    return {
        "mode": "artifact",
        **artifact
    }