import unittest
from unittest.mock import Mock

from Tools.window_layout import fit_window


class WindowLayoutTests(unittest.TestCase):
    def window(self, width, height, scale=1.0):
        window = Mock()
        window.winfo_screenwidth.return_value = width
        window.winfo_screenheight.return_value = height
        window._get_window_scaling.return_value = scale
        return window

    def test_large_screen_uses_larger_preferred_sizes(self):
        for size in ('1360x820', '1200x780', '1200x800', '460x210'):
            window = self.window(1920, 1080)
            fit_window(window, size)
            window.geometry.assert_called_once_with(size)

    def test_small_screen_reserves_room_for_desktop_and_titlebar(self):
        window = self.window(1366, 768)
        self.assertEqual(fit_window(window, '1360x820'), (1286, 668))
        window.geometry.assert_called_once_with('1286x668')

    def test_high_dpi_converts_physical_limit_to_logical_dimensions(self):
        window = self.window(1920, 1080, scale=1.5)
        width, height = fit_window(window, '1360x820')
        self.assertLessEqual(width * 1.5, 1840)
        self.assertLessEqual(height * 1.5, 980)

    def test_does_not_enlarge_small_dialog_to_fill_screen(self):
        window = self.window(1366, 768)
        self.assertEqual(fit_window(window, '460x210'), (460, 210))
