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


def _to_text(data: Union[str, bytes]) -> str:
    """Convert supported input to searchable text."""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="ignore")

    return str(data)


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


def find_first_flag(data: Union[str, bytes]):
    """Return first detected flag, otherwise None."""
    flags = find_flags(data)

    return flags[0] if flags else None