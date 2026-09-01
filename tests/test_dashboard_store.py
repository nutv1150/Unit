import os
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from Tools.dashboard_store import DashboardStore


def test_dashboard_store():
    print("=" * 64)
    print("UNIT DASHBOARD STORE")
    print("=" * 64)

    with tempfile.TemporaryDirectory() as temp_dir:
        state_path = os.path.join(temp_dir, "dashboard_state.json")
        sample_file = os.path.join(temp_dir, "evidence.bin")
        with open(sample_file, "wb") as file_obj:
            file_obj.write(b"sample")

        store = DashboardStore(state_path)
        assert store.get_active_competition() == "General"

        store.add_competition("TCTT2026")
        store.add_category("Forensics")
        store.save_favorite(
            "strings",
            "pipeline_tool:strings",
            "Forensics",
            "Ctrl+4",
        )

        store.record_event(
            tool="strings",
            category="File Inspection",
            action="Analyze File",
            file_path=sample_file,
            flags=["TCTT2026{dashboard_test}"],
        )
        store.record_event(
            tool="Base64",
            category="Data Hashing",
            action="Decode",
            status="failed",
            details="invalid input",
        )

        snapshot = store.get_snapshot()
        assert snapshot["active_competition"] == "TCTT2026"
        assert snapshot["totals"]["operations"] == 2
        assert snapshot["totals"]["success"] == 1
        assert snapshot["totals"]["failed"] == 1
        assert snapshot["totals"]["flags"] == 1
        assert snapshot["totals"]["files"] == 1
        assert snapshot["top_tools"][0] == ("strings", 1)
        assert snapshot["recent_files"][0]["path"] == sample_file

        competition = next(
            row
            for row in snapshot["competition_stats"]
            if row["name"] == "TCTT2026"
        )
        assert competition["operations"] == 2
        assert competition["flags"] == 1
        assert competition["files"] == 1

        # โหลดใหม่เพื่อยืนยันว่า state คงอยู่ข้าม instance
        reloaded = DashboardStore(state_path).get_snapshot()
        assert reloaded["totals"] == snapshot["totals"]
        assert any(
            item["target"] == "pipeline_tool:strings"
            for item in reloaded["favorites"]
        )

    print("[PASS] Persistent usage statistics")
    print("[PASS] Competition statistics")
    print("[PASS] Recent files")
    print("[PASS] Favorites, shortcuts, and custom categories")
    print("=" * 64)


if __name__ == "__main__":
    test_dashboard_store()
