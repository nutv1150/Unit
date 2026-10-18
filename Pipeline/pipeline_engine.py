import subprocess
import json
import os
import shlex
import signal
import time

from Tools.flag_detector import find_first_flag
from Pipeline.output_files import CommandResult, output_locations, snapshot_files, changed_files
from Pipeline.config_store import read_json, write_json
from Tools.stream_capture import run_capture
from Tools.app_paths import writable_path, external_environment

class PipelineEngine:
    # path ของไฟล์นี้
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # path ของไฟล์เก็บ tool
    CUSTOM_TOOL_FILE = str(writable_path('Pipeline/custom_tools.json'))
    # regex สำหรับหา flag

    # หน้าที่: เตรียมทะเบียนเครื่องมือและโหลด definitions จาก JSON พร้อมเก็บสถานะข้อผิดพลาด
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.validate_tools (อ้างอิง/callback)
    # ที่มา: Tools/system_check.py::report (อ้างอิง/callback)
    # ที่มา: pages/my_tools.py::available_tool_options (อ้างอิง/callback)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def __init__(self):
        self.load_error = ""
        self._captures = []
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
        

    # หน้าที่: ตรวจ definitions แล้วสร้าง callable สำหรับประกอบคำสั่งของ file/text tools
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.save_custom_tool (เรียกตรง)
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.__init__ (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
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
                # หน้าที่: สร้าง closure ที่ประกอบ executable, params และตำแหน่ง input file
                # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.load_custom_tools (เรียกตรง)
                # Input: command (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                # Input: params (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                # Input: input_mode (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                # Input: input_flag (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                def make_file_tool(
                    command,
                    params,
                    input_mode="positional",
                    input_flag=None
                ):
                    # หน้าที่: คืน argument list ของเครื่องมือตามคำสั่งและค่าที่ closure จับไว้
                    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.load_custom_tools.make_file_tool (อ้างอิง/callback)
                    # Input: file_path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
                    # Input: p (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                    # Closure: command (str) — รับจาก scope PipelineEngine.load_custom_tools.make_file_tool
                    # Closure: input_flag (str | None) — รับจาก scope PipelineEngine.load_custom_tools.make_file_tool
                    # Closure: input_mode (str) — รับจาก scope PipelineEngine.load_custom_tools.make_file_tool
                    # Closure: params (list[str]) — รับจาก scope PipelineEngine.load_custom_tools.make_file_tool
                    # Closure: self (PipelineEngine) — รับจาก scope PipelineEngine.load_custom_tools
                    def tool(file_path, p=None):

                        cmd = [command] + params + self.arguments(p)

                        if file_path:

                            cmd = self.attach_input(cmd, os.fspath(file_path), input_mode, input_flag)

                        return cmd

                    return tool

                # หน้าที่: สร้าง closure ที่ประกอบคำสั่งสำหรับเครื่องมือรับข้อความทาง stdin
                # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.load_custom_tools (เรียกตรง)
                # Input: command (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                # Input: params (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                def make_text_tool(command, params):
                    # หน้าที่: คืน argument list ของเครื่องมือตามคำสั่งและค่าที่ closure จับไว้
                    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.load_custom_tools.make_text_tool (อ้างอิง/callback)
                    # Input: p (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
                    # Closure: command (str) — รับจาก scope PipelineEngine.load_custom_tools.make_text_tool
                    # Closure: params (list[str]) — รับจาก scope PipelineEngine.load_custom_tools.make_text_tool
                    # Closure: self (PipelineEngine) — รับจาก scope PipelineEngine.load_custom_tools
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

    # หน้าที่: แปลงข้อความ arguments ด้วย shlex หรือคัดลอกรายการ tokens ที่ตรวจชนิดแล้ว
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.build_command (เรียกตรง)
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.validate_tools (เรียกตรง)
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.add_tool (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 3 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: value (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def arguments(value):
        if value is None:
            return []
        if isinstance(value, str):
            return shlex.split(value)
        if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
            return list(value)
        raise ValueError("Arguments must be text or a list of strings")

    # หน้าที่: ตรวจ schema หมวด เครื่องมือ input mode และ options ก่อนนำไปใช้งาน
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.load_custom_tools (เรียกตรง)
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.save_custom_tool (เรียกตรง)
    # ที่มา: Tools/system_check.py::report (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: data (Any (JSON; validate_tools ตรวจ dict[str, list[dict]])) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
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

    # หน้าที่: แนบ path แบบ positional, flag หรือ key=value และตรวจ input ที่ขัดกัน
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.load_custom_tools.make_file_tool.tool (เรียกตรง)
    # Input: cmd (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    # Input: mode (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: flag (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
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

    # หน้าที่: เรียก command builder ของ tool แล้วต่อ arguments ที่ต้องอยู่หลัง input
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.command_for (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: params (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: file_path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    # Input: after_params (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def build_command(self, tool, params=None, file_path=None, after_params=None):
        if tool in self.file_tools:
            cmd = self.file_tools[tool](file_path, params)
        elif tool in self.text_tools:
            cmd = self.text_tools[tool](params)
        else:
            raise ValueError(f"Unknown tool: {tool}")
        return cmd + self.arguments(after_params)

    # หน้าที่: รันคำสั่งผ่าน stream capture และห่อ stdout/stderr เป็น CommandResult
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._run_command (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: cmd (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: input_data (bytes | Path | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: cancel_event (threading.Event หรือ object ที่มี is_set() -> bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _communicate(self, cmd, input_data, cancel_event):
        capture = run_capture(cmd, input_data, cancel_event)
        result = CommandResult(capture.stdout, capture.stderr, capture.returncode,
                             stdout_file=capture.stdout_file, stderr_file=capture.stderr_file)
        if capture.stdout_file or capture.stderr_file:
            self._captures.append(capture)
        else:
            capture.close()
        return result

    # หน้าที่: ปิดและนำ capture ที่ไม่มีไฟล์ผลลัพธ์เหลืออยู่ออกจากรายการ
    # ที่มา: pages/pipeline.py::PipelinePage.cleanup_pipeline_artifacts (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def prune_captures(self):
        keep = []
        for capture in self._captures:
            if any(path and path.exists() for path in (capture.stdout_file, capture.stderr_file)):
                keep.append(capture)
            else:
                capture.close()
        self._captures = keep

    # หน้าที่: รัน subprocess จัดการ timeout/cancel/error และสำรวจไฟล์ผลลัพธ์เมื่อร้องขอ
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.run_text_tool (เรียกตรง)
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine.run_file_tool (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.run_tool.worker (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: cmd (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: input_data (bytes | Path | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: input_path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    # Input: detailed (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: cancel_event (threading.Event หรือ object ที่มี is_set() -> bool | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _run_command(self, cmd, input_data=None, input_path=None, detailed=False, cancel_event=None):
        if cancel_event is not None and cancel_event.is_set():
            result = CommandResult(stderr=b"Cancelled")
            return result if detailed else result.stderr
        locations = output_locations(cmd, input_path) if detailed else []
        before, complete_before = snapshot_files(locations)
        try:
            if detailed or cancel_event is not None:
                result = self._communicate(cmd, input_data, cancel_event)
            else:
                process = subprocess.run(
                    cmd, input=input_data, capture_output=True, check=False, timeout=30,
                    env=external_environment(),
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

    # หน้าที่: เรียกเครื่องมือชนิด text โดยส่งข้อมูลเข้า stdin
    # ที่มา: Tools/package_smoke.py::main (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: input_data (bytes | Path | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: params (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: detailed (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def run_text_tool(self, tool, input_data, params=None, detailed=False):

        if tool not in self.text_tools:
            return CommandResult(stderr=b"Unknown text tool") if detailed else b"Unknown text tool"

        cmd = self.text_tools[tool](params) # สร้าง command

        return self._run_command(cmd, input_data=input_data, detailed=detailed)

    # หน้าที่: เรียกเครื่องมือชนิด file โดยส่ง path ผ่าน arguments
    # ที่มา: API/helper ของโมดูลนี้; ผู้เรียกส่ง arguments หรือเรียกผ่าน callback/interface
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: file_path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
    # Input: params (str | list[str] | tuple[str, ...] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: detailed (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def run_file_tool(self, tool, file_path, params=None, detailed=False):

        if tool not in self.file_tools:
            return CommandResult(stderr=b"Unknown file tool") if detailed else b"Unknown file tool"

        cmd = self.file_tools[tool](file_path, params)

        return self._run_command(cmd, input_path=file_path, detailed=detailed)
    # หน้าที่: คืน flag แรกที่จับรูปแบบได้จากผลลัพธ์
    # ที่มา: API/helper ของโมดูลนี้; ผู้เรียกส่ง arguments หรือเรียกผ่าน callback/interface
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def check_flag(self, text):
        return find_first_flag(text)
    
    # หน้าที่: ลงทะเบียน command builder ของเครื่องมือใหม่ในหน่วยความจำ
    # ที่มา: API/helper ของโมดูลนี้; ผู้เรียกส่ง arguments หรือเรียกผ่าน callback/interface
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: command (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: mode (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def add_tool(self, name, command, mode):

        if mode == "file":

            self.file_tools[name] = lambda f, p=None, c=command: \
                [c] + self.arguments(p) + [f]

        else:

            self.text_tools[name] = lambda p=None, c=command: \
                [c] + self.arguments(p)
            
    # หน้าที่: ตรวจและบันทึก definition เครื่องมือใหม่ลง JSON แล้วโหลดทะเบียนใหม่
    # ที่มา: pages/pipeline.py::PipelinePage.open_add_tool_window.save_tool (เรียกตรง)
    # Input: self (PipelineEngine) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: command (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: mode (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: category (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: description (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
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
