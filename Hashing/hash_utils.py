import hashlib

def hash_data(text, algo="sha256", length=32):
    raw = text.encode()

    algos = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha224": hashlib.sha224,
        "sha256": hashlib.sha256,
        "sha384": hashlib.sha384,
        "sha512": hashlib.sha512,
        "sha3_224": hashlib.sha3_224,
        "sha3_256": hashlib.sha3_256,
        "sha3_384": hashlib.sha3_384,
        "sha3_512": hashlib.sha3_512,
        "blake2b": hashlib.blake2b,
        "blake2s": hashlib.blake2s,
        "shake_128": hashlib.shake_128,
        "shake_256": hashlib.shake_256,
    }

    if algo not in algos:
        return "Unsupported algorithm"

    # สร้างออบเจกต์ของ Hash
    h = algos[algo](raw)

    # เช็คว่าเป็นตระกูล SHAKE หรือเปล่า ถ้าใช่ต้องบังคับใส่ length
    if algo.startswith("shake_"):
        return h.hexdigest(length)
    else:
        return h.hexdigest()