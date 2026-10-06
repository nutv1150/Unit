"""Offline integration guards; these tests never contact Gemini or user services."""
import subprocess
import threading
import unittest
from unittest.mock import Mock, patch

from pages.gemini import GeminiPage


class GeminiSafetyTests(unittest.TestCase):
    def page(self):
        page = GeminiPage.__new__(GeminiPage)
        page._busy = False
        page._connecting = False
        page._stop_requested = False
        page._confirm_dialog = None
        page.current_process = None
        page.cli_ready = True
        page.gemini_cmd = "mock-gemini"
        page.model_name = "test-model"
        page.cli_workdir = None
        page._build_env = Mock(return_value={})
        page.after = lambda delay, callback, *args: callback(*args)
        page.update_chat_ui = Mock()
        page.finish_response = Mock()
        page.history = []
        page.build_prompt_with_history = lambda text: text
        return page

    def test_nonzero_cli_with_stdout_is_failure(self):
        page = self.page()
        process = Mock(returncode=9)
        process.communicate.return_value = ("partial output", "failure")
        with patch("pages.gemini.subprocess.Popen", return_value=process):
            with self.assertRaisesRegex(RuntimeError, "failure"):
                page.call_gemini_cli("hello")
        self.assertIsNone(page.current_process)

    def test_connection_nonzero_is_not_ready(self):
        page = self.page()
        page._init_api_success = Mock()
        page._init_api_fail = Mock()
        results = [subprocess.CompletedProcess([], 0, "1.0", ""),
                   subprocess.CompletedProcess([], 1, "partial", "connection failure")]
        with patch("pages.gemini.subprocess.run", side_effect=results):
            page._init_api_worker()
        page._init_api_success.assert_not_called()
        page._init_api_fail.assert_called_once()

    def test_repeated_enter_does_not_start_second_request(self):
        page = self.page()
        page.input_field = Mock()
        page.input_field.get.return_value = "hello"
        page.send_btn = Mock()
        page.stop_btn = Mock()
        with patch("pages.gemini.threading.Thread") as worker:
            page.send_message()
            page.send_message()
        self.assertEqual(worker.call_count, 1)

    def test_denied_actions_neither_execute_nor_save(self):
        page = self.page()
        page.call_gemini_cli = Mock(return_value="[EXEC]echo test[/EXEC][SAVE:denied.txt]data[/SAVE]")
        page.ask_action_confirm = Mock(return_value=False)
        with patch("pages.gemini.subprocess.Popen") as launch, patch("builtins.open") as write:
            page.process_request("analyze")
        launch.assert_not_called()
        write.assert_not_called()
        self.assertEqual(page.ask_action_confirm.call_count, 2)

    def test_silent_approved_command_reports_exit_code(self):
        page = self.page()
        page.call_gemini_cli = Mock(side_effect=["[EXEC]true[/EXEC]", "done"])
        page.ask_action_confirm = Mock(return_value=True)
        process = Mock(returncode=0)
        process.communicate.return_value = ("", "")
        with patch("pages.gemini.subprocess.Popen", return_value=process):
            page.process_request("analyze")
        feedback = page.call_gemini_cli.call_args_list[1].args[0]
        self.assertIn("Exit code: 0", feedback)
        self.assertIn("(empty)", feedback)

    def test_stop_releases_pending_confirmation(self):
        page = self.page()
        page._confirm_event = threading.Event()
        page._confirm_dialog = Mock()
        dialog = page._confirm_dialog
        page.request_stop()
        self.assertTrue(page._confirm_event.is_set())
        self.assertFalse(page._confirm_result)
        dialog.destroy.assert_called_once()
