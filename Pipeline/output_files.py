"""Discover output files without changing a command's working directory."""
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CommandResult:
    stdout: bytes = b""
    stderr: bytes = b""
    returncode: int | None = None
    files: list[Path] = field(default_factory=list)
    discovery_note: str = ""
    stdout_file: Path | None = None
    stderr_file: Path | None = None

    # หน้าที่: รายงานว่าคำสั่งจบสำเร็จเมื่อ returncode เท่ากับศูนย์
    # ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._run_command (อ้างอิง/callback)
    # ที่มา: Tools/package_smoke.py::main (อ้างอิง/callback)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.show_result (อ้างอิง/callback)
    # ที่มาเพิ่มเติม: อีก 3 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (CommandResult) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    @property
    def succeeded(self):
        return self.returncode == 0


# หน้าที่: อ่าน flags ของคำสั่งเพื่อรวบรวมตำแหน่งที่จะตรวจไฟล์ผลลัพธ์
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._run_command (เรียกตรง)
# Input: command (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: input_path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def output_locations(command, input_path=None):
    """Watch default locations plus output options of supported CLI tools.

    Do not treat every -o/-d as an output path: grep/cut use them differently.
    Unknown custom destinations can still be selected manually in the UI.
    """
    locations = [Path.cwd()]
    if input_path:
        locations.append(Path(input_path).absolute().parent)
    executable = Path(command[0]).name
    flags = {
        "openssl": {"-out"}, "unzip": {"-d"},
        "7z": {"-o"}, "7za": {"-o"}, "7zz": {"-o"},
        "tar": {"-C", "--directory"}, "steghide": {"-xf", "--extractfile"},
        "foremost": {"-o"}, "binwalk": {"-C", "--directory"},
        "apktool": {"-o", "--output"}, "jadx": {"-d", "--output-dir"},
        "tshark": {"-w"}, "sort": {"-o", "--output"},
    }.get(executable, set())
    for index, arg in enumerate(command[1:], 1):
        value = None
        if arg in flags and index + 1 < len(command):
            value = command[index + 1]
        elif arg.partition("=")[0] in flags and "=" in arg:
            value = arg.partition("=")[2]
        elif executable in {"7z", "7za", "7zz"} and arg.startswith("-o"):
            value = arg[2:]
        elif executable == "dd" and arg.startswith("of="):
            value = arg[3:]
        if value and value != "-":
            locations.append(Path(value).absolute())
    return list(dict.fromkeys(locations))


# หน้าที่: สำรวจ metadata ของไฟล์แบบจำกัดจำนวนและไม่ตาม symbolic link
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._run_command (เรียกตรง)
# Input: locations (Iterable[Path]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: limit (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def snapshot_files(locations, limit=20000):
    """Bound discovery; never follow symlinks or inspect file contents."""
    found = {}
    visited = set()
    pending = list(locations)
    count = 0
    complete = True
    while pending:
        path = pending.pop().absolute()
        if path in visited:
            continue
        visited.add(path)
        count += 1
        if count > limit:
            return found, False
        try:
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                found[path] = (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino)
            elif stat.S_ISDIR(info.st_mode):
                with os.scandir(path) as entries:
                    for entry in entries:
                        if entry.name in {".git", ".venv", "venv", "node_modules", "__pycache__"}:
                            continue
                        pending.append(Path(entry.path))
                        if len(pending) + count > limit:
                            return found, False
        except FileNotFoundError:
            pass
        except OSError:
            complete = False
    return found, complete


# หน้าที่: เปรียบเทียบ metadata ก่อนและหลังเพื่อหาไฟล์ที่เพิ่มหรือเปลี่ยน
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._run_command (เรียกตรง)
# Input: before (dict[Path, tuple[int, int, int, int]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: after (dict[Path, tuple[int, int, int, int]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: input_path (str | PathLike[str] | None) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def changed_files(before, after, input_path=None):
    excluded = Path(input_path).absolute() if input_path else None
    return sorted(
        (path for path, stamp in after.items()
         if path != excluded and before.get(path) != stamp), key=str,
    )
