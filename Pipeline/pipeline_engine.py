import subprocess
import json
import os
import shlex

from Tools.flag_detector import find_first_flag
from Pipeline.output_files import CommandResult, output_locations, snapshot_files, changed_files

class PipelineEngine:
    # path ของไฟล์นี้
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # path ของไฟล์เก็บ tool
    CUSTOM_TOOL_FILE = os.path.join(BASE_DIR, "custom_tools.json")
    # regex สำหรับหา flag

    def __init__(self):
        self.file_tools = {} # tool ที่ใช้กับไฟล์
        self.text_tools = {} # tool ที่ใช้กับ text
        self.tool_descriptions = {} 
        self.tool_options = {} # เก็บ options ของ tool
        
        self.tool_input_modes = {}
        self.tool_input_flags = {}
        

        self.load_custom_tools() # โหลด tool จาก JSON
        

    def load_custom_tools(self):

        if not os.path.exists(self.CUSTOM_TOOL_FILE):
            return # ถ้าไม่มีไฟล์ก็จบ

        with open(self.CUSTOM_TOOL_FILE) as f:
            data = json.load(f) # อ่าน JSON

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

                        cmd = [command] + params

                        if p:
                            cmd += shlex.split(p)

                        if file_path:

                            if (
                                input_mode == "flag"
                                and input_flag
                            ):
                                cmd += [
                                    input_flag,
                                    file_path
                                ]

                            else:
                                cmd += [
                                    file_path
                                ]

                        return cmd

                    return tool

                def make_text_tool(command, params):
                    def tool(p=None):
                        return [command] + params + (shlex.split(p) if p else [])
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

    def _run_command(self, cmd, input_data=None, input_path=None, detailed=False):
        locations = output_locations(cmd, input_path) if detailed else []
        before, complete_before = snapshot_files(locations)
        try:
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
                result.discovery_note = "ตรวจหาไฟล์ได้ไม่ครบ กรุณาเลือกไฟล์ผลลัพธ์ด้วย Browse result file"
        return result if detailed else result.stdout + result.stderr

    def run_text_tool(self, tool, input_data, params=None, detailed=False):

        if tool not in self.text_tools:
            return CommandResult(stderr=b"Unknown text tool") if detailed else b"Unknown text tool"

        cmd = self.text_tools[tool](params) # สร้าง command
        print("RUN CMD:", cmd)

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
                [c] + (p.split() if p else []) + [f]

        else:

            self.text_tools[name] = lambda p=None, c=command: \
                [c] + (p.split() if p else [])
            
    def save_custom_tool(self, name, command, mode, category, description=""):
        # ปรับปรุงให้บันทึก description ลง JSON ด้วย
        if os.path.exists(self.CUSTOM_TOOL_FILE):
            with open(self.CUSTOM_TOOL_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {}

        if category not in data:
            data[category] = []

        data[category].append({
            "name": name,
            "command": command,
            "mode": mode,
            "description": description, # คำอธิบายจากระบบ
            "user_description": ""      # เว้นว่างไว้สำหรับรอให้ User มาเติมใน Pipeline
        })

        with open(self.CUSTOM_TOOL_FILE, "w") as f:
            json.dump(data, f, indent=4)
