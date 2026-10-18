"""Persistent user groups and challenge timers, independent of Tk."""
import json
import math
import os
import time
import uuid
from copy import deepcopy
from pathlib import Path

from Tools.app_paths import writable_path

CONFIG_DIR = writable_path('config')


# หน้าที่: อ่านรายการ records จาก JSON และตรวจ ID ว่าครบและไม่ซ้ำ
# ที่มา: Tools/workspace_store.py::ChallengeStore.__init__ (เรียกตรง)
# ที่มา: pages/my_tools.py::MyToolsPage.__init__ (เรียกตรง)
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def load_records(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
        raise ValueError('Config must contain a list of records')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Config has missing or duplicate IDs')
    return rows


# หน้าที่: เขียนรายการ records เป็น JSON ผ่านไฟล์ชั่วคราวแล้วแทนที่ไฟล์จริง
# ที่มา: Tools/workspace_store.py::ChallengeStore.commit (เรียกตรง)
# ที่มา: pages/my_tools.py::MyToolsPage._commit (เรียกตรง)
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
# Input: rows (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def save_records(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)


# หน้าที่: ตรวจชื่อและเครื่องมือแล้วสร้าง group record พร้อม ID และสำเนารายการ tools
# ที่มา: pages/my_tools.py::MyToolsPage._open_dialog.save (เรียกตรง)
# ที่มา: pages/my_tools.py::MyToolsPage.__init__ (เรียกตรง)
# Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: tools (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: group_id (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def make_group(name, tools, group_id=None):
    name = name.strip()
    if not name:
        raise ValueError('Enter a group name')
    if not tools:
        raise ValueError('Select at least one tool')
    return dict(id=group_id or uuid.uuid4().hex, name=name,
                category_color=tools[0].get('color', 'purple'), tools=deepcopy(tools))


# หน้าที่: ตรวจค่าจำนวนเต็ม ASCII และค่าต่ำสุดก่อนแปลงเป็น int
# ที่มา: Tools/workspace_store.py::ChallengeStore.update (เรียกตรง)
# ที่มา: Tools/workspace_store.py::ChallengeStore.__init__ (เรียกตรง)
# ที่มา: Tools/workspace_store.py::ChallengeStore.create (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: value (str | int (ตรวจค่าและปฏิเสธ bool)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: minimum (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: label (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def integer(value, minimum, label):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError(f'{label} must be an integer of at least {minimum}')
    number = int(value)
    if number < minimum:
        raise ValueError(f'{label} must be an integer of at least {minimum}')
    return number


# หน้าที่: คำนวณเวลารวมจากเวลาสะสมและ timestamp ที่เริ่มจับเวลาล่าสุด
# ที่มา: Tools/workspace_store.py::ChallengeStore.update (เรียกตรง)
# ที่มา: Tools/workspace_store.py::ChallengeStore.pause_all (เรียกตรง)
# ที่มา: pages/challenge.py::ChallengePage._time_text (เรียกตรง)
# Input: record (dict[str, Any]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: now (float | int | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def elapsed(record, now=None):
    now = time.time() if now is None else now
    total = record['elapsed_seconds']
    if record['is_running']:
        total += max(0, now - record['resume_timestamp'])
    return total


# หน้าที่: จัดวินาทีเป็นข้อความ HH:MM:SS
# ที่มา: pages/challenge.py::ChallengePage._time_text (เรียกตรง)
# Input: seconds (float | int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def format_elapsed(seconds):
    seconds = max(0, int(seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


class ChallengeStore:
    # หน้าที่: โหลด Challenge records และตรวจคะแนน เวลา และสถานะ timer
    # ที่มา: pages/challenge.py::ChallengePage.__init__ (เรียกตรง)
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    # Input: clock (Callable[[], float]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def __init__(self, path=None, clock=time.time):
        self.path = Path(path) if path is not None else CONFIG_DIR / 'challenges.json'
        self.clock = clock
        self.rows = load_records(self.path)
        for row in self.rows:
            if not isinstance(row.get('name'), str) or not row['name'].strip():
                raise ValueError('Invalid challenge name')
            total = integer(row.get('total_items'), 1, 'Total items')
            if integer(row.get('solved_items'), 0, 'Solved') > total:
                raise ValueError('Solved exceeds total')
            if not isinstance(row.get('is_running'), bool):
                raise ValueError('Invalid timer status')
            for key in ('elapsed_seconds', 'resume_timestamp'):
                value = row.get(key)
                if key == 'resume_timestamp' and value is None and not row['is_running']:
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError('Invalid timer value')

    # หน้าที่: บันทึก Challenge records และอัปเดตสำเนาในหน่วยความจำ
    # ที่มา: Tools/solve_history.py::SolveHistoryStore.begin (เรียกตรง)
    # ที่มา: Tools/solve_history.py::SolveHistoryStore.finish (เรียกตรง)
    # ที่มา: Tools/solve_history.py::SolveHistoryStore.clear (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 4 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: rows (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def commit(self, rows):
        save_records(self.path, rows)
        self.rows = rows

    # หน้าที่: สร้าง Challenge ใหม่พร้อมคะแนนเริ่มต้นและ timer ที่หยุดอยู่
    # ที่มา: pages/challenge.py::ChallengePage._create (เรียกตรง)
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: total (str | int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def create(self, name, total):
        if not name.strip():
            raise ValueError('Enter a competition name')
        record = dict(id=uuid.uuid4().hex, name=name.strip(), total_items=integer(total, 1, 'Total items'),
                      solved_items=0, elapsed_seconds=0, resume_timestamp=None, is_running=False)
        self.commit(self.rows + [record])
        return record['id']

    # หน้าที่: ค้นหา Challenge record ตาม ID
    # ที่มา: pages/challenge.py::ChallengePage._open_editor (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._open_editor.toggle (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._delete (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: record_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def get(self, record_id):
        return next(row for row in self.rows if row['id'] == record_id)

    # หน้าที่: ตรวจคะแนน อัปเดต timer และบันทึก record ที่แก้ไข
    # ที่มา: pages/challenge.py::ChallengePage._open_editor.toggle (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._open_editor.save (เรียกตรง)
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: record_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: solved (str | int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: running (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def update(self, record_id, solved, running):
        rows = deepcopy(self.rows)
        row = next(r for r in rows if r['id'] == record_id)
        solved = integer(solved, 0, 'Solved')
        if solved > row['total_items']:
            raise ValueError('Solved must not exceed Total items')
        now = self.clock()
        row.update(elapsed_seconds=elapsed(row, now), resume_timestamp=now if running else None,
                   is_running=bool(running), solved_items=solved)
        self.commit(rows)

    # หน้าที่: ลบ Challenge ที่มี ID ตรงกันแล้วบันทึกรายการที่เหลือ
    # ที่มา: pages/challenge.py::ChallengePage._delete.remove (เรียกตรง)
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: record_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def delete(self, record_id):
        self.commit([r for r in self.rows if r['id'] != record_id])

    # หน้าที่: หยุด timers ทุกตัวและบันทึกเวลาสะสมก่อนปิดแอป
    # ที่มา: pages/challenge.py::ChallengePage.save_before_close (เรียกตรง)
    # Input: self (ChallengeStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def pause_all(self):
        rows = deepcopy(self.rows)
        now = self.clock()
        for row in rows:
            row.update(elapsed_seconds=elapsed(row, now), is_running=False, resume_timestamp=None)
        self.commit(rows)
