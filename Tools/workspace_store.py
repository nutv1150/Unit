"""Persistent user groups and challenge timers, independent of Tk."""
import json
import math
import os
import time
import uuid
from copy import deepcopy
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config'


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


def save_records(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)


def make_group(name, tools, group_id=None):
    name = name.strip()
    if not name:
        raise ValueError('กรุณากรอกชื่อกลุ่ม')
    if not tools:
        raise ValueError('เลือกเครื่องมืออย่างน้อย 1 รายการ')
    return dict(id=group_id or uuid.uuid4().hex, name=name,
                category_color=tools[0].get('color', 'purple'), tools=deepcopy(tools))


def integer(value, minimum, label):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError(f'{label} ต้องเป็นจำนวนเต็มตั้งแต่ {minimum}')
    number = int(value)
    if number < minimum:
        raise ValueError(f'{label} ต้องเป็นจำนวนเต็มตั้งแต่ {minimum}')
    return number


def elapsed(record, now=None):
    now = time.time() if now is None else now
    total = record['elapsed_seconds']
    if record['is_running']:
        total += max(0, now - record['resume_timestamp'])
    return total


def format_elapsed(seconds):
    seconds = max(0, int(seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


class ChallengeStore:
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

    def commit(self, rows):
        save_records(self.path, rows)
        self.rows = rows

    def create(self, name, total):
        if not name.strip():
            raise ValueError('กรุณากรอกชื่อการแข่งขัน')
        record = dict(id=uuid.uuid4().hex, name=name.strip(), total_items=integer(total, 1, 'Total items'),
                      solved_items=0, elapsed_seconds=0, resume_timestamp=None, is_running=False)
        self.commit(self.rows + [record])
        return record['id']

    def get(self, record_id):
        return next(row for row in self.rows if row['id'] == record_id)

    def update(self, record_id, solved, running):
        rows = deepcopy(self.rows)
        row = next(r for r in rows if r['id'] == record_id)
        solved = integer(solved, 0, 'Solved')
        if solved > row['total_items']:
            raise ValueError('Solved ต้องไม่เกิน Total items')
        now = self.clock()
        row.update(elapsed_seconds=elapsed(row, now), resume_timestamp=now if running else None,
                   is_running=bool(running), solved_items=solved)
        self.commit(rows)

    def delete(self, record_id):
        self.commit([r for r in self.rows if r['id'] != record_id])

    def pause_all(self):
        rows = deepcopy(self.rows)
        now = self.clock()
        for row in rows:
            row.update(elapsed_seconds=elapsed(row, now), is_running=False, resume_timestamp=None)
        self.commit(rows)
