import subprocess
import re
import json
import os



class PipelineEngine:

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CUSTOM_TOOL_FILE = os.path.join(BASE_DIR, "custom_tools.json")

    def __init__(self):

        self.file_tools = {
            "file": lambda f, p: ["file", f],
            "strings": lambda f, p: ["strings", f],
            "binwalk": lambda f, p: ["binwalk", f],
            "md5sum": lambda f, p: ["md5sum", f],
            "zsteg": lambda f, p: ["zsteg", f],
            "zbarimg": lambda f, p: ["zbarimg", f],
        }

        self.text_tools = {
            "grep": lambda p: ["grep", p],
            "base64_decode": lambda p: ["base64", "-d", "-i"],
            "unique": lambda p: ["uniq"],
        }
        self.load_custom_tools()

    FLAG_PATTERN = r"TCTT\{.*?\}|flag\{.*?\}"

    def run_file_tool(self, tool, file_path, params=None):

        if tool not in self.file_tools:
            return b"Unknown file tool"

        cmd = self.file_tools[tool](file_path, params)

        result = subprocess.run(cmd, capture_output=True)
        return result.stdout
    
    def run_text_tool(self, tool, input_data, params=None):

        if tool not in self.text_tools:
            return b"Unknown text tool"

        cmd = self.text_tools[tool](params)

        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True
        )

        return result.stdout

    def build_file_command(self, tool, file_path, params):
        if tool == "file":
            return ["file", file_path]
        
        elif tool == "strings":
            return ["strings", file_path]

        elif tool == "binwalk":
            return ["binwalk", file_path]

        elif tool == "md5sum":
            return ["md5sum", file_path]

        elif tool == "zsteg":
            return ["zsteg", file_path]

        elif tool == "zbarimg":
            return ["zbarimg", file_path]

        raise ValueError("Unknown file tool")

    def build_text_command(self, tool, params):
        if tool == "grep":
            if not params:
                raise ValueError("grep requires pattern")
            return ["grep", params]

        elif tool == "base64_decode":
            return ["base64", "-d", "-i"]

        elif tool == "unique":
            return ["uniq"]

        raise ValueError("Unknown text tool")

    def check_flag(self, text):

        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")

        match = re.search(self.FLAG_PATTERN, text)
        return match.group() if match else None
    
    def add_tool(self, name, command, mode):

        if mode == "file":
            self.file_tools[name] = lambda f, p: [command, f]
        else:
            self.text_tools[name] = lambda p: [command]

    def save_custom_tool(self, name, command, mode):
        tools = []

        if os.path.exists(self.CUSTOM_TOOL_FILE):
            with open(self.CUSTOM_TOOL_FILE, "r") as f:
                tools = json.load(f)

        tools.append({
            "name": name,
            "command": command,
            "mode": mode
        })

        with open(self.CUSTOM_TOOL_FILE, "w") as f:
            json.dump(tools, f, indent=4)
    
    def load_custom_tools(self):

        if not os.path.exists(self.CUSTOM_TOOL_FILE):
            return

        with open(self.CUSTOM_TOOL_FILE, "r") as f:
            try:
                data = json.load(f)
            except:
                return

        for tool in data:
            self.add_tool(
                tool["name"],
                tool["command"],
                tool["mode"]
            )
    