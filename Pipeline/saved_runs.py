"""Reusable pipeline recipes, separate from live widgets and execution results."""
from copy import deepcopy

from Pipeline.config_store import saved_pipelines, validate_saved_pipelines, write_json


def step_recipe(node, settings=None):
    recipe = {
        "name": node["name"],
        "params": node.get("params", ""),
        "user_description": node.get("user_description", ""),
        "options": deepcopy(node.get("options", [])),
    }
    settings = node.get("run_settings") if settings is None else settings
    if settings is not None:
        recipe["run_settings"] = deepcopy(settings)
    return recipe


def completed_steps(nodes):
    """Only a complete, current chain may be offered as a successful recipe."""
    if not nodes or any(not node.get("_successful_step") for node in nodes):
        return None
    return deepcopy([node["_successful_step"] for node in nodes])


def save_recipe(path, entry, original_name=None, expected=None):
    entry = deepcopy(entry)
    entry["pipeline_name"] = entry["pipeline_name"].strip()
    validate_saved_pipelines({"saved_pipelines": [entry]})
    if not entry["steps"]:
        raise ValueError("A pipeline needs at least one step")
    data = saved_pipelines(path)
    entries = data["saved_pipelines"]
    if any(p["pipeline_name"] == entry["pipeline_name"]
           and p["pipeline_name"] != original_name for p in entries):
        raise ValueError("Pipeline name already exists; choose a different name")
    if original_name is None:
        entries.append(entry)
    else:
        matches = [i for i, p in enumerate(entries) if p["pipeline_name"] == original_name]
        if len(matches) != 1:
            raise ValueError("Saved pipeline was removed or is ambiguous; reopen the list")
        index = matches[0]
        if expected is not None and entries[index] != expected:
            raise ValueError("Saved pipeline changed; reopen it before editing")
        entries[index] = entry
    write_json(path, data)
    return entry


def delete_recipe(path, name, expected=None):
    data = saved_pipelines(path)
    matches = [p for p in data["saved_pipelines"] if p["pipeline_name"] == name]
    if len(matches) != 1:
        raise ValueError("Saved pipeline was removed or is ambiguous; reopen the list")
    if expected is not None and matches[0] != expected:
        raise ValueError("Saved pipeline changed; reopen it before deleting")
    data["saved_pipelines"].remove(matches[0])
    write_json(path, data)
