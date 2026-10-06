"""Validated, atomic configuration writes. Never recover by overwriting bad JSON."""
import json
import os
import tempfile
from pathlib import Path


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


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


def saved_pipelines(path):
    data = read_json(path, {"saved_pipelines": []})
    return validate_saved_pipelines(data)


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
    return data
