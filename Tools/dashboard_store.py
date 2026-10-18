import json
import os
import tempfile
import threading
import uuid
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from Tools.app_paths import writable_path


class DashboardStore:
    """Persistent activity store used by the UNIT dashboard."""

    SCHEMA_VERSION = 1
    MAX_EVENTS = 2000
    DEFAULT_COMPETITION = "General"
    DEFAULT_CATEGORY = "Core"

    # หน้าที่: กำหนด path, lock และโหลดสถานะ Dashboard
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: state_path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    def __init__(self, state_path=None):
        default_path = writable_path('data/dashboard_state.json')
        self.state_path = Path(state_path or default_path)
        self._lock = threading.RLock()
        self.persistence_error = None
        self.read_only = False
        self._state = self._load_state()

    # หน้าที่: สร้างค่าเริ่มต้นของหมวด การแข่งขัน รายการโปรด และประวัติกิจกรรม
    # ที่มา: Tools/dashboard_store.py::DashboardStore._load_state (เรียกตรง)
    # Input: cls (type[DashboardStore]) — Python ส่งคลาสเมื่อเรียก classmethod
    @classmethod
    def _default_state(cls):
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "active_competition": cls.DEFAULT_COMPETITION,
            "competitions": [cls.DEFAULT_COMPETITION],
            "categories": [cls.DEFAULT_CATEGORY],
            "favorites": [
                {
                    "name": "Data Hashing",
                    "target": "page:Data Hashing",
                    "category": cls.DEFAULT_CATEGORY,
                    "shortcut": "Ctrl+1",
                },
                {
                    "name": "File Inspection",
                    "target": "page:File Inspection",
                    "category": cls.DEFAULT_CATEGORY,
                    "shortcut": "Ctrl+2",
                },
                {
                    "name": "Pipeline",
                    "target": "page:Pipeline",
                    "category": cls.DEFAULT_CATEGORY,
                    "shortcut": "Ctrl+3",
                },
            ],
            "events": [],
        }

    # หน้าที่: อ่านและตรวจ state จาก JSON โดยเก็บข้อผิดพลาดและปิดการเขียนเมื่อข้อมูลเสีย
    # ที่มา: Tools/dashboard_store.py::DashboardStore.__init__ (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _load_state(self):
        default = self._default_state()

        if not self.state_path.exists():
            return default

        try:
            with self.state_path.open("r", encoding="utf-8") as file_obj:
                loaded = json.load(file_obj)
        except (OSError, ValueError, TypeError) as exc:
            self.persistence_error = f"Dashboard state could not be read: {exc}"
            self.read_only = True
            return default

        if not isinstance(loaded, dict):
            self.persistence_error = "Dashboard state has an invalid schema"
            self.read_only = True
            return default

        if not self._valid_loaded_state(loaded):
            self.persistence_error = "Dashboard state has an invalid schema"
            self.read_only = True
            return default

        for key, value in default.items():
            loaded.setdefault(key, deepcopy(value))

        loaded["competitions"] = self._clean_names(
            loaded.get("competitions"), self.DEFAULT_COMPETITION
        )
        loaded["categories"] = self._clean_names(
            loaded.get("categories"), self.DEFAULT_CATEGORY
        )
        loaded["active_competition"] = str(
            loaded.get("active_competition") or self.DEFAULT_COMPETITION
        ).strip()

        if loaded["active_competition"] not in loaded["competitions"]:
            loaded["competitions"].append(loaded["active_competition"])

        if not isinstance(loaded.get("favorites"), list):
            loaded["favorites"] = deepcopy(default["favorites"])
        else:
            loaded["favorites"] = [self._clean_favorite(favorite) for favorite in loaded["favorites"]]
        if not isinstance(loaded.get("events"), list):
            loaded["events"] = []
        else:
            loaded["events"] = [self._clean_event(event) for event in loaded["events"]]

        loaded["events"] = loaded["events"][-self.MAX_EVENTS :]
        loaded["schema_version"] = self.SCHEMA_VERSION
        return loaded

    # หน้าที่: ตรวจ schema และชนิดฟิลด์ของ state ที่อ่านจากไฟล์
    # ที่มา: Tools/dashboard_store.py::DashboardStore._load_state (เรียกตรง)
    # Input: cls (type[DashboardStore]) — Python ส่งคลาสเมื่อเรียก classmethod
    # Input: state (dict[str, Any]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @classmethod
    def _valid_loaded_state(cls, state):
        if state.get("schema_version", cls.SCHEMA_VERSION) != cls.SCHEMA_VERSION:
            return False
        checks = (("competitions", list), ("categories", list), ("favorites", list), ("events", list))
        for key, kind in checks:
            if key in state and not isinstance(state[key], kind):
                return False
        if "active_competition" in state and not isinstance(state["active_competition"], str):
            return False
        for key in ("competitions", "categories"):
            if any(not isinstance(value, str) or not value.strip() for value in state.get(key, [])):
                return False
        for favorite in state.get("favorites", []):
            if (not isinstance(favorite, dict) or not isinstance(favorite.get("name"), str)
                    or not isinstance(favorite.get("target"), str)
                    or ("category" in favorite and not isinstance(favorite["category"], str))
                    or ("shortcut" in favorite and not isinstance(favorite["shortcut"], str))):
                return False
            if not favorite["name"].strip() or not favorite["target"].strip():
                return False
        for event in state.get("events", []):
            if not isinstance(event, dict):
                return False
            for key in ("id", "timestamp", "competition", "tool", "category", "action", "status", "details"):
                if key in event and not isinstance(event[key], str):
                    return False
            if "flags" in event and not isinstance(event["flags"], list):
                return False
            if any(not isinstance(flag, str) for flag in event.get("flags", [])):
                return False
            if "file_path" in event and event["file_path"] is not None and not isinstance(event["file_path"], str):
                return False
        return True

    # หน้าที่: ตรวจและปรับรูปแบบรายการโปรดหนึ่งรายการ
    # ที่มา: Tools/dashboard_store.py::DashboardStore._load_state (เรียกตรง)
    # Input: favorite (Any (record จาก JSON ที่ต้องตรวจชนิด)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _clean_favorite(favorite):
        if not isinstance(favorite, dict):
            return None
        name, target = favorite.get("name"), favorite.get("target")
        if not isinstance(name, str) or not isinstance(target, str) or not name.strip() or not target.strip():
            return None
        return {
            "name": name.strip(), "target": target.strip(),
            "category": str(favorite.get("category") or "Core").strip() or "Core",
            "shortcut": str(favorite.get("shortcut") or "").strip(),
        }

    # หน้าที่: ปรับฟิลด์กิจกรรมให้อยู่ในชนิดที่บันทึกและแสดงผลได้
    # ที่มา: Tools/dashboard_store.py::DashboardStore._load_state (เรียกตรง)
    # Input: event (Any (record จาก JSON ที่ต้องตรวจชนิด)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _clean_event(event):
        if not isinstance(event, dict):
            return None
        flags = event.get("flags") if isinstance(event.get("flags"), list) else []
        return {
            "id": str(event.get("id") or uuid.uuid4().hex),
            "timestamp": str(event.get("timestamp") or ""),
            "competition": str(event.get("competition") or "General"),
            "tool": str(event.get("tool") or "Unknown"),
            "category": str(event.get("category") or "Other"),
            "action": str(event.get("action") or "Run"),
            "status": str(event.get("status") or "failed"),
            "file_path": str(event["file_path"]) if isinstance(event.get("file_path"), (str, os.PathLike)) else None,
            "flags": [str(flag) for flag in flags if isinstance(flag, (str, int, float))],
            "details": str(event.get("details") or "")[:500],
        }

    # หน้าที่: ตัดช่องว่างและชื่อซ้ำ พร้อมใส่ชื่อสำรองในรายการ
    # ที่มา: Tools/dashboard_store.py::DashboardStore._load_state (เรียกตรง)
    # Input: values (Any (ค่าจาก JSON; ต้องเป็น list จึงใช้รายการได้)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: fallback (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _clean_names(values, fallback):
        if not isinstance(values, list):
            values = []

        cleaned = []
        for value in values:
            name = str(value).strip()
            if name and name not in cleaned:
                cleaned.append(name)

        if fallback not in cleaned:
            cleaned.insert(0, fallback)
        return cleaned

    # หน้าที่: บันทึก state แบบ atomic โดยเคารพสถานะ read-only
    # ที่มา: Tools/dashboard_store.py::DashboardStore._mutate (เรียกตรง)
    # ที่มา: Tools/dashboard_store.py::DashboardStore.remove_category (เรียกตรง)
    # ที่มา: Tools/dashboard_store.py::DashboardStore.save_favorite (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _save(self):
        if self.read_only:
            raise OSError(self.persistence_error or "Dashboard state is read-only")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.state_path.name}.", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file_obj:
                json.dump(self._state, file_obj, indent=2, ensure_ascii=False)
                file_obj.flush()
                os.fsync(file_obj.fileno())
            os.replace(temp_name, self.state_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    # หน้าที่: แก้ state ภายใต้ lock และย้อนคืนสำเนาเมื่อบันทึกไม่สำเร็จ
    # ที่มา: Tools/dashboard_store.py::DashboardStore.add_competition (เรียกตรง)
    # ที่มา: Tools/dashboard_store.py::DashboardStore.set_active_competition (เรียกตรง)
    # ที่มา: Tools/dashboard_store.py::DashboardStore.add_category (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: operation (Callable[[], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
    def _mutate(self, operation):
        with self._lock:
            previous = deepcopy(self._state)
            try:
                operation()
                self._save()
            except Exception:
                self._state = previous
                raise

    # หน้าที่: คืนชื่อการแข่งขันที่กำลังเลือกจาก state
    # ที่มา: API/helper ของโมดูลนี้; ผู้เรียกส่ง arguments หรือเรียกผ่าน callback/interface
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def get_active_competition(self):
        with self._lock:
            return self._state["active_competition"]

    # หน้าที่: คืนสำเนารายชื่อการแข่งขัน
    # ที่มา: API/helper ของโมดูลนี้; ผู้เรียกส่ง arguments หรือเรียกผ่าน callback/interface
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def list_competitions(self):
        with self._lock:
            return list(self._state["competitions"])

    # หน้าที่: ตรวจชื่อและเพิ่มการแข่งขันพร้อมเลือกเป็นรายการปัจจุบัน
    # ที่มา: pages/dashboard.py::DashboardPage.open_competition_popup.save_competition (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def add_competition(self, name):
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Competition name is required")

        # หน้าที่: แก้ state ที่ฟังก์ชันภายนอกเตรียมไว้ ภายใต้ขั้นตอนบันทึกและ rollback ของ store
        # ที่มา: Tools/dashboard_store.py::DashboardStore.add_competition (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
        # Closure: clean_name (str) — รับจาก scope DashboardStore.add_competition
        # Closure: self (DashboardStore) — รับจาก scope DashboardStore.add_competition
        def operation():
            if clean_name not in self._state["competitions"]:
                self._state["competitions"].append(clean_name)
            self._state["active_competition"] = clean_name
        self._mutate(operation)
        return clean_name

    # หน้าที่: เปลี่ยนการแข่งขันปัจจุบันและเพิ่มชื่อถ้ายังไม่มี
    # ที่มา: pages/dashboard.py::DashboardPage.change_competition (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def set_active_competition(self, name):
        clean_name = str(name or "").strip()
        if not clean_name:
            return

        # หน้าที่: แก้ state ที่ฟังก์ชันภายนอกเตรียมไว้ ภายใต้ขั้นตอนบันทึกและ rollback ของ store
        # ที่มา: Tools/dashboard_store.py::DashboardStore.set_active_competition (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
        # Closure: clean_name (str) — รับจาก scope DashboardStore.set_active_competition
        # Closure: self (DashboardStore) — รับจาก scope DashboardStore.set_active_competition
        def operation():
            if clean_name not in self._state["competitions"]:
                self._state["competitions"].append(clean_name)
            self._state["active_competition"] = clean_name
        self._mutate(operation)

    # หน้าที่: คืนสำเนารายชื่อหมวดรายการโปรด
    # ที่มา: pages/dashboard.py::DashboardPage.open_pin_popup (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup.render_categories (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def list_categories(self):
        with self._lock:
            return list(self._state["categories"])

    # หน้าที่: ตรวจชื่อหมวดและบันทึกเมื่อเป็นหมวดใหม่
    # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup.add_category (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def add_category(self, name):
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Category name is required")

        if clean_name not in self._state["categories"]:
            self._mutate(lambda: self._state["categories"].append(clean_name))
        return clean_name

    # หน้าที่: ลบหมวดที่ไม่ใช่หมวดหลักและย้ายรายการโปรดกลับหมวดเริ่มต้น
    # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup.delete_category (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def remove_category(self, name):
        clean_name = str(name or "").strip()
        if clean_name == self.DEFAULT_CATEGORY:
            return False

        with self._lock:
            if clean_name not in self._state["categories"]:
                return False

            # หน้าที่: แก้ state ที่ฟังก์ชันภายนอกเตรียมไว้ ภายใต้ขั้นตอนบันทึกและ rollback ของ store
            # ที่มา: Tools/dashboard_store.py::DashboardStore.remove_category (เรียกตรง)
            # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
            # Closure: clean_name (str) — รับจาก scope DashboardStore.remove_category
            # Closure: self (DashboardStore) — รับจาก scope DashboardStore.remove_category
            def operation():
                self._state["categories"].remove(clean_name)
                for favorite in self._state["favorites"]:
                    if favorite.get("category") == clean_name:
                        favorite["category"] = self.DEFAULT_CATEGORY
            previous = deepcopy(self._state)
            operation()
            try:
                self._save()
            except Exception:
                self._state = previous
                raise
        return True

    # หน้าที่: คืน deep copy ของรายการโปรดเพื่อไม่ให้ผู้เรียกแก้ state โดยตรง
    # ที่มา: API/helper ของโมดูลนี้; ผู้เรียกส่ง arguments หรือเรียกผ่าน callback/interface
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def list_favorites(self):
        with self._lock:
            return deepcopy(self._state["favorites"])

    # หน้าที่: เพิ่มหรือแก้รายการโปรดและจัดการ shortcut ที่ซ้ำก่อนบันทึก
    # ที่มา: pages/dashboard.py::DashboardPage.open_pin_popup.save_pin (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: target (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: category (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: shortcut (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def save_favorite(self, name, target, category=None, shortcut=""):
        clean_name = str(name or "").strip()
        clean_target = str(target or "").strip()
        clean_category = str(category or self.DEFAULT_CATEGORY).strip()
        clean_shortcut = str(shortcut or "").strip()

        if not clean_name or not clean_target:
            raise ValueError("Favorite name and target are required")

        with self._lock:
            previous = deepcopy(self._state)
            if clean_category not in self._state["categories"]:
                self._state["categories"].append(clean_category)

            # A shortcut can belong to only one favorite.
            if clean_shortcut:
                for favorite in self._state["favorites"]:
                    if favorite.get("shortcut") == clean_shortcut:
                        favorite["shortcut"] = ""

            new_favorite = {
                "name": clean_name,
                "target": clean_target,
                "category": clean_category,
                "shortcut": clean_shortcut,
            }

            for index, favorite in enumerate(self._state["favorites"]):
                if favorite.get("target") == clean_target:
                    self._state["favorites"][index] = new_favorite
                    break
            else:
                self._state["favorites"].append(new_favorite)

            try:
                self._save()
            except Exception:
                self._state = previous
                raise
        return deepcopy(new_favorite)

    # หน้าที่: ลบรายการโปรดตาม target และบันทึก state เมื่อมีการเปลี่ยนแปลง
    # ที่มา: pages/dashboard.py::DashboardPage.remove_favorite (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: target (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def remove_favorite(self, target):
        clean_target = str(target or "").strip()
        with self._lock:
            previous = deepcopy(self._state)
            before = len(self._state["favorites"])
            self._state["favorites"] = [
                item
                for item in self._state["favorites"]
                if item.get("target") != clean_target
            ]
            changed = len(self._state["favorites"]) != before
            if changed:
                try:
                    self._save()
                except Exception:
                    self._state = previous
                    raise
        return changed

    # หน้าที่: ปรับข้อมูลกิจกรรมและบันทึกลงประวัติ Dashboard ภายใต้เพดานรายการ
    # ที่มา: app.py::UNITApp.record_activity (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: category (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: action (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: status (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: file_path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    # Input: flags (list[str] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: details (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: competition (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def record_event(
        self,
        tool,
        category,
        action,
        status="success",
        file_path=None,
        flags=None,
        details=None,
        competition=None,
    ):
        clean_tool = str(tool or "Unknown").strip() or "Unknown"
        clean_category = str(category or "Other").strip() or "Other"
        clean_action = str(action or "Run").strip() or "Run"
        clean_status = "success" if status == "success" else "failed"
        clean_flags = []

        for flag in flags or []:
            value = str(flag).strip()
            if value and value not in clean_flags:
                clean_flags.append(value)

        clean_file_path = None
        if file_path:
            clean_file_path = os.path.abspath(os.path.expanduser(str(file_path)))

        with self._lock:
            previous = deepcopy(self._state)
            active_competition = str(
                competition or self._state["active_competition"]
            ).strip()
            if active_competition not in self._state["competitions"]:
                self._state["competitions"].append(active_competition)

            event = {
                "id": uuid.uuid4().hex,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "competition": active_competition,
                "tool": clean_tool,
                "category": clean_category,
                "action": clean_action,
                "status": clean_status,
                "file_path": clean_file_path,
                "flags": clean_flags,
                "details": str(details or "")[:500],
            }
            self._state["events"].append(event)
            self._state["events"] = self._state["events"][-self.MAX_EVENTS :]
            try:
                self._save()
            except Exception:
                self._state = previous
                raise
        return deepcopy(event)

    # หน้าที่: สรุปสถิติ หมวด รายการโปรด เครื่องมือยอดนิยม และไฟล์ล่าสุดจาก state
    # ที่มา: pages/dashboard.py::DashboardPage.refresh_dashboard (เรียกตรง)
    # Input: self (DashboardStore) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: recent_limit (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def get_snapshot(self, recent_limit=6):
        with self._lock:
            events = deepcopy(self._state["events"])
            favorites = deepcopy(self._state["favorites"])
            competitions = list(self._state["competitions"])
            categories = list(self._state["categories"])
            active_competition = self._state["active_competition"]

        successful = sum(event.get("status") == "success" for event in events)
        failed = len(events) - successful
        flag_count = sum(len(event.get("flags") or []) for event in events)
        tool_counts = Counter(event.get("tool", "Unknown") for event in events)

        recent_files = []
        seen_paths = set()
        for event in reversed(events):
            path = event.get("file_path")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            recent_files.append(
                {
                    "path": path,
                    "name": os.path.basename(path),
                    "timestamp": event.get("timestamp", ""),
                    "tool": event.get("tool", ""),
                    "competition": event.get("competition", self.DEFAULT_COMPETITION),
                    "exists": os.path.isfile(path),
                }
            )
            if len(recent_files) >= recent_limit:
                break

        competition_rows = []
        for competition in competitions:
            competition_events = [
                event
                for event in events
                if event.get("competition") == competition
            ]
            file_paths = {
                event.get("file_path")
                for event in competition_events
                if event.get("file_path")
            }
            competition_rows.append(
                {
                    "name": competition,
                    "operations": len(competition_events),
                    "success": sum(
                        event.get("status") == "success"
                        for event in competition_events
                    ),
                    "files": len(file_paths),
                    "flags": sum(
                        len(event.get("flags") or [])
                        for event in competition_events
                    ),
                }
            )

        return {
            "totals": {
                "operations": len(events),
                "success": successful,
                "failed": failed,
                "flags": flag_count,
                "files": len(
                    {
                        event.get("file_path")
                        for event in events
                        if event.get("file_path")
                    }
                ),
                "success_rate": (
                    round((successful / len(events)) * 100)
                    if events
                    else 0
                ),
            },
            "top_tools": tool_counts.most_common(3),
            "recent_files": recent_files,
            "competition_stats": competition_rows,
            "recent_events": list(reversed(events[-recent_limit:])),
            "favorites": favorites,
            "competitions": competitions,
            "categories": categories,
            "active_competition": active_competition,
        }
