import subprocess
import json
import os
import shlex
import signal
import time

from Tools.flag_detector import find_first_flag
from Pipeline.output_files import CommandResult, output_locations, snapshot_files, changed_files
from Pipeline.config_store import read_json, write_json

class PipelineEngine:
    # path ของไฟล์นี้
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # path ของไฟล์เก็บ tool
    CUSTOM_TOOL_FILE = os.path.join(BASE_DIR, "custom_tools.json")
    # regex สำหรับหา flag

    def __init__(self):
        self.load_error = ""
        self.file_tools = {} # tool ที่ใช้กับไฟล์
        self.text_tools = {} # tool ที่ใช้กับ text
        self.tool_descriptions = {} 
        self.tool_options = {} # เก็บ options ของ tool
        
        self.tool_input_modes = {}
        self.tool_input_flags = {}
        

        try:
            self.load_custom_tools()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.file_tools.clear()
            self.text_tools.clear()
            self.load_error = f"Cannot load tools: {error} (original file unchanged)"
        

    def load_custom_tools(self):

        if not os.path.exists(self.CUSTOM_TOOL_FILE):
            return # ถ้าไม่มีไฟล์ก็จบ

        with open(self.CUSTOM_TOOL_FILE, encoding="utf-8") as f:
            data = json.load(f) # อ่าน JSON

        self.validate_tools(data)

        for category in data: # วนทุกหมวด

            if not isinstance(data[category], list):
                continue

            for tool in data[category]:

                name = tool["name"] # ชื่อ tool
                command = tool["command"] 
                mode = tool["mode"]

                params = tool.get("params", [])
                input_mode = tool.get(
                    "input_mode",
                    "positional"
                )

                input_flag = tool.get(
                    "input_flag",
                    None
                )

                self.tool_input_modes[name] = input_mode
                self.tool_input_flags[name] = input_flag

                # description
                self.tool_descriptions[name] = tool.get(
                    "description",
                    "No description available"
                )

                # options (สำคัญ)
                self.tool_options[name] = tool.get("options", [])

                #command + params + input → กลายเป็น list command
                def make_file_tool(
                    command,
                    params,
                    input_mode="positional",
                    input_flag=None
                ):
                    def tool(file_path, p=None):

                        cmd = [command] + params + self.arguments(p)

                        if file_path:

                            cmd = self.attach_input(cmd, os.fspath(file_path), input_mode, input_flag)

                        return cmd

                    return tool

                def make_text_tool(command, params):
                    def tool(p=None):
                        return [command] + params + self.arguments(p)
                    return tool
                
                if mode == "file":

                    self.file_tools[name] = make_file_tool(
                        command,
                        params,
                        input_mode,
                        input_flag
                    )
                else:
                    self.text_tools[name] = make_text_tool(command, params)

    @staticmethod
    def arguments(value):
        if value is None:
            return []
        if isinstance(value, str):
            return shlex.split(value)
        if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
            return list(value)
        raise ValueError("Arguments must be text or a list of strings")

    @staticmethod
    def validate_tools(data):
        if not isinstance(data, dict):
            raise ValueError("Tool config must be an object of categories")
        names = set()
        for category, entries in data.items():
            if not isinstance(entries, list):
                raise ValueError(f"Invalid category: {category}")
            for entry in entries:
                if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("name", "command", "mode")):
                    raise ValueError("Invalid tool definition")
                if entry["mode"] not in ("text", "file") or entry["name"] in names:
                    raise ValueError("Invalid mode or duplicate tool name")
                names.add(entry["name"])
                if not isinstance(entry.get("params", []), list):
                    raise ValueError("Tool params must be an argument list")
                PipelineEngine.arguments(entry.get("params", []))
                mode = entry.get("input_mode", "positional")
                if mode not in ("positional", "flag", "keyvalue"):
                    raise ValueError("Invalid input mode")
                if mode != "positional" and not isinstance(entry.get("input_flag"), str):
                    raise ValueError("Missing input flag")
                if not isinstance(entry.get("options", []), list):
                    raise ValueError("Options must be a list")
                for opt in entry.get("options", []):
                    if not isinstance(opt, dict) or not isinstance(opt.get("flag"), str) or opt.get("type") not in ("checkbox", "text", "file"):
                        raise ValueError("Invalid tool option")

    @staticmethod
    def attach_input(cmd, path, mode, flag):
        # Honour legacy manual -in/-r inputs, but never silently use a different file.
        if mode == "flag" and flag:
            if flag in cmd:
                index = cmd.index(flag) + 1
                if index == len(cmd) or cmd[index].startswith("-"):
                    cmd.insert(index, path)
                elif os.path.abspath(cmd[index]) != os.path.abspath(path):
                    raise ValueError(f"{flag} conflicts with the Input file; select one input")
            else:
                cmd += [flag, path]
        elif mode == "keyvalue" and flag:
            prefix = flag.rstrip("=") + "="
            existing = next((x for x in cmd if x.startswith(prefix)), None)
            if existing is None:
                cmd.append(prefix + path)
            elif os.path.abspath(existing[len(prefix):]) != os.path.abspath(path):
                raise ValueError(f"{prefix} conflicts with the Input file")
        else:
            cmd.append(path)
        return cmd

    def build_command(self, tool, params=None, file_path=None, after_params=None):
        if tool in self.file_tools:
            cmd = self.file_tools[tool](file_path, params)
        elif tool in self.text_tools:
            cmd = self.text_tools[tool](params)
        else:
            raise ValueError(f"Unknown tool: {tool}")
        return cmd + self.arguments(after_params)

    @staticmethod
    def _communicate(cmd, input_data, cancel_event):
        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, start_new_session=(os.name == "posix")) as process:
            deadline = time.monotonic() + 30
            first = True
            while True:
                if cancel_event.is_set() or time.monotonic() >= deadline:
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        process.kill()
                    out, err = process.communicate()
                    reason = b"Cancelled" if cancel_event.is_set() else b"Command timeout"
                    return CommandResult(out, err + b"\n" + reason)
                try:
                    out, err = process.communicate(input=input_data if first else None, timeout=0.1)
                    return CommandResult(out, err, process.returncode)
                except subprocess.TimeoutExpired:
                    first = False

    def _run_command(self, cmd, input_data=None, input_path=None, detailed=False, cancel_event=None):
        if cancel_event is not None and cancel_event.is_set():
            result = CommandResult(stderr=b"Cancelled")
            return result if detailed else result.stderr
        locations = output_locations(cmd, input_path) if detailed else []
        before, complete_before = snapshot_files(locations)
        try:
            if cancel_event is not None:
                result = self._communicate(cmd, input_data, cancel_event)
            else:
                process = subprocess.run(
                    cmd, input=input_data, capture_output=True, check=False, timeout=30,
                )
                result = CommandResult(process.stdout, process.stderr, process.returncode)
        except FileNotFoundError:
            result = CommandResult(stderr=b"Command not found")
        except subprocess.TimeoutExpired as error:
            result = CommandResult(
                stdout=error.stdout or b"",
                stderr=(error.stderr or b"") + b"\nCommand timeout",
            )
        except OSError as error:
            result = CommandResult(stderr=str(error).encode("utf-8"))
        if detailed and result.succeeded:
            after, complete_after = snapshot_files(locations)
            if complete_before and complete_after:
                result.files = changed_files(before, after, input_path)
            else:
                result.discovery_note = "File discovery was incomplete. Use Browse result file to select the output file."
        return result if detailed else result.stdout + result.stderr

    def run_text_tool(self, tool, input_data, params=None, detailed=False):

        if tool not in self.text_tools:
            return CommandResult(stderr=b"Unknown text tool") if detailed else b"Unknown text tool"

        cmd = self.text_tools[tool](params) # สร้าง command

        return self._run_command(cmd, input_data=input_data, detailed=detailed)

    def run_file_tool(self, tool, file_path, params=None, detailed=False):

        if tool not in self.file_tools:
            return CommandResult(stderr=b"Unknown file tool") if detailed else b"Unknown file tool"

        cmd = self.file_tools[tool](file_path, params)

        return self._run_command(cmd, input_path=file_path, detailed=detailed)
    def check_flag(self, text):
        return find_first_flag(text)
    
    def add_tool(self, name, command, mode):

        if mode == "file":

            self.file_tools[name] = lambda f, p=None, c=command: \
                [c] + self.arguments(p) + [f]

        else:

            self.text_tools[name] = lambda p=None, c=command: \
                [c] + self.arguments(p)
            
    def save_custom_tool(self, name, command, mode, category, description=""):
        # ปรับปรุงให้บันทึก description ลง JSON ด้วย
        data = read_json(self.CUSTOM_TOOL_FILE, {})
        self.validate_tools(data)
        if not name.strip() or not command.strip() or not category.strip():
            raise ValueError("Name, executable and category are required")

        if category not in data:
            data[category] = []

        data[category].append({
            "name": name,
            "command": command,
            "mode": mode,
            "description": description, # คำอธิบายจากระบบ
            "user_description": ""      # เว้นว่างไว้สำหรับรอให้ User มาเติมใน Pipeline
        })

        self.validate_tools(data)
        write_json(self.CUSTOM_TOOL_FILE, data)
        self.load_custom_tools()
