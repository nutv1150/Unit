import base64
import os
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("DISPLAY"), "Tk GUI tests require a display (use xvfb-run)")
class CodecGuiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        cls.ctk = ctk
        from pages.data_hash import DataHashPage
        cls.DataHashPage = DataHashPage

    def setUp(self):
        try:
            self.root = self.ctk.CTk()
        except Exception as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        self.root.withdraw()
        self.page = self.DataHashPage(self.root)
        self.page.pack()

    def tearDown(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.tk.call('after', 'cancel', callback)
        self.root.destroy()

    def _input(self, value):
        self.page.input_box.delete("1.0", "end")
        self.page.input_box.insert("1.0", value)
        self.page.process_data()

    def test_hash_preserves_exact_whitespace(self):
        self.page.set_mode("Hash")
        self.page.algo_menu.set("sha256")
        value = "  leading and trailing  \n"
        self._input(value)
        import hashlib
        self.assertEqual(self.page.output_box.get("1.0", "end-1c"), hashlib.sha256(value.encode()).hexdigest())

    def test_binary_display_and_raw_save(self):
        self.page.set_mode("Decode")
        self.page.algo_menu.set("Base64")
        raw = b"\x00\xff\x80\x01"
        self._input(base64.b64encode(raw).decode())
        shown = self.page.output_box.get("1.0", "end-1c")
        self.assertIn("BINARY HEX", shown)
        self.assertIn("4 bytes", shown)
        with tempfile.NamedTemporaryFile(delete=False) as target:
            path = target.name
        try:
            with patch("pages.data_hash.filedialog.asksaveasfilename", return_value=path):
                self.page.save_raw_output()
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), raw)
        finally:
            os.unlink(path)

    def test_text_flow(self):
        self.page.set_mode("Decode")
        self.page.algo_menu.set("Base64")
        self._input("SGVsbG8=")
        self.assertEqual(self.page.output_box.get("1.0", "end-1c"), "Hello")


if __name__ == "__main__":
    unittest.main()
