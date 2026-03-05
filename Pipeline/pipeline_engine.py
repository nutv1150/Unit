import subprocess
import re
import json
import os


class PipelineEngine:

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CUSTOM_TOOL_FILE = os.path.join(BASE_DIR, "custom_tools.json")

    FLAG_PATTERN = r"TCTT\{.*?\}|flag\{.*?\}"

    def __init__(self):

        self.file_tools = {}
        self.text_tools = {}

        self.load_custom_tools()


    def load_custom_tools(self):

        if not os.path.exists(self.CUSTOM_TOOL_FILE):
            return

        with open(self.CUSTOM_TOOL_FILE) as f:
            data = json.load(f)

        for category in data:

            for tool in data[category]:

                name = tool["name"]
                command = tool["command"]
                mode = tool["mode"]
                params = tool.get("params", [])

                if mode == "file":

                    self.file_tools[name] = lambda f, p=None, c=command, pa=params: \
                        [c] + pa + (p.split() if p else []) + [f]

                else:

                    self.text_tools[name] = lambda p=None, c=command, pa=params: \
                        [c] + pa + (p.split() if p else [])

    def run_text_tool(self, tool, input_data, params=None):

        if tool not in self.text_tools:
            return b"Unknown text tool"

        cmd = self.text_tools[tool](params)

        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True
        )

        return result.stdout + result.stderr

    def run_file_tool(self, tool, file_path, params=None):

        if tool not in self.file_tools:
            return b"Unknown file tool"

        cmd = self.file_tools[tool](file_path, params)

        result = subprocess.run(
            cmd,
            capture_output=True,
            check=False
        )

        return result.stdout + result.stderr
    def check_flag(self, text):

        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")

        match = re.search(self.FLAG_PATTERN, text)

        return match.group() if match else None
    
    def add_tool(self, name, command, mode):

        if mode == "file":

            self.file_tools[name] = lambda f, p=None, c=command: \
                [c] + (p.split() if p else []) + [f]

        else:

            self.text_tools[name] = lambda p=None, c=command: \
                [c] + (p.split() if p else [])
            
    def save_custom_tool(self, name, command, mode, category):

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
            "mode": mode
        })

        with open(self.CUSTOM_TOOL_FILE, "w") as f:
            json.dump(data, f, indent=4)