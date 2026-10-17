"""Teaching aid, separate from UNIT runtime. SHA-256 trace and actual UNIT calls.

Run: python3 docs/presentation/algorithm_lab.py
No network, GUI, user-state writes, or third-party dependencies.
SHA-256 equations: NIST FIPS 180-4 sections 4–6; RFC 6234.
"""
from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from Hashing.hash_utils import hash_data
from Encode.base_encoder import encode_data
from Decode.base_decoder import decode_to_bytes, auto_detect_decode
from Tools.extra_tools import bitwise_mask, _parse_input_bytes, _parse_key_bytes
from Tools.rot import rot_n

MASK = 0xFFFFFFFF
INITIAL = (
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
)
K = tuple(int(x, 16) for x in """
428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5
d807aa98 12835b01 243185be 550c7dc3 72be5d74 80deb1fe 9bdc06a7 c19bf174
e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da
983e5152 a831c66d b00327c8 bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967
27b70a85 2e1b2138 4d2c6dfc 53380d13 650a7354 766a0abb 81c2c92e 92722c85
a2bfe8a1 a81a664b c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070
19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3
748f82ee 78a5636f 84c87814 8cc70208 90befffa a4506ceb bef9a3f7 c67178f2
""".split())


def rotr(value, count):
    return ((value >> count) | (value << (32 - count))) & MASK


def sha256_teaching(raw, trace=False):
    """Readable whole-message implementation for study, not production use."""
    bit_length = len(raw) * 8
    padded = raw + b'\x80'
    padded += b'\0' * ((56 - len(padded) % 64) % 64)
    padded += bit_length.to_bytes(8, 'big')
    state = list(INITIAL)
    if trace:
        print('Input bytes:', raw.hex(' '))
        print('Original length:', bit_length, 'bits')
        print('Padded bytes:', padded.hex(' '))
        print('Blocks:', len(padded) // 64)
    for block_index, start in enumerate(range(0, len(padded), 64)):
        block = padded[start:start + 64]
        words = [int.from_bytes(block[i:i + 4], 'big') for i in range(0, 64, 4)]
        for i in range(16, 64):
            x, y = words[i - 15], words[i - 2]
            s0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3)
            s1 = rotr(y, 17) ^ rotr(y, 19) ^ (y >> 10)
            words.append((words[i - 16] + s0 + words[i - 7] + s1) & MASK)
        a, b, c, d, e, f, g, h = state
        if trace:
            print('Block', block_index, 'W[0..17]:', ' '.join(f'{w:08x}' for w in words[:18]))
        for i in range(64):
            big1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
            choose = (e & f) ^ ((~e & MASK) & g)
            t1 = (h + big1 + choose + K[i] + words[i]) & MASK
            big0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
            majority = (a & b) ^ (a & c) ^ (b & c)
            t2 = (big0 + majority) & MASK
            a, b, c, d, e, f, g, h = (
                (t1 + t2) & MASK, a, b, c, (d + t1) & MASK, e, f, g,
            )
            if trace and i in (0, 1, 63):
                print(f'Round {i:02}: T1={t1:08x} T2={t2:08x};',
                      'a..h=', ' '.join(f'{x:08x}' for x in (a,b,c,d,e,f,g,h)))
        state = [(old + new) & MASK for old, new in zip(state, (a,b,c,d,e,f,g,h))]
        if trace:
            print('Feed-forward H:', ' '.join(f'{x:08x}' for x in state))
    return ''.join(f'{x:08x}' for x in state)


def main():
    samples = [b'', b'abc', b'a' * 55, b'a' * 56, b'a' * 63, b'a' * 64,
               b'a' * 65, bytes(range(256)), 'ไทย'.encode(), b' leading \n']
    for raw in samples:
        assert sha256_teaching(raw) == hashlib.sha256(raw).hexdigest()
    print('SHA-256 educational implementation: 10 vectors match hashlib')
    print('\n--- Trace abc ---')
    digest = sha256_teaching(b'abc', trace=True)
    assert digest == hash_data('abc', 'sha256')
    print('UNIT hash_data:', digest)
    print('digest bytes:', len(bytes.fromhex(digest)), '; hex characters:', len(digest))
    print('\n--- Exact input matters ---')
    for value in ('abc', 'abc\n', ' abc', 'ไทย'):
        print(repr(value), value.encode().hex(), hash_data(value))
    print('\n--- Actual UNIT codecs ---')
    for algo in ('Base64', 'Base32', 'Base45', 'Base85', 'Base16', 'Base58',
                 'Base62', 'Hex', 'Binary', 'Octal', 'Decimal', 'URL-safe Base64'):
        encoded = encode_data('AB', algo)
        assert decode_to_bytes(encoded, algo) == b'AB'
        print(algo, repr(encoded))
    assert decode_to_bytes('FG EC EF', 'Hex', alphabet='AJIHGFEDCBjihgfe') == b'The'
    print('Custom Hex FG EC EF -> The')
    print('ROT13:', rot_n('flag', 13), '->', rot_n(rot_n('flag', 13), 13))
    print('Auto Detect:', auto_detect_decode(encode_data('flag{demo}').encode()))
    print('\n--- Actual UNIT parser and XOR ---')
    for value in ('41', 'A', 'dead', '0x41,0x42'):
        print('input', repr(value), _parse_input_bytes(value))
    for value in ('74', '0x4A', '4142', '0x4142'):
        print('key', repr(value), _parse_key_bytes(value))
    print(bitwise_mask('2c 26 2b 2d', '0x4A', 'xor'))
    assert bytes(x ^ 0x4A for x in b'flag') == bytes.fromhex('2c262b2d')
    assert 'flag' in bitwise_mask('2c262b2d', '0x4A', 'xor')
    print('All educational checks passed. No app state was written.')


if __name__ == '__main__':
    main()
