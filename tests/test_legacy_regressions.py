"""Include standalone legacy checks in the standard unittest discovery command."""
import runpy
import unittest
from pathlib import Path


class LegacyRegressionTests(unittest.TestCase):
    def test_standalone_checks(self):
        for name, entry in [('test_artifact_bridge.py', 'main'),
                            ('test_artifact_pipeline_compat.py', 'main'),
                            ('test_binary_decode.py', 'main'),
                            ('test_smart_hex_parser.py', 'main'),
                            ('test_flag_detector.py', 'test_flag_detector'),
                            ('test_dashboard_store.py', 'test_dashboard_store')]:
            with self.subTest(script=name):
                runpy.run_path(str(Path(__file__).with_name(name)))[entry]()
