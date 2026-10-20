import json
import os
from copy import deepcopy
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from Pipeline.config_store import saved_pipelines, validate_saved_pipelines, write_json
from Pipeline.saved_runs import completed_steps, delete_recipe, save_recipe, step_recipe


def settings(source="previous"):
    return {
        "input_source": source,
        "option_values": [
            {"flag": "-n", "type": "checkbox", "value": True},
            {"flag": "-v", "type": "checkbox", "value": False},
            {"flag": "", "type": "text", "value": "flag{"},
        ],
        "before_enabled": True,
        "before_rows": [{"flag": "--color", "type": "text", "value": "never"}],
        "after_enabled": False,
        "after_rows": [{"flag": "--label", "type": "text", "value": "a b"}],
    }


def recipe(name="Saved"):
    return {"pipeline_name": name, "steps": [
        {"name": "grep", "params": "", "options": [], "run_settings": settings()}
    ]}


class SavedStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "saved.json"

    def test_create_edit_rename_delete_preserves_other_entries(self):
        first = recipe()
        save_recipe(self.path, first)
        legacy = {"pipeline_name": "Legacy", "steps": [{"name": "file", "params": "-b"}]}
        save_recipe(self.path, legacy)
        changed = deepcopy(first)
        changed["pipeline_name"] = "Renamed"
        changed["steps"][0]["run_settings"]["option_values"][2]["value"] = "new value"
        save_recipe(self.path, changed, "Saved", first)
        self.assertEqual([changed, legacy], saved_pipelines(self.path)["saved_pipelines"])
        delete_recipe(self.path, "Renamed", changed)
        self.assertEqual([legacy], saved_pipelines(self.path)["saved_pipelines"])

    def test_duplicate_blank_and_empty_steps_do_not_overwrite(self):
        save_recipe(self.path, recipe())
        original = self.path.read_bytes()
        for entry in (recipe(), recipe("  "), {"pipeline_name": "Empty", "steps": []}):
            with self.assertRaises(ValueError):
                save_recipe(self.path, entry)
            self.assertEqual(original, self.path.read_bytes())

    def test_corrupt_file_is_not_replaced_by_save_or_delete(self):
        self.path.write_text("{invalid", encoding="utf-8")
        for action in (lambda: save_recipe(self.path, recipe()), lambda: delete_recipe(self.path, "Saved")):
            with self.assertRaises(ValueError):
                action()
            self.assertEqual("{invalid", self.path.read_text())

    def test_failed_atomic_write_leaves_original_intact(self):
        save_recipe(self.path, recipe())
        original = self.path.read_bytes()
        with patch("Pipeline.config_store.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                save_recipe(self.path, recipe("New"))
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual([self.path], list(self.path.parent.iterdir()))

    def test_stale_editor_and_delete_do_not_overwrite_newer_changes(self):
        old = recipe()
        save_recipe(self.path, old)
        changed = recipe()
        changed["steps"][0]["params"] = "-i"
        save_recipe(self.path, changed, "Saved", old)
        for action in (lambda: save_recipe(self.path, old, "Saved", old),
                       lambda: delete_recipe(self.path, "Saved", old)):
            with self.assertRaises(ValueError):
                action()
        self.assertEqual(changed, saved_pipelines(self.path)["saved_pipelines"][0])

    def test_run_settings_validation_and_legacy_compatibility(self):
        validate_saved_pipelines({"saved_pipelines": [
            {"pipeline_name": "Old", "steps": [{"name": "grep", "options": []}]}]})
        for key, value in (("option_values", "bad"), ("before_enabled", "yes"),
                           ("input_source", "/tmp/input")):
            entry = recipe()
            entry["steps"][0]["run_settings"][key] = value
            with self.assertRaises(ValueError):
                validate_saved_pipelines({"saved_pipelines": [entry]})
        entry = recipe()
        entry["steps"][0]["run_settings"]["option_values"][0]["value"] = "False"
        with self.assertRaises(ValueError):
            validate_saved_pipelines({"saved_pipelines": [entry]})

    def test_snapshot_excludes_widgets_and_results_and_is_independent(self):
        node = dict(name="grep", frame=object(), output=b"secret", run_settings=settings())
        snap = step_recipe(node)
        node["_successful_step"] = snap
        result = completed_steps([node])
        node["run_settings"]["option_values"][2]["value"] = "changed"
        self.assertEqual("flag{", result[0]["run_settings"]["option_values"][2]["value"])
        self.assertNotIn("frame", result[0])
        self.assertNotIn("output", result[0])
        self.assertIsNone(completed_steps([node, {"name": "file"}]))
        self.assertIsNone(completed_steps([]))


@unittest.skipUnless(os.environ.get("DISPLAY"), "GUI regression tests require Xvfb or a display")
class SavedPipelineGuiTests(unittest.TestCase):
    def setUp(self):
        import customtkinter as ctk
        from pages.pipeline import PipelinePage
        from Pipeline.pipeline_engine import PipelineEngine
        self.ctk = ctk
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root_path = Path(self.temp.name)
        self.path = self.root_path / "Pipeline/saved_pipelines.json"
        self.input_path = self.root_path / "sample.txt"
        self.input_path.write_text("hello world\nflag{example}\n")
        tool_path = self.root_path / "Pipeline/custom_tools.json"
        tool_path.parent.mkdir()
        tool_path.write_bytes((Path(__file__).resolve().parents[1] / "Pipeline/custom_tools.json").read_bytes())
        previous_cwd = Path.cwd()
        os.chdir(self.root_path)
        self.addCleanup(os.chdir, previous_cwd)
        self.env = patch.dict(os.environ, {"UNIT_DATA_HOME": str(self.root_path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.tools_patch = patch.object(PipelineEngine, "CUSTOM_TOOL_FILE", str(tool_path))
        self.tools_patch.start()
        self.addCleanup(self.tools_patch.stop)
        self.root = ctk.CTk()
        self.root.geometry("1200x800")
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args[1])
        host = ctk.CTkFrame(self.root)
        host.pack(fill="both", expand=True)
        self.page = PipelinePage(host)
        self.page.pack(fill="both", expand=True)
        self.root.update()

    def tearDown(self):
        self.page.cleanup_pipeline_artifacts()
        # Cancel pending CTk redraw timers before destroying this test's interpreter.
        for timer in self.root.tk.call("after", "info"):
            self.root.tk.call("after", "cancel", timer)
        self.root.destroy()
        self.assertEqual([], self.errors, f"Tk callback errors: {self.errors}")

    def widgets(self, parent, kind=None):
        found = []
        for child in parent.winfo_children():
            if kind is None or isinstance(child, kind):
                found.append(child)
            found.extend(self.widgets(child, kind))
        return found

    def button(self, parent, text):
        return next(w for w in self.widgets(parent, self.ctk.CTkButton) if w.cget("text") == text)

    def entry(self, parent, label):
        for widget in self.widgets(parent, self.ctk.CTkLabel):
            if widget.cget("text") == label:
                siblings = list(widget.master.winfo_children())
                for sibling in siblings[siblings.index(widget) + 1:]:
                    if isinstance(sibling, self.ctk.CTkEntry):
                        return sibling
        raise AssertionError(f"No entry for {label}")

    def set_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def wait_for(self, condition, timeout=4):
        end = time.monotonic() + timeout
        while not condition():
            self.root.update()
            if self.errors:
                raise self.errors[0]
            if time.monotonic() > end:
                self.fail("Timed out waiting for GUI worker")
            time.sleep(.01)
        self.root.update()

    def run_step(self, win):
        self.button(win, "Run").invoke()
        self.wait_for(lambda: self.button(win, "Run").cget("state") == "normal")

    def test_real_auto_save_load_replays_options_and_forwarding(self):
        """Real strings → grep, then reload and run the saved recipe again."""
        self.page.add_tool_node("strings")
        self.page.add_tool_node("grep")
        windows = []

        def drive(win):
            index = len(windows)
            windows.append(win.title())
            self.root.update()
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            if index == 0:
                self.set_entry(self.widgets(win, self.ctk.CTkEntry)[0], str(self.input_path))
                self.set_entry(self.entry(win, "-n:"), "6")
            else:
                self.set_entry(self.entry(win, ":"), "flag{")
                checks = self.widgets(win, self.ctk.CTkCheckBox)
                next(c for c in checks if c.cget("text").startswith("-n")).toggle()
            self.run_step(win)
            self.assertEqual(index == 1, bool(self.button(win, "Save Pipeline").winfo_ismapped()))
            self.button(win, "Next" if index == 0 else "Close").invoke()

        with patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        self.assertEqual(2, len(windows))
        self.assertIn(b"flag{example}", self.page.run_logs[-1]["output"])
        original_steps = deepcopy(self.page._completed_recipe)
        self.assertEqual("6", original_steps[0]["run_settings"]["option_values"][0]["value"])
        self.assertEqual("previous", original_steps[1]["run_settings"]["input_source"])
        dialog = self.page.open_save_pipeline(original_steps)
        dialog.name_var.set("Find flag")
        dialog.save()
        self.assertEqual(2, len(self.page.nodes))
        self.assertTrue(self.button(self.page.tools_panel, "🔨").winfo_exists())
        self.assertTrue(self.button(self.page.tools_panel, "🗑️").winfo_exists())
        self.assertTrue(self.button(self.page.tools_panel, "+ Add Tools").winfo_exists())
        self.assertTrue(self.page.load_saved_pipeline_to_canvas("Find flag"))
        rerun_index = [0]

        def replay(win):
            index = rerun_index[0]
            rerun_index[0] += 1
            if index == 0:
                self.set_entry(self.widgets(win, self.ctk.CTkEntry)[0], str(self.input_path))
                self.assertEqual("6", self.entry(win, "-n:").get())
            else:
                self.assertEqual("flag{", self.entry(win, ":").get())
            self.run_step(win)
            self.button(win, "Next" if index == 0 else "Close").invoke()

        with patch.object(self.page, "wait_window", side_effect=replay):
            self.page.run_pipeline()
        self.assertEqual(original_steps, self.page._completed_recipe)
        self.assertIn(b"2:flag{example}", self.page.run_logs[-1]["output"])

    def test_failed_retry_dirty_options_and_cancel_never_save_stale_success(self):
        from Pipeline.output_files import CommandResult
        self.page.add_tool_node("grep")
        node = self.page.nodes[0]

        def drive(win):
            self.set_entry(self.widgets(win, self.ctk.CTkEntry)[0], "flag{example}")
            pattern = self.entry(win, ":")
            self.set_entry(pattern, "flag{")
            self.run_step(win)
            self.assertTrue(self.button(win, "Save Pipeline").winfo_ismapped())
            self.set_entry(pattern, "changed")
            self.root.update()
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            self.assertNotIn("_successful_step", node)
            self.run_step(win)  # failed retry
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            self.assertNotIn("_successful_step", node)
            self.button(win, "Close").invoke()

        with patch.object(self.page.engine, "_run_command", side_effect=[
            CommandResult(stdout=b"yes", returncode=0), CommandResult(stderr=b"failed", returncode=1)
        ]), patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        self.assertIsNone(self.page._completed_recipe)
        self.assertEqual([], self.page.run_logs)

        def cancel_worker(*args, cancel_event, **kwargs):
            cancel_event.wait(3)
            return CommandResult(returncode=-15)

        def cancel(win):
            self.set_entry(self.entry(win, ":"), "flag")
            self.button(win, "Run").invoke()
            self.button(win, "Cancel").invoke()
            self.wait_for(lambda: self.button(win, "Run").cget("state") == "normal")
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            self.button(win, "Close").invoke()

        with patch.object(self.page.engine, "_run_command", side_effect=cancel_worker), \
                patch.object(self.page, "wait_window", side_effect=cancel):
            self.page.run_pipeline()
        self.assertIsNone(self.page._completed_recipe)

    def test_step_continue_finish_and_latest_successful_retry(self):
        from Pipeline.output_files import CommandResult
        self.page.set_pipeline_mode("Step")
        self.page.add_tool_node("grep")
        count = [0]

        def drive(win):
            index = count[0]
            count[0] += 1
            self.set_entry(self.entry(win, ":"), "first" if index == 0 else "last")
            self.run_step(win)
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            if index == 0:
                self.set_entry(self.entry(win, ":"), "latest")
                self.run_step(win)
                self.widgets(win, self.ctk.CTkComboBox)[0].set("grep")
                self.button(win, "Continue").invoke()
            else:
                self.button(win, "Finish").invoke()

        with patch.object(self.page.engine, "_run_command", return_value=CommandResult(stdout=b"text", returncode=0)), \
                patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        steps = self.page._completed_recipe
        self.assertEqual(2, len(steps))
        self.assertEqual("latest", steps[0]["run_settings"]["option_values"][-1]["value"])
        self.assertEqual("last", steps[1]["run_settings"]["option_values"][-1]["value"])
        self.assertEqual(2, len(self.page.run_logs))
        self.assertEqual("Step", self.page.pipeline_mode)
        self.assertFalse(self.page._pipeline_running)

    def test_edit_cancel_save_rename_delete_leave_canvas_untouched(self):
        save_recipe(self.path, recipe())
        self.page.add_tool_node("file")
        node = self.page.nodes[0]
        self.page.run_logs = [{"tool": "file", "output": b"keep"}]
        dialog = self.page.edit_saved_pipeline("Saved")
        dialog.name_var.set("Canceled")
        dialog.destroy()
        self.assertEqual("Saved", saved_pipelines(self.path)["saved_pipelines"][0]["pipeline_name"])
        dialog = self.page.edit_saved_pipeline("Saved")
        dialog.name_var.set("Renamed")
        dialog.option_vars[-1][2].set("changed")
        dialog.manual_vars["after"][0].set(True)
        dialog.save()
        entry = saved_pipelines(self.path)["saved_pipelines"][0]
        self.assertEqual("Renamed", entry["pipeline_name"])
        self.assertEqual("changed", entry["steps"][0]["run_settings"]["option_values"][-1]["value"])
        self.assertTrue(entry["steps"][0]["run_settings"]["after_enabled"])
        self.assertIs(node, self.page.nodes[0])
        self.assertEqual(b"keep", self.page.run_logs[0]["output"])
        with patch("pages.pipeline.messagebox.askyesno", return_value=False):
            self.page.delete_saved_pipeline("Renamed")
        self.assertEqual(1, len(saved_pipelines(self.path)["saved_pipelines"]))
        with patch("pages.pipeline.messagebox.askyesno", return_value=True):
            self.page.delete_saved_pipeline("Renamed")
        self.assertEqual([], saved_pipelines(self.path)["saved_pipelines"])
        self.assertIs(node, self.page.nodes[0])
        self.assertTrue(node["frame"].winfo_exists())

    def test_manual_before_after_file_options_and_params_restore_without_duplication(self):
        from Pipeline.output_files import CommandResult
        entry = recipe()
        step = entry["steps"][0]
        step["params"] = "-i"
        step["options"] = [{"flag": "--test-file", "type": "file"}]
        step["run_settings"]["option_values"].append(
            {"flag": "--test-file", "type": "file", "value": "/tmp/file with spaces"})
        step["run_settings"]["after_enabled"] = True
        save_recipe(self.path, entry)
        self.page.load_saved_pipeline_to_canvas("Saved")
        calls = []

        def worker(command, *args, **kwargs):
            calls.append(command)
            return CommandResult(returncode=0)

        def drive(win):
            self.run_step(win)
            self.assertTrue(self.button(win, "Save Pipeline").winfo_ismapped())
            self.button(win, "Close").invoke()

        with patch.object(self.page.engine, "_run_command", side_effect=worker), \
                patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        self.assertEqual([["grep", "-i", "--color", "never", "-n", "flag{",
                           "--test-file", "/tmp/file with spaces", "--label", "a b"]], calls)
        self.assertEqual(step["run_settings"], self.page._completed_recipe[0]["run_settings"])

    def test_legacy_load_and_mode_switch_clear_stale_save_offer(self):
        legacy = {"pipeline_name": "Old", "steps": [
            {"name": "grep", "params": "-i", "options": [{"flag": "-F", "type": "checkbox"}]}]}
        save_recipe(self.path, legacy)
        self.assertTrue(self.page.load_saved_pipeline_to_canvas("Old"))
        self.assertNotIn("run_settings", self.page.nodes[0])
        self.page.set_completed_recipe(legacy["steps"])
        self.page.set_pipeline_mode("Step")
        self.assertIsNone(self.page._completed_recipe)
        self.page.set_pipeline_mode("Auto")
        self.assertEqual("grep", self.page.nodes[0]["name"])
        self.assertEqual("-i", self.page.nodes[0]["params"])
        self.page.clear_pipeline()
        self.assertEqual([], self.page.nodes)
        self.assertIsNone(self.page._completed_recipe)

    def test_saved_file_sources_restore_without_reusing_old_input_path(self):
        from Pipeline.output_files import CommandResult
        previous = self.root_path / "previous.txt"
        previous.write_text("previous")
        for source in ("previous", "original", "manual"):
            with self.subTest(source=source):
                self.page.clear_pipeline()
                self.page.add_tool_node("file")
                self.page.set_original_file(str(self.input_path))
                node = self.page.nodes[0]
                node["run_settings"] = {"input_source": source}
                calls = []

                def worker(command, input_data, input_path, **kwargs):
                    calls.append(input_path)
                    return CommandResult(stdout=b"ok", returncode=0)

                def drive(win):
                    inp = self.widgets(win, self.ctk.CTkEntry)[0]
                    if source == "manual":
                        self.assertEqual("", inp.get())
                        self.run_step(win)
                        self.assertEqual([], calls)  # No fallback to previous output.
                        self.set_entry(inp, str(self.input_path))
                    else:
                        self.assertEqual(str(previous if source == "previous" else self.input_path), inp.get())
                    self.run_step(win)
                    self.button(win, "Close").invoke()

                with patch.object(self.page.engine, "_run_command", side_effect=worker), \
                        patch.object(self.page, "wait_window", side_effect=drive), \
                        patch("pages.pipeline.history_hooks.begin", return_value="current") as history:
                    self.page.open_step_window(
                        node, previous, previous,
                        [{"history_id": "prior", "tool": "file", "output": previous}], True,
                        step_index=2, total_steps=2)
                self.assertEqual("prior" if source == "previous" else None,
                                 history.call_args.kwargs.get("parent_id"))
                self.assertEqual([str(previous if source == "previous" else self.input_path)], calls)
                self.assertEqual(source, node["_successful_step"]["run_settings"]["input_source"])
                self.assertNotIn(str(previous), json.dumps(node["_successful_step"]))
                self.assertNotIn(str(self.input_path), json.dumps(node["_successful_step"]))

    def test_changes_while_worker_runs_are_not_saved_as_executed_options(self):
        from Pipeline.output_files import CommandResult
        self.page.add_tool_node("grep")
        release = threading.Event()

        def worker(*args, **kwargs):
            release.wait(3)
            return CommandResult(stdout=b"ok", returncode=0)

        def drive(win):
            pattern = self.entry(win, ":")
            self.set_entry(pattern, "executed")
            self.button(win, "Run").invoke()
            self.set_entry(pattern, "edited while running")
            release.set()
            self.wait_for(lambda: self.button(win, "Run").cget("state") == "normal")
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            self.assertNotIn("_successful_step", self.page.nodes[0])
            self.assertEqual("executed", self.page.nodes[0]["run_settings"]["option_values"][-1]["value"])
            self.button(win, "Close").invoke()

        with patch.object(self.page.engine, "_run_command", side_effect=worker), \
                patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        self.assertIsNone(self.page._completed_recipe)

    def test_dirty_earlier_step_blocks_save_but_preserves_existing_next_flow(self):
        from Pipeline.output_files import CommandResult
        self.page.add_tool_node("grep")
        self.page.add_tool_node("grep")
        index = [0]

        def drive(win):
            current = index[0]
            index[0] += 1
            self.set_entry(self.entry(win, ":"), "executed")
            self.run_step(win)
            if current == 0:
                self.set_entry(self.entry(win, ":"), "not executed")
            self.root.update()
            self.assertFalse(self.button(win, "Save Pipeline").winfo_ismapped())
            self.button(win, "Next" if current == 0 else "Close").invoke()

        with patch.object(self.page.engine, "_run_command", return_value=CommandResult(stdout=b"ok", returncode=0)), \
                patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        self.assertEqual(2, len(self.page.run_logs))
        self.assertIsNone(self.page._completed_recipe)

    def test_step_close_analysis_does_not_offer_save_as_finished(self):
        from Pipeline.output_files import CommandResult
        self.page.set_pipeline_mode("Step")
        self.page.add_tool_node("grep")

        def drive(win):
            self.run_step(win)
            self.button(win, "Close Analysis").invoke()

        with patch.object(self.page.engine, "_run_command", return_value=CommandResult(stdout=b"ok", returncode=0)), \
                patch.object(self.page, "wait_window", side_effect=drive):
            self.page.run_pipeline()
        self.assertIsNone(self.page._completed_recipe)
        self.assertEqual([], self.page.run_logs)
        self.assertFalse(self.page._pipeline_running)


if __name__ == "__main__":
    unittest.main()
