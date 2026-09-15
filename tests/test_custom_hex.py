import unittest

from Decode.base_decoder import custom_hex_to_hex, decode_data, decode_to_bytes


class CustomHexTests(unittest.TestCase):
    def test_known_message(self):
        self.assertEqual(custom_hex_to_hex('FG EC EF'), '546865')
        self.assertEqual(decode_data('FG\nEC\tEF', 'Custom Hex'), 'The')

    def test_every_byte_preserved(self):
        alphabet = 'AJIHGFEDCBjihgfe'
        raw = bytes(range(256))
        encoded = ''.join(alphabet[int(c, 16)] for c in raw.hex())
        self.assertEqual(decode_to_bytes(encoded, 'Custom Hex'), raw)

    def test_custom_alphabet(self):
        self.assertEqual(decode_data('4869', 'Custom Hex', alphabet='0123456789abcdef'), 'Hi')
        self.assertEqual(custom_hex_to_hex('Ee'), '6F')

    def test_validation(self):
        for text, alphabet in [('AA', 'A'*16), ('AA', 'abc'), ('AA', '0123456789abcde '), ('AZ', 'AJIHGFEDCBjihgfe'), ('A', 'AJIHGFEDCBjihgfe')]:
            with self.subTest(text=text, alphabet=alphabet):
                with self.assertRaises(ValueError):
                    custom_hex_to_hex(text, alphabet)

    def test_unified_hex(self):
        self.assertEqual(decode_data('54 68 65', 'Hex'), 'The')
        self.assertEqual(decode_data('c3a9', 'Hex'), 'é')
        self.assertEqual(decode_data('FG EC EF', 'Hex', alphabet='AJIHGFEDCBjihgfe'), 'The')
        self.assertEqual(decode_to_bytes('ee', 'Hex', alphabet='AJIHGFEDCBjihgfe'), b'\xff')
        self.assertEqual(decode_to_bytes('ff', 'Hex', alphabet='0123456789ABCDEF'), b'\xff')

    def test_empty_and_standard_hex(self):
        self.assertEqual(decode_to_bytes('', 'Custom Hex'), b'')
        self.assertEqual(decode_data('546865', 'Hex'), 'The')
        self.assertEqual(decode_to_bytes('FF', 'Hex'), b'\xff')


if __name__ == '__main__':
    unittest.main()
