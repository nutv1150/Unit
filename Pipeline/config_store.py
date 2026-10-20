"""Validated, atomic configuration writes. Never recover by overwriting bad JSON."""
import json
import os
import tempfile
from pathlib import Path


# หน้าที่: อ่าน JSON เป็นโครงสร้าง Python หรือใช้ค่าเริ่มต้นเมื่อยังไม่มีไฟล์
# ที่มา: Pipeline/config_store.py::saved_pipelines (เรียกตรง)
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.save_custom_tool (เรียกตรง)
# ที่มา: pages/my_tools.py::available_tool_options (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
# Input: default (Any (ค่าเริ่มต้นเมื่อไฟล์ยังไม่มี)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


# หน้าที่: เขียน JSON ผ่านไฟล์ชั่วคราวแล้วแทนที่ปลายทางเมื่อเขียนสำเร็จ
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.save_custom_tool (เรียกตรง)
# ที่มา: Tools/package_smoke.py::main (เรียกตรง)
# ที่มา: pages/pipeline.py::PipelinePage.finalize_wizard_pipeline (เรียกตรง)
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
# Input: data (Any (ค่าที่ json.dump serialize ได้)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


# หน้าที่: อ่านไฟล์ Saved Pipelines และตรวจ schema ก่อนคืนข้อมูล
# ที่มา: Tools/package_smoke.py::main (เรียกตรง)
# ที่มา: pages/pipeline.py::PipelinePage.finalize_wizard_pipeline (เรียกตรง)
# ที่มา: pages/pipeline.py::PipelinePage.load_saved_pipeline_to_canvas (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def saved_pipelines(path):
    data = read_json(path, {"saved_pipelines": []})
    return validate_saved_pipelines(data)


# หน้าที่: ตรวจชื่อ pipeline รายการขั้นตอน และ options ตาม schema ที่แอปรองรับ
# ที่มา: Pipeline/config_store.py::saved_pipelines (เรียกตรง)
# ที่มา: pages/pipeline.py::PipelinePage.finalize_wizard_pipeline (เรียกตรง)
# Input: data (Any (ค่าจาก JSON; validator ตรวจ schema dict[str, list[dict]])) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def validate_saved_pipelines(data):
    if not isinstance(data, dict) or not isinstance(data.get("saved_pipelines"), list):
        raise ValueError("Invalid saved pipeline config")
    for pipeline in data["saved_pipelines"]:
        if not isinstance(pipeline, dict) or not isinstance(pipeline.get("pipeline_name"), str) or not pipeline["pipeline_name"].strip() or not isinstance(pipeline.get("steps"), list):
            raise ValueError("Invalid saved pipeline")
        for step in pipeline["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("name"), str) or not step["name"].strip():
                raise ValueError("Invalid pipeline step")
            if not isinstance(step.get("params", ""), str) or not isinstance(step.get("user_description", ""), str):
                raise ValueError("Invalid step parameters")
            if not isinstance(step.get("options", []), list):
                raise ValueError("Invalid step options")
            for option in step.get("options", []):
                if not isinstance(option, dict) or not isinstance(option.get("flag"), str) or option.get("type") not in ("checkbox", "text", "file"):
                    raise ValueError("Invalid step option")
            if "run_settings" in step:
                validate_run_settings(step["run_settings"])
    return data


def validate_run_settings(settings):
    """Optional executed values; legacy pipelines have only option definitions."""
    if not isinstance(settings, dict):
        raise ValueError("Invalid saved run settings")
    if settings.get("input_source", "previous") not in ("previous", "original", "manual"):
        raise ValueError("Invalid saved input source")
    for key in ("before_enabled", "after_enabled"):
        if not isinstance(settings.get(key, False), bool):
            raise ValueError("Invalid manual option switch")
    for key in ("option_values", "before_rows", "after_rows"):
        rows = settings.get(key, [])
        if not isinstance(rows, list):
            raise ValueError("Invalid saved option values")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("flag"), str):
                raise ValueError("Invalid saved option flag")
            kind = row.get("type")
            if kind not in ("checkbox", "text", "file"):
                raise ValueError("Invalid saved option type")
            value = row.get("value")
            if key == "option_values" and kind == "checkbox":
                if not isinstance(value, bool):
                    raise ValueError("Invalid saved checkbox value")
            elif not isinstance(value, str):
                raise ValueError("Invalid saved option value")
