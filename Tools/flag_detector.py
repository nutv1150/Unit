import re
from typing import List, Union


# ============================================================
# Universal wrapped-flag detector
#
# รองรับตัวอย่าง:
# flag{...}
# CTF{...}
# picoCTF{...}
# HTB{...}
# THCTT{...}
# TCTT2026{...}
# IT_MSU_ANNIV25{...}
#
# จงใจไม่ match CSS/JS ทั่วไป เช่น body{color:red}
# ============================================================

UNIVERSAL_FLAG_REGEX = (
    r"(?i)\b(?:"
    r"flag|"
    r"ctf|"
    r"htb|"
    r"picoctf|"
    r"thctt|"
    r"tctt\d*|"
    r"it_msu_anniv\d*|"
    r"[a-z0-9_]*(?:ctf|flag|tctt|thctt|msu|anniv)[a-z0-9_]*"
    r")\{[^{}\r\n]{1,256}\}"
)


_FLAG_RE = re.compile(UNIVERSAL_FLAG_REGEX)


# หน้าที่: แปลง str หรือ bytes เป็นข้อความสำหรับค้นหารูปแบบ flag
# ที่มา: Tools/flag_detector.py::find_flags (เรียกตรง)
# Input: data (Union[str, bytes]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def _to_text(data: Union[str, bytes]) -> str:
    """Convert supported input to searchable text."""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="ignore")

    return str(data)


# หน้าที่: รวบรวม flag ที่ตรง pattern และตัดรายการซ้ำ
# ที่มา: Decode/base_decoder.py::auto_detect_decode (เรียกตรง)
# ที่มา: Tools/flag_detector.py::find_first_flag (เรียกตรง)
# ที่มา: pages/data_hash.py::DataHashPage._show_result (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: data (Union[str, bytes]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def find_flags(data: Union[str, bytes]) -> List[str]:
    """
    Find all wrapped CTF flags.

    Returns unique flags while preserving discovery order.
    """
    text = _to_text(data)

    results = []
    seen = set()

    for match in _FLAG_RE.finditer(text):
        flag = match.group(0)

        if flag not in seen:
            seen.add(flag)
            results.append(flag)

    return results


# หน้าที่: คืน flag แรกที่ตรวจพบหรือ None เมื่อไม่พบ
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.check_flag (เรียกตรง)
# ที่มา: Tools/extra_tools.py::_flag_hint (เรียกตรง)
# Input: data (Union[str, bytes]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def find_first_flag(data: Union[str, bytes]):
    """Return first detected flag, otherwise None."""
    flags = find_flags(data)

    return flags[0] if flags else None
