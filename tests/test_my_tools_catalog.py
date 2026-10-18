import json
import tempfile
import unittest
from pathlib import Path

from Tools.tool_catalog import (
    DATA_HASH_BITWISE_ALGORITHMS,
    DATA_HASH_DECODE_ALGORITHMS,
    FILE_INSPECTION_TOOLS,
)
from app import UNITApp
from pages.my_tools import available_tool_options


class MyToolsCatalogTests(unittest.TestCase):
    # หน้าที่: ตรวจจำนวน/ชื่อ Decode, Bitwise และ File Inspection ใน catalog
    # ที่มา: unittest/test runner เรียกกรณีทดสอบนี้
    # Input: self (MyToolsCatalogTests) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def test_complete_static_catalog(self):
        self.assertEqual(19, len(DATA_HASH_DECODE_ALGORITHMS))
        self.assertEqual(
            ("XOR Mask", "XOR Unmask", "OR Mask", "AND Mask"),
            DATA_HASH_BITWISE_ALGORITHMS,
        )
        self.assertEqual(7, len(FILE_INSPECTION_TOOLS))

    # หน้าที่: ตรวจว่าตัวเลือก Pipeline อ่าน tools จาก JSON รวมทั้ง OpenSSL
    # ที่มา: unittest/test runner เรียกกรณีทดสอบนี้
    # Input: self (MyToolsCatalogTests) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def test_pipeline_tools_are_loaded_from_config(self):
        config = {
            "Cryptography": [
                {
                    "name": "openssl enc",
                    "command": "openssl",
                    "mode": "file",
                    "params": ["enc"],
                    "input_mode": "flag",
                    "input_flag": "-in",
                    "options": [],
                }
            ],
            "Programming": [
                {
                    "name": "grep",
                    "command": "grep",
                    "mode": "text",
                    "options": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tools.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            options = available_tool_options(path)

        pipeline = [
            (tool["name"], tool.get("sub"), tool.get("category"))
            for tool in options
            if tool["page"] == "Pipeline" and tool.get("sub")
        ]
        self.assertEqual(
            [("openssl enc", "openssl enc", "Cryptography"),
             ("grep", "grep", "Programming")],
            pipeline,
        )


class NavigationTests(unittest.TestCase):
    class DataPage:
        # หน้าที่: เตรียมสถานะเริ่มต้นของหน้าจำลองเพื่อทดสอบ navigation โดยไม่สร้าง Tk widgets
        # ที่มา: Python เรียกผ่านวงจรชีวิตหรือ protocol ของ object
        # Input: self (DataPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        def __init__(self):
            self.calls = []

        # หน้าที่: เก็บโหมดที่ navigate_to ขอให้หน้าจำลองเลือก
        # ที่มา: test fixture/UNITApp.navigate_to เรียกผ่าน interface ของหน้าจำลอง
        # Input: self (DataPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        # Input: value (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        def set_mode(self, value):
            self.calls.append(("mode", value))

        # หน้าที่: เก็บอัลกอริทึมที่ navigate_to ขอให้หน้าจำลองเลือก
        # ที่มา: test fixture/UNITApp.navigate_to เรียกผ่าน interface ของหน้าจำลอง
        # Input: self (DataPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        # Input: value (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        def select_quick_algo(self, value):
            self.calls.append(("algo", value))

    class FilePage:
        class Menu:
            # หน้าที่: เตรียมสถานะเริ่มต้นของหน้าจำลองเพื่อทดสอบ navigation โดยไม่สร้าง Tk widgets
            # ที่มา: Python เรียกผ่านวงจรชีวิตหรือ protocol ของ object
            # Input: self (Menu) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
            def __init__(self):
                self.value = None

            # หน้าที่: เก็บค่าที่ส่งเข้ามาแทนการตั้ง dropdown จริง
            # ที่มา: test fixture/UNITApp.navigate_to เรียกผ่าน interface ของหน้าจำลอง
            # Input: self (Menu) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
            # Input: value (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
            def set(self, value):
                self.value = value

        # หน้าที่: เตรียมสถานะเริ่มต้นของหน้าจำลองเพื่อทดสอบ navigation โดยไม่สร้าง Tk widgets
        # ที่มา: Python เรียกผ่านวงจรชีวิตหรือ protocol ของ object
        # Input: self (FilePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        def __init__(self):
            self.tool_menu = self.Menu()
            self.changed = None

        # หน้าที่: เก็บ tool ที่ navigation ขอให้ File Inspection จำลองเลือก
        # ที่มา: test fixture/UNITApp.navigate_to เรียกผ่าน interface ของหน้าจำลอง
        # Input: self (FilePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        # Input: value (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        def on_tool_change(self, value):
            self.changed = value

    class PipelinePage:
        # หน้าที่: เตรียมสถานะเริ่มต้นของหน้าจำลองเพื่อทดสอบ navigation โดยไม่สร้าง Tk widgets
        # ที่มา: Python เรียกผ่านวงจรชีวิตหรือ protocol ของ object
        # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        def __init__(self):
            self.added = []

        # หน้าที่: เก็บชื่อ node ที่ navigation ขอเพิ่มใน Pipeline จำลอง
        # ที่มา: test fixture/UNITApp.navigate_to เรียกผ่าน interface ของหน้าจำลอง
        # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        # Input: value (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        def add_tool_node(self, value):
            self.added.append(value)

    class FakeApp:
        # หน้าที่: เตรียมสถานะเริ่มต้นของหน้าจำลองเพื่อทดสอบ navigation โดยไม่สร้าง Tk widgets
        # ที่มา: Python เรียกผ่านวงจรชีวิตหรือ protocol ของ object
        # Input: self (FakeApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        def __init__(self):
            self.pages = {
                "Data Hashing": NavigationTests.DataPage(),
                "File Inspection": NavigationTests.FilePage(),
                "Pipeline": NavigationTests.PipelinePage(),
            }
            self.switched = []

        # หน้าที่: เก็บชื่อหน้าที่ navigation ขอเปิดโดยไม่สร้างหน้าต่างจริง
        # ที่มา: test fixture/UNITApp.navigate_to เรียกผ่าน interface ของหน้าจำลอง
        # Input: self (FakeApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
        # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        def switch_page(self, name):
            self.switched.append(name)

    # หน้าที่: ตรวจ routing ของ XOR Unmask, Decode, File Inspection และ OpenSSL
    # ที่มา: unittest/test runner เรียกกรณีทดสอบนี้
    # Input: self (NavigationTests) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def test_shortcuts_select_requested_tools(self):
        app = self.FakeApp()
        UNITApp.navigate_to(app, "Data Hashing", "XOR Unmask", "Bitwise")
        UNITApp.navigate_to(app, "Data Hashing", "Base45", "Decode")
        UNITApp.navigate_to(app, "File Inspection", "steghide Analysis")
        UNITApp.navigate_to(app, "Pipeline", "openssl enc")

        self.assertEqual(
            [("mode", "Bitwise"), ("algo", "XOR Unmask"),
             ("mode", "Decode"), ("algo", "Base45")],
            app.pages["Data Hashing"].calls,
        )
        self.assertEqual(
            "steghide Analysis", app.pages["File Inspection"].tool_menu.value
        )
        self.assertEqual("steghide Analysis", app.pages["File Inspection"].changed)
        self.assertEqual(["openssl enc"], app.pages["Pipeline"].added)

    # หน้าที่: ตรวจว่าทางลัด XOR รูปแบบเดิมยังเปิด XOR Mask ได้
    # ที่มา: unittest/test runner เรียกกรณีทดสอบนี้
    # Input: self (NavigationTests) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def test_legacy_xor_shortcut_still_opens_xor_mask(self):
        app = self.FakeApp()
        UNITApp.navigate_to(app, "Data Hashing", "XOR")
        self.assertEqual(
            [("mode", "Bitwise"), ("algo", "XOR Mask")],
            app.pages["Data Hashing"].calls,
        )


if __name__ == "__main__":
    unittest.main()
