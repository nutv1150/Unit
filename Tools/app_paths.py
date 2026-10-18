"""Read-only bundle resources and writable per-user packaged-app data.

Source checkouts retain their existing paths unless UNIT_DATA_HOME is supplied.
No automatic migration of personal evidence or credentials is performed.
"""
import os
from pathlib import Path
import sys
import tempfile

RESOURCE_ROOT = Path(__file__).resolve().parents[1]


# หน้าที่: ตรวจโหมด packaged app หรือ UNIT_DATA_HOME เพื่อเลือกที่เก็บข้อมูลผู้ใช้
# ที่มา: Tools/app_paths.py::initialize_user_data (เรียกตรง)
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: sys.frozen (bool) และ os.environ (Mapping[str, str]) จาก runtime/ระบบ
def uses_user_data():
    return bool(getattr(sys, 'frozen', False) or os.environ.get('UNIT_DATA_HOME'))


# หน้าที่: เลือก data directory จาก environment, packaged mode หรือราก source
# ที่มา: Tools/app_paths.py::initialize_user_data (เรียกตรง)
# ที่มา: Tools/app_paths.py::writable_path (เรียกตรง)
# ที่มา: Tools/desktop_install.py::main (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: UNIT_DATA_HOME/XDG_DATA_HOME (str | None) จาก environment และตำแหน่ง home/source (Path)
def data_root():
    override = os.environ.get('UNIT_DATA_HOME')
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            raise ValueError('UNIT_DATA_HOME must be an absolute path')
        return path
    if getattr(sys, 'frozen', False):
        base = Path(os.environ.get('XDG_DATA_HOME', '')).expanduser()
        if not base.is_absolute():
            base = Path.home() / '.local' / 'share'
        return base / 'unit'
    return RESOURCE_ROOT


# หน้าที่: ต่อ relative path เข้ากับที่เก็บข้อมูลที่เลือกสำหรับแอป
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine (เรียกตรง)
# ที่มา: Tools/dashboard_store.py::DashboardStore.__init__ (เรียกตรง)
# ที่มา: Tools/package_smoke.py::main (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 9 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: relative (str | PathLike[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def writable_path(relative):
    return data_root() / relative


# หน้าที่: สร้างค่าเริ่มต้นใน profile เฉพาะไฟล์ที่ยังไม่มีโดยไม่เขียนทับข้อมูลเดิม
# ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: ค่าเริ่มต้นของ config จาก source/bundle (ไฟล์ JSON) และ data_root() (Path)
def initialize_user_data():
    """Publish clean defaults once, never overwrite an existing user file."""
    if not uses_user_data():
        return
    root = data_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    defaults = RESOURCE_ROOT / ('defaults' if getattr(sys, 'frozen', False) else 'packaging/defaults')
    for relative in ('Pipeline/custom_tools.json', 'Pipeline/saved_pipelines.json', 'custom_tools.json'):
        target = root / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        contents = (defaults / relative).read_bytes()
        # Hard-link publication is atomic and fails if another instance won.
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.unit-default-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            try:
                os.link(temporary, target)
            except FileExistsError:
                pass
        finally:
            temporary.unlink()


# หน้าที่: คัดลอก environment และคืนค่า library path ของระบบก่อนเรียกโปรแกรมภายนอก
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._run_command (เรียกตรง)
# ที่มา: Tools/stream_capture.py::run_capture (เรียกตรง)
# ที่มา: pages/app_portal.py::AppPortalPage.launch_app (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: env (dict[str, str] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def external_environment(env=None):
    """Do not inject bundled Linux libraries into system CLI tools."""
    result = dict(os.environ if env is None else env)
    if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
        original = result.get('LD_LIBRARY_PATH_ORIG')
        if original is None:
            result.pop('LD_LIBRARY_PATH', None)
        else:
            result['LD_LIBRARY_PATH'] = original
    return result
