"""Save/review and edit dialogs which never mutate the active pipeline canvas."""
from copy import deepcopy
import shlex
import tkinter as tk

import customtkinter as ctk

from Pipeline.saved_runs import save_recipe
from Tools.app_paths import writable_path
from Tools.window_layout import fit_window

BG = "#15151E"
CARD = "#1E1E2A"
CYAN = "#00FFFF"
DIM = "#A0AAC5"


def manual_text(rows):
    return " ".join(
        row["flag"] + (
            " " + shlex.quote(row["value"])
            if row["type"] != "checkbox" and row["value"].strip() else ""
        ) for row in rows if row["flag"].strip()
    )


class SavedPipelineDialog(ctk.CTkToplevel):
    def __init__(self, page, steps, name="", *, editing=False, parent=None):
        super().__init__(parent or page)
        self.page = page
        self.steps = deepcopy(steps)
        self.editing = editing
        self.original_name = name if editing else None
        self.expected = None
        self.index = 0
        self.title("Edit Saved Pipeline" if editing else "Save Pipeline")
        self.configure(fg_color=BG)
        fit_window(self, "680x720" if editing else "620x520")
        self.transient(parent or page.winfo_toplevel())
        self.attributes("-topmost", True)
        self.grab_set()

        ctk.CTkLabel(self, text=self.title(), text_color=CYAN,
                    font=ctk.CTkFont(size=20, weight="bold")).pack(padx=20, pady=(15, 5), anchor="w")
        ctk.CTkLabel(self, text="Pipeline name", text_color=DIM).pack(padx=20, anchor="w")
        self.name_var = tk.StringVar(value=name)
        ctk.CTkEntry(self, textvariable=self.name_var).pack(fill="x", padx=20, pady=(0, 12))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=20, pady=15)
        ctk.CTkButton(buttons, text="Cancel", command=self.destroy,
                      fg_color=CARD, width=100).pack(side="right", padx=(10, 0))
        ctk.CTkButton(buttons, text="Save Changes" if editing else "Save Pipeline",
                      command=self.save, fg_color=CYAN, text_color="black").pack(side="right")
        self.status = ctk.CTkLabel(self, text="", text_color="#FF7896", wraplength=560)
        self.status.pack(side="bottom", fill="x", padx=20)

        if editing:
            self.step_menu = ctk.CTkOptionMenu(
                self, values=[f"Step {i + 1}" for i in range(len(self.steps))],
                command=self.select_step)
            self.step_menu.pack(fill="x", padx=20, pady=(0, 8))
        self.body = ctk.CTkScrollableFrame(self, fg_color=CARD)
        self.body.pack(fill="both", expand=True, padx=20, pady=(0, 5))
        if editing:
            self.draw_step()
        else:
            for i, step in enumerate(self.steps, 1):
                ctk.CTkLabel(self.body, text=f"{i:02d} · {step['name']}",
                            text_color=CYAN, anchor="w").pack(fill="x", padx=10, pady=(10, 0))
                settings = step.get("run_settings", {})
                lines = []
                if step.get("params"):
                    lines.append("Parameters: " + step["params"])
                for opt in settings.get("option_values", []):
                    value = opt["value"]
                    if isinstance(value, bool):
                        value = "On" if value else "Off"
                    lines.append(f"{opt['flag'] or 'Pattern'} = {value}")
                for side in ("before", "after"):
                    text = manual_text(settings.get(side + "_rows", []))
                    if text:
                        on = "On" if settings.get(side + "_enabled") else "Off"
                        lines.append(f"{side.title()} input ({on}): {text}")
                lines.append("Input: " + settings.get("input_source", "previous"))
                ctk.CTkLabel(self.body, text="\n".join(lines), text_color=DIM,
                            justify="left", anchor="w", wraplength=500).pack(fill="x", padx=10, pady=(0, 10))
        self.after(100, self.lift)

    def field(self, label, value):
        ctk.CTkLabel(self.body, text=label, text_color=DIM).pack(anchor="w", padx=10)
        var = tk.StringVar(value=value)
        ctk.CTkEntry(self.body, textvariable=var).pack(fill="x", padx=10, pady=(0, 8))
        return var

    def draw_step(self):
        for widget in self.body.winfo_children():
            widget.destroy()
        step = self.steps[self.index]
        settings = step.get("run_settings", {})
        tools = sorted(set(self.page.engine.file_tools) | set(self.page.engine.text_tools) | {step["name"]})
        ctk.CTkLabel(self.body, text="Tool", text_color=DIM).pack(anchor="w", padx=10)
        self.tool_menu = ctk.CTkOptionMenu(self.body, values=tools, command=self.change_tool)
        self.tool_menu.set(step["name"])
        self.tool_menu.pack(fill="x", padx=10, pady=(0, 8))
        self.params_var = self.field("Parameters", step.get("params", ""))
        self.description_var = self.field("Description", step.get("user_description", ""))
        ctk.CTkLabel(self.body, text="Input source", text_color=DIM).pack(anchor="w", padx=10)
        self.source_var = tk.StringVar(value=settings.get("input_source", "previous"))
        ctk.CTkOptionMenu(self.body, values=["previous", "original", "manual"],
                         variable=self.source_var).pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(self.body, text="manual: choose input when running",
                    text_color=DIM).pack(anchor="w", padx=10)
        values = {(o["flag"], o["type"]): o["value"] for o in settings.get("option_values", [])}
        self.option_vars = []
        seen = set()
        for opt in self.page.engine.tool_options.get(step["name"], []) + step.get("options", []):
            flag, kind = opt["flag"], opt["type"]
            if flag in seen:
                continue
            seen.add(flag)
            label = flag or opt.get("placeholder", "Pattern / value")
            if kind == "checkbox":
                var = tk.BooleanVar(value=values.get((flag, kind), False))
                ctk.CTkCheckBox(self.body, text=label, variable=var).pack(anchor="w", padx=10, pady=6)
            else:
                var = self.field(label, values.get((flag, kind), ""))
            self.option_vars.append((flag, kind, var))
        self.manual_vars = {}
        for side in ("before", "after"):
            enabled = tk.BooleanVar(value=settings.get(side + "_enabled", False))
            ctk.CTkCheckBox(self.body, text=f"Manual options ({side} input)",
                           variable=enabled).pack(anchor="w", padx=10, pady=(15, 6))
            text = self.field("Arguments", manual_text(settings.get(side + "_rows", [])))
            self.manual_vars[side] = enabled, text

    def collect_step(self):
        step = self.steps[self.index]
        shlex.split(self.params_var.get())
        settings = deepcopy(step.get("run_settings", {}))
        settings["input_source"] = self.source_var.get()
        settings["option_values"] = [
            {"flag": flag, "type": kind, "value": var.get()}
            for flag, kind, var in self.option_vars
        ]
        for side, (enabled, text) in self.manual_vars.items():
            value = text.get()
            shlex.split(value)
            old_rows = settings.get(side + "_rows", [])
            settings[side + "_enabled"] = enabled.get()
            settings[side + "_rows"] = old_rows if value == manual_text(old_rows) else (
                [{"flag": value, "type": "checkbox", "value": ""}] if value.strip() else [])
        step.update(params=self.params_var.get(), user_description=self.description_var.get(),
                    run_settings=settings)

    def select_step(self, label):
        try:
            self.collect_step()
        except ValueError as error:
            self.status.configure(text=str(error))
            self.step_menu.set(f"Step {self.index + 1}")
            return
        self.index = int(label.split()[-1]) - 1
        self.status.configure(text="")
        self.draw_step()

    def change_tool(self, name):
        if name == self.steps[self.index]["name"]:
            return
        self.steps[self.index] = {
            "name": name, "params": "", "options": [],
            "user_description": self.description_var.get(),
        }
        self.draw_step()

    def save(self):
        try:
            if self.editing:
                self.collect_step()
            for step in self.steps:
                if step["name"] not in self.page.engine.file_tools and step["name"] not in self.page.engine.text_tools:
                    raise ValueError(f"Tool is not registered: {step['name']}")
            entry = {"pipeline_name": self.name_var.get(), "steps": self.steps}
            save_recipe(writable_path("Pipeline/saved_pipelines.json"), entry,
                        self.original_name, self.expected)
        except (OSError, ValueError, TypeError) as error:
            self.status.configure(text=f"Save failed: {error}")
            return
        self.page.refresh_tools_panel()
        self.destroy()
