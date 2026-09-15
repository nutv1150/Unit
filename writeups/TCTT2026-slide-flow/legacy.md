### Slide Flow

**Legacy Signer**

---

#### ขั้น 1 — เจออะไรในไฟล์

ใช้ **unzip ภายนอก** แตก package ของ Legacy Signer แล้วเปิด TASK.md และ CHANGELOG.md ใน Text Editor:
```bash
mkdir -p /tmp/unit-legacy
cd /tmp/unit-legacy
unzip -p "/home/nutvv/Downloads/tctt2026.zip" "tctt2026/Legacy Signer/player_package.zip" > player_package.zip
unzip -q player_package.zip -d .
```

`-p` ส่งเนื้อหาไฟล์ภายใน ZIP ออกมาโดยตรง, `>` เก็บเป็น player_package.zip และ `-d .` แตกลงโฟลเดอร์ทำงาน

TASK กำหนดให้หา private key `d` ของ secp256k1 แล้วใช้ `hex(d)` คำนวณ flag
![[Screenshot 2026-08-15 153722.png]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| ก่อน 2019-02-06: nonce บิตบน 12 บิตเป็นศูนย์ | nonce มีขอบเขตเล็กกว่าปกติ | Python LLL ใช้ scale จาก 12 บิต |
| ก่อน 2020-01-16: nonce บิตบน 8 บิตเป็นศูนย์ | มีอีกกลุ่มที่ใช้ขอบเขต 8 บิต | เลือก signature ตาม timestamp |
| ทุก signature ใช้ private key เดียวกัน | รวมสมการหลายรายการเพื่อหา d เดียว | สร้าง lattice จาก signature 40 ตัวแรก |
| TASK ใช้ `sha256(hex(d).encode())[:32]` | ต้อง hash ข้อความรวม 0x | UNIT → Hash → sha256 แล้วเอา 32 ตัวแรก |

![[Screenshot 2026-08-15 153737.png]]

---

#### ขั้น 3 — ทำไมใช้ lattice หา private key

ECDSA มีสมการ `s·k ≡ h + r·d (mod N)` แม้ไม่รู้ k เต็มค่า แต่รู้ขอบเขตจากบิตบนที่เป็นศูนย์ จึงเอาหลายสมการมาสร้าง lattice แล้วใช้ LLL หา candidate d

ชุดนี้มี signature 463 รายการ โดย 227 รายการอยู่ในช่วง nonce อ่อน เลือก 40 รายการแรกมาสร้างเมทริกซ์ 42×42 การคำนวณนี้ใช้ Python + python-flint ภายนอก UNIT

---

#### ขั้น 4 — รัน LLL solver

**Step 1 — เตรียม Python environment**
```bash
python3 -m venv .solver-venv
.solver-venv/bin/python -m pip install python-flint==0.9.0
```

`-m venv` สร้าง environment สำหรับ solver และ `==0.9.0` ระบุรุ่นไลบรารีที่ใช้ลด lattice

**Step 2 — บันทึก solver เป็นไฟล์**
```bash
cat > solve_legacy.py <<'PYCODE'
from pathlib import Path
import argparse, hashlib, json, sys
from flint import fmpz_mat

p=argparse.ArgumentParser()
p.add_argument('--package',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
args=p.parse_args()
sys.path.insert(0,str(args.package.resolve()))
from ec_core import N,G,scalar_mult,ecdsa_sign,ecdsa_verify
logs=json.loads((args.package/'signatures.json').read_text())
pub=json.loads((args.package/'pubkey.json').read_text())
Q=(int(pub['Qx'],16),int(pub['Qy'],16))
eligible=[(x,12 if x['timestamp']<'2019-02-06' else 8) for x in logs if x['timestamp']<'2020-01-16']
chosen=eligible[:40]
m=len(chosen)
A=[[0]*(m+2) for _ in range(m+2)]
for i,(x,bits) in enumerate(chosen):
    r,s=int(x['r'],16),int(x['s'],16)
    h=int.from_bytes(hashlib.sha256(x['message'].encode()).digest(),'big')
    scale=2*(1<<bits)
    A[i][i]=scale*N
    A[m][i]=scale*(r*pow(s,-1,N)%N)
    A[m+1][i]=scale*(h*pow(s,-1,N)%N)-N
A[m][m]=1
A[m+1][m+1]=N
reduced=fmpz_mat(A).lll()
d=None
for i in range(m+2):
    for sign in (-1,1):
        candidate=(sign*int(reduced[i,m]))%N
        if candidate and scalar_mult(candidate,G)==Q:
            d=candidate
            break
    if d is not None:break
if d is None:raise RuntimeError('No verified key recovered from this dataset')

for x,bits in eligible:
    r,s=int(x['r'],16),int(x['s'],16)
    h=int.from_bytes(hashlib.sha256(x['message'].encode()).digest(),'big')
    nonce=((h+r*d)*pow(s,-1,N))%N
    assert 0<nonce<(1<<(256-bits))

message=b'give-me-the-flag'
# Fixed only for a reproducible proof on this public CTF key, not for production.
proof_nonce=1+int.from_bytes(hashlib.sha256(b'CTF proof nonce 2026-09-12').digest(),'big')%(N-1)
r,s=ecdsa_sign(message,d,proof_nonce)
assert ecdsa_verify(message,r,s,Q)
result={'d':hex(d),
        'public_key_match':True,'weak_nonce_checks':len(eligible),'selected_signatures':m,
        'proof_message':message.decode(),'proof_signature':{'r':hex(r),'s':hex(s)},'proof_verified':True}
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result['d'])
PYCODE
```

`cat > ...` สร้างสคริปต์ตามโค้ดใน block; `lll()` ลด lattice ส่วนเงื่อนไข `candidate * G == Q` ใช้เลือก private key ที่ตรงกับ public key

**Step 3 — รันกับ package**
```bash
.solver-venv/bin/python solve_legacy.py --package player_package --out recovered.json
```

`--package` ระบุโฟลเดอร์ข้อมูลโจทย์และ ec_core.py, `--out` เก็บ private key กับผลคำนวณเป็น JSON

ค่า d ที่ได้:
```text
0x14911ee05a623cb056bf9f43430dbfda855194b3486202ea7db686643b1370b4
```

![[legacy — LLL solver และ private key d]]

---

#### ขั้น 5 — ใช้ UNIT คำนวณ SHA-256

เปิด **Data Hashing → Hash → sha256** วางค่า d ในรูปข้อความนี้ลง INPUT_STREAM:
```text
0x14911ee05a623cb056bf9f43430dbfda855194b3486202ea7db686643b1370b4
```

เก็บ `0x` ไว้ตาม TASK ไม่แปลงข้อความนี้เป็น bytes ด้วย Hex ก่อน hash

OUTPUT คือ:
```text
eec35ec95f3c4683ccf9a13554090b103be65b0038b2d72af9db3880ff398997
```

ใช้ 32 ตัวแรกของ digest แล้วเติม `TCTT2026{...}`
![[legacy — UNIT SHA-256 ของ hex(d)]]

---

#### ขั้น 6 — ปิดเคส

**🚩 Flag = `TCTT2026{eec35ec95f3c4683ccf9a13554090b10}`**
