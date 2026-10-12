import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import importlib.util
_spec = importlib.util.spec_from_file_location("unit_packaging_build", ROOT / "packaging" / "build.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
_manifest, build = _module._manifest, _module.build


class PackagingBuildTests(unittest.TestCase):
    def test_manifest_has_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _manifest(out, "9.9.9")
            payload = json.loads((out / "manifest.json").read_text())
            self.assertEqual(payload["version"], "9.9.9")
            self.assertTrue(payload["packages"])

    def test_build_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "UNIT-1.0.0-linux-x86_64"
            target.mkdir()
            with self.assertRaises(FileExistsError):
                build(Path(tmp), "1.0.0", archive=False)


if __name__ == "__main__":
    unittest.main()
