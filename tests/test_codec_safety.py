import base64
import unittest

from Encode.base_encoder import BASE58, BASE62, encode_base_n
from Decode.base_decoder import decode_data, decode_to_bytes


class CodecSafetyTests(unittest.TestCase):
    def test_auto_detect_does_not_drop_invalid_input_bytes(self):
        from Decode.base_decoder import auto_detect_decode
        with self.assertRaises(UnicodeDecodeError):
            auto_detect_decode(b'\xffSGVsbG8=')

    def test_binary_bytes_are_not_discarded(self):
        raw = bytes([0, 1, 127, 128, 254, 255])
        encoded = base64.b64encode(raw).decode()
        self.assertEqual(decode_to_bytes(encoded, "Base64"), raw)
        # The text compatibility wrapper uses reversible hex for binary.
        self.assertEqual(decode_data(encoded, "Base64"), raw.hex())

    def test_urlsafe_base64(self):
        raw = b"hello"
        encoded = base64.urlsafe_b64encode(raw).decode()
        self.assertEqual(decode_to_bytes(encoded, "URL-safe Base64"), raw)
        with self.assertRaises(ValueError):
            decode_to_bytes(encoded.rstrip("="), "URL-safe Base64")

    def test_base_n_preserves_leading_zero_bytes(self):
        for alphabet in (BASE58, BASE62):
            raw = b"\0\0abc"
            encoded = encode_base_n(raw, alphabet)
            self.assertEqual(decode_to_bytes(encoded, "Base58" if alphabet == BASE58 else "Base62"), raw)

    def test_empty_base_n_round_trip(self):
        self.assertEqual(encode_base_n(b"", BASE58), "")
        self.assertEqual(decode_to_bytes("", "Base58"), b"")


if __name__ == "__main__":
    unittest.main()
