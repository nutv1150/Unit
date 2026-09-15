### Slide Flow

**Phantom Packets**

---

#### ขั้น 1 — เจออะไรในไฟล์

Phantom Packets ซ่อน flag สองส่วนใน Git ที่ส่งผ่าน TLS โดย key ถูกแทรกใน DNS AAAA response

เริ่มจากไฟล์ประกอบ `dns-chunks.json`, `client.tls`, `server.tls` ที่แยกมาจาก `traffic.pcapng` ใช้ **unzip ภายนอก** เตรียมข้อมูล:
```bash
mkdir -p /tmp/unit-phantom
cd /tmp/unit-phantom
unzip -q "/home/nutvv/Downloads/write up.zip" "phantom/*" -d .
```

`-q` ลดข้อความระหว่างแตกไฟล์, `"phantom/*"` เลือกเฉพาะเคสนี้ และ `-d .` วางไฟล์ในโฟลเดอร์ทำงาน

![[challenge.png]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| DNS label 0001 ถึง 0107 | แต่ละ response เป็นชิ้นข้อมูลตามลำดับ | Python เรียง sequence แล้วต่อ RDATA |
| AAAA RDATA เป็น ASCII | อาจบรรทุกข้อความแทน IPv6 จริง | อ่าน rdata_hex ครั้งละ 16 bytes |
| ได้ BEGIN PRIVATE KEY | เป็นคีย์สำหรับถอด TLS session | Python cryptography โหลด PEM |
| HTTP หลัง TLS เป็น Git smart protocol | ต้องแยก pack และอ่าน object history | Python ตัด chunk/sideband แล้วใช้ Git |
| มี pt1 กับ pt2 | ต่อเนื้อหาตามหมายเลข | ต่อข้อความ ไม่ hash ซ้ำ |

---

#### ขั้น 3 — ประกอบ TLS key จาก DNS

ใช้ **Python ภายนอก** เรียงชิ้น DNS แล้วต่อเป็น PEM:
```bash
python3 - <<'PYCODE'
import json
from pathlib import Path
rows = json.loads(Path("phantom/tls/dns-chunks.json").read_text())
raw = b"".join(bytes.fromhex(r["rdata_hex"]) for r in sorted(rows, key=lambda r:r["sequence"]))
pem = raw.rstrip(b"\x00")
Path("phantom/tls/dns-key.pem").write_bytes(pem)
print("Chunks:", len(rows), "Raw bytes:", len(raw), "PEM bytes:", len(pem))
print(pem.splitlines()[0].decode())
PYCODE
```

`sequence` เป็นลำดับ 1–107 และ `rstrip(b"\x00")` ตัด NUL padding ท้าย key ได้ 1,712 bytes ก่อนตัด และ PEM 1,704 bytes
![[phantom — DNS chunks ต่อเป็น PEM private key]]

---

#### ขั้น 4 — ถอด TLS ด้วย Python cryptography

cipher suite คือ `TLS_RSA_WITH_AES_256_GCM_SHA384` ใช้ RSA key ถอด premaster secret แล้วคำนวณ key block ตาม extended master secret

**Step 1 — เตรียม environment และสคริปต์**
```bash
python3 -m venv .tls-venv
.tls-venv/bin/python -m pip install cryptography
```

```bash
cat > decrypt_tls.py <<'PYCODE'
from pathlib import Path
import argparse,struct,hashlib,hmac,json,re
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();root=a.directory
def records(b):
 out=[];i=0
 while i<len(b):
  t,v,n=struct.unpack_from('!BHH',b,i);assert i+5+n<=len(b);out.append((t,v,b[i+5:i+5+n]));i+=5+n
 return out
c=records((root/'client.tls').read_bytes());s=records((root/'server.tls').read_bytes())
ch,sh=c[0][2],s[0][2];assert sh[4:6]==b'\x03\x03';sid=sh[38];assert sh[39+sid:41+sid]==b'\x00\x9d';assert b'\x00\x17\x00\x00' in sh
transcript=ch+s[0][2]+s[1][2]+s[2][2]+c[1][2]
key=load_pem_private_key((root/'dns-key.pem').read_bytes(),password=None)
premaster=key.decrypt(c[1][2][6:],PKCS1v15());assert len(premaster)==48 and premaster[:2]==b'\x03\x03'
def prf(secret,label,seed,n):
 seed=label+seed;A=seed;out=b''
 while len(out)<n:
  A=hmac.new(secret,A,'sha384').digest();out+=hmac.new(secret,A+seed,'sha384').digest()
 return out[:n]
master=prf(premaster,b'extended master secret',hashlib.sha384(transcript).digest(),48)
kb=prf(master,b'key expansion',sh[6:38]+ch[6:38],72)
count=0;finished={}
for name,recs,k,iv in [('client',c,kb[:32],kb[64:68]),('server',s,kb[32:64],kb[68:72])]:
 active=False;seq=0;plaintext=[]
 for t,v,data in recs:
  if t==20:active=True;continue
  if not active:continue
  aad=seq.to_bytes(8,'big')+struct.pack('!BHH',t,v,len(data)-24)
  plain=AESGCM(k).decrypt(iv+data[:8],data[8:],aad);count+=1;seq+=1
  if t==22:
   assert plain[:4]==b'\x14\x00\x00\x0c';finished[name]=plain
  if t==23:plaintext.append(plain)
 (root/(name+'-plaintext.bin')).write_bytes(b''.join(plaintext))
 print(name,'application bytes',sum(map(len,plaintext)))
PYCODE
```

`PKCS1v15()` ใช้ถอด RSA premaster; `AESGCM` ถอด record; `seq` กับ header ประกอบเป็น AAD ของแต่ละ record; type 23 คือ application data ที่ต้องเก็บไปอ่าน HTTP

**Step 2 — รันสคริปต์**
```bash
.tls-venv/bin/python decrypt_tls.py phantom/tls
```

argument `phantom/tls` คือโฟลเดอร์ที่มี PEM และ TLS streams ได้ `client-plaintext.bin` กับ `server-plaintext.bin`
![[phantom — HTTP plaintext หลังถอด TLS]]

---

#### ขั้น 5 — แยก Git pack จาก HTTP

ใช้ **Python ภายนอก** อ่าน HTTP chunked response แล้วเก็บเฉพาะ Git sideband channel 1:
```bash
python3 - <<'PYCODE'
from pathlib import Path
b = Path("phantom/tls/server-plaintext.bin").read_bytes()
i = b.rfind(b"HTTP/1.1 200 OK")
i = b.index(b"\r\n\r\n", i) + 4
body = b""
while True:
    j = b.index(b"\r\n", i)
    n = int(b[i:j], 16)
    i = j + 2
    if n == 0:
        break
    body += b[i:i+n]
    i += n + 2
pack, i = b"", 0
while i < len(body):
    n = int(body[i:i+4], 16)
    if n < 4:
        i += 4
        continue
    data = body[i+4:i+n]
    i += n
    if data[:1] == b"\x01":
        pack += data[1:]
Path("recovered.pack").write_bytes(pack)
print("Git pack:", len(pack), "bytes")
PYCODE
```

`int(..., 16)` อ่านขนาด HTTP chunk และ Git pkt-line; byte `0x01` คือ channel ที่บรรทุก pack ส่วน channel อื่นเป็นข้อความประกอบ

ใช้ **Git ภายนอก** อ่าน pack โดยไม่ checkout repository:
```bash
git init --bare recovered.git
git --git-dir=recovered.git index-pack --stdin < recovered.pack
```

`--bare` สร้างเฉพาะฐาน object; `--git-dir` ระบุตำแหน่งฐาน Git; `index-pack --stdin` รับ pack ที่ส่งเข้าทาง `< recovered.pack`
![[phantom — แยก Git pack และ index-pack]]

---

#### ขั้น 6 — อ่านไฟล์สองส่วนจากประวัติ Git

ใช้ **Python เรียก Git** สำรวจ blob ทุกตัวใน pack เพื่อค้นหา flag fragments ก่อน:

```bash
python3 - <<'PYCODE'
import subprocess, re
base = ["git", "--git-dir=recovered.git"]
objects = subprocess.check_output(base + ["cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)"], text=True)
for line in objects.splitlines():
    oid, kind = line.split()
    if kind != "blob":
        continue
    data = subprocess.check_output(base + ["cat-file", "blob", oid])
    for part in re.findall(rb"TCTT2026_pt[12]\{[^}]+\}", data):
        print(oid, part.decode())
PYCODE
```

`--batch-all-objects` อ่าน object ทั้งหมด รวมไฟล์ที่หลุดจาก tree ล่าสุด; `--batch-check` แสดง ID และชนิด; `cat-file blob` อ่านเนื้อหาแต่ละไฟล์ พบส่วน 1 ใน blob `71f755098bc93c6a5c15e22dd8855d4c4d35b063` และส่วน 2 ใน `b8e1e3826a8b62807c87d627e072197f57789659`

ใช้ **git show** อ่านไฟล์จาก commit ที่เก็บข้อมูล:
```bash
git --git-dir=recovered.git show 3421643f9f550c5d80583769fa0aaa2499b7ffe3:deploy/staging-vars.conf
git --git-dir=recovered.git show edf1f1923a14ea7b18fea2ef313511c8d20b61b2:config/credentials.bak
```

รูปแบบ `commit:path` อ่านไฟล์ ณ commit นั้นโดยตรง จึงอ่าน credentials.bak ที่ถูกลบใน commit ถัดมาได้

พบสองค่า:
```text
DEPLOY_TOKEN=TCTT2026_pt1{5b9437e03df7b252}
api_secret=TCTT2026_pt2{9562ad4705a54963}
```

ต่อค่าด้านใน pt1 แล้ว pt2 ได้ `5b9437e03df7b2529562ad4705a54963` แล้วห่อด้วย TCTT2026{...}

ขั้นถอด DNS/TLS/Git ใช้ Python และ Git ภายนอกทั้งหมด การต่อสองส่วนเป็นขั้นสุดท้ายของข้อนี้
![[phantom — git show พบ flag part1 และ part2]]

---

#### ขั้น 7 — ปิดเคส

**🚩 Flag = `TCTT2026{5b9437e03df7b2529562ad4705a54963}`**
