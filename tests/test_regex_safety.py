import unittest

from Tools.regex_runner import find_match_spans


class RegexSafetyTests(unittest.TestCase):
    def test_matches_are_case_insensitive_and_keep_unicode_offsets(self):
        self.assertEqual(find_match_spans(r'flag\{[^}]+\}', 'ไทย FLAG{ok} flag{two}'),
                         [[4, 12], [13, 22]])

    def test_catastrophic_pattern_times_out_in_child(self):
        with self.assertRaisesRegex(ValueError, 'exceeded'):
            find_match_spans('(a+)+$', 'a' * 32 + '!', timeout=.5)

    def test_result_count_and_invalid_pattern_are_bounded(self):
        with self.assertRaisesRegex(ValueError, 'match limit'):
            find_match_spans('.', 'abcdef', max_matches=3)
        with self.assertRaises(ValueError):
            find_match_spans('[', 'data')
