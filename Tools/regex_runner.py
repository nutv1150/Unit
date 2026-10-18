"""Run user-provided regex outside Tk's process with bounded time/results."""
import json
from pathlib import Path
import re
import subprocess
import sys


# หน้าที่: เรียก regex worker แยก process พร้อม timeout และเพดานจำนวน matches
# ที่มา: Tools/package_smoke.py::main (เรียกตรง)
# ที่มา: pages/file_inspection.py::FileInspectionPage.extract_all_strings (เรียกตรง)
# Input: pattern (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: timeout (float | int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: max_matches (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def find_match_spans(pattern, text, timeout=2, max_matches=10000):
    request = json.dumps({'pattern': pattern, 'text': text, 'max_matches': max_matches})
    command = ([sys.executable, '--unit-regex-worker'] if getattr(sys, 'frozen', False)
               else [sys.executable, '-I', str(Path(__file__).resolve())])
    try:
        result = subprocess.run(
            command,
            input=request.encode('utf-8'), capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(f'Regex exceeded {timeout:g}s; simplify the pattern or reduce input') from error
    if result.returncode != 0:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip() or 'Regex worker failed')
    return json.loads(result.stdout)


# หน้าที่: อ่านคำขอ JSON จาก stdin แล้วคืนตำแหน่ง regex matches ทาง stdout
# ที่มา: Tools/regex_runner.py::<module> (เรียกตรง)
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: sys.stdin (text stream) มี JSON object: pattern/text (str), max_matches (int)
def main():
    try:
        request = json.load(sys.stdin)
        matches = []
        for match in re.finditer(request['pattern'], request['text'], re.IGNORECASE):
            if len(matches) >= request['max_matches']:
                raise ValueError('Regex exceeded match limit; narrow the pattern or reduce input')
            matches.append(match.span())
        print(json.dumps(matches))
    except (ValueError, KeyError, TypeError, re.error) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
