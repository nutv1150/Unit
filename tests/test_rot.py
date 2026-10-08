import unittest

from Tools.rot import rot_n
from Encode.base_encoder import encode_data
from Decode.base_decoder import decode_data, decode_to_bytes, auto_detect_decode


class RotTests(unittest.TestCase):
    def test_known_shifts_and_legacy(self):
        for transform in (encode_data, decode_data):
            self.assertEqual(transform("Abc XYZ! ไทย", "ROT:7"), "Hij EFG! ไทย")
            self.assertEqual(transform("Hello", "ROT13"), "Uryyb")
            self.assertEqual(transform("Hello", "ROT"), "Uryyb")
            self.assertEqual(transform("Hello!", "ROT:47:ascii"), "w6==@P")
        self.assertEqual(decode_to_bytes("Uryyb ไทย", "ROT13"), "Hello ไทย".encode())

    def test_all_shifts_round_trip(self):
        text = ''.join(chr(n) for n in range(33, 127)) + " \t\nไทย"
        for mode, size in (("alpha", 26), ("ascii", 94)):
            for n in range(1, size):
                encoded = encode_data(text, f"ROT:{n}:{mode}")
                self.assertEqual(decode_data(encoded, f"ROT:{size-n}:{mode}"), text)
                self.assertEqual(decode_to_bytes(encoded, f"ROT:{size-n}:{mode}"), text.encode())

    def test_invalid_parameters(self):
        for algo in ("ROT:x", "ROT:0", "ROT:26", "ROT:94:ascii", "ROT:7:other", "ROT:7:alpha:extra"):
            for transform in (encode_data, decode_data, decode_to_bytes):
                with self.subTest(algo=algo, transform=transform.__name__):
                    with self.assertRaises(ValueError):
                        transform("Hello", algo)

    def test_auto_detect_rot_flags(self):
        for mode, n, size in (("alpha", 7, 26), ("ascii", 47, 94), ("ascii", 93, 94)):
            plain = "flag{hello_world}"
            self.assertEqual(auto_detect_decode(rot_n(plain, n, mode).encode()),
                             (f"ROT:{size-n}:{mode}", plain))

    def test_auto_detect_base64_regression(self):
        self.assertEqual(auto_detect_decode(b"SGVsbG8="), ("Base64", "Hello"))


if __name__ == "__main__":
    unittest.main()
