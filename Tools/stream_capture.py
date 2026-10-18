"""Disk-backed subprocess output. Large streams never accumulate in pipes/RAM."""
from dataclasses import dataclass
from pathlib import Path
import os
import signal
import shutil
import subprocess
import tempfile
import time
from Tools.app_paths import external_environment

PREVIEW_BYTES = 128 * 1024
MAX_CAPTURE_BYTES = 512 * 1024 * 1024


@dataclass
class Capture:
    stdout: bytes
    stderr: bytes
    returncode: int | None
    stdout_file: Path | None
    stderr_file: Path | None
    owner: object

    # หน้าที่: เก็บกวาด temporary directory ที่เป็นเจ้าของไฟล์ stdout/stderr
    # ที่มา: Tools/stream_capture.py::Capture.__del__ (เรียกตรง)
    # Input: self (Capture) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def close(self):
        self.owner.cleanup()

    # หน้าที่: รวม stdout และ stderr เต็มลงไฟล์รายงานพร้อมหัวข้อแยก stream
    # ที่มา: pages/gemini.py::GeminiPage.process_request (เรียกตรง)
    # Input: self (Capture) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def report_path(self):
        """Full, labelled command output without joining both streams in RAM."""
        folder = Path(self.owner.name)
        destination = folder / 'command-output.txt'
        with destination.open('wb') as output:
            output.write(f'Exit code: {self.returncode}\nstdout:\n'.encode())
            with (folder / 'stdout').open('rb') as source:
                shutil.copyfileobj(source, output, 65536)
            output.write(b'\nstderr:\n')
            with (folder / 'stderr').open('rb') as source:
                shutil.copyfileobj(source, output, 65536)
        return destination

    # หน้าที่: คืนทรัพยากรของ capture เมื่อ object หมดอายุ
    # ที่มา: Python เรียกผ่านวงจรชีวิตของ object หรือ protocol ของคลาส
    # Input: self (Capture) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


# หน้าที่: รัน subprocess โดยเก็บ stream ลงดิสก์ ตรวจ timeout/cancel และจำกัดขนาด output
# ที่มา: Pipeline/pipeline_engine.py::PipelineEngine._communicate (เรียกตรง)
# ที่มา: pages/file_inspection.py::FileInspectionPage._external_analysis (เรียกตรง)
# ที่มา: pages/gemini.py::GeminiPage.call_gemini_cli (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: command (str | list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: input_data (bytes | Path | None) — stdin ที่ engine/worker เตรียมเป็น bytes หรือ Path สำหรับอ่านแบบ streaming
# Input: cancel_event (threading.Event หรือ object ที่มี is_set() -> bool | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: timeout (float | int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: on_process (Callable[[subprocess.Popen], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
# Input: **kwargs (dict[str, Any]) — keyword arguments เพิ่มเติมจากผู้เรียก ส่งต่อไปยัง API ภายใน
def run_capture(command, input_data=None, cancel_event=None, timeout=30, on_process=None, **kwargs):
    """Caller owns Capture until all consumers of its files have finished.

    File input is streamed by the OS; bytes input is spooled without another copy.
    The private temporary directory is outside the command's working directory.
    """
    owner = tempfile.TemporaryDirectory(prefix='unit-stream-')
    kwargs['env'] = external_environment(kwargs.get('env'))
    folder = Path(owner.name)
    try:
        with (folder / 'stdout').open('w+b') as out, (folder / 'stderr').open('w+b') as err:
            if isinstance(input_data, Path):
                incoming = input_data.open('rb')
            else:
                incoming = tempfile.TemporaryFile()
                if input_data:
                    incoming.write(input_data)
                incoming.seek(0)
            with incoming:
                with subprocess.Popen(command, stdin=incoming, stdout=out, stderr=err,
                                      start_new_session=(os.name == 'posix'), **kwargs) as process:
                    if on_process:
                        on_process(process)
                    deadline = time.monotonic() + timeout if timeout is not None else None
                    reason = None
                    while process.poll() is None:
                        cancelled = cancel_event is not None and cancel_event.is_set()
                        oversized = os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > MAX_CAPTURE_BYTES
                        if cancelled or oversized or (deadline is not None and time.monotonic() >= deadline):
                            if os.name == 'posix':
                                try:
                                    os.killpg(process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            else:
                                process.kill()
                            process.wait()
                            reason = (b'Cancelled' if cancelled else b'Output exceeded 512 MiB safety limit; partial output retained' if oversized else b'Command timeout')
                            break
                        time.sleep(.02)
                    # A short-lived process may exit between polls after writing
                    # beyond the budget. Never report that partial capture as success.
                    if not reason and os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > MAX_CAPTURE_BYTES:
                        reason = b'Output exceeded safety limit; partial output retained'
                    code = None if reason else process.returncode
            if reason:
                err.seek(0, os.SEEK_END)
                err.write(b'\n' + reason)
            out.flush()
            err.flush()
            out_size = out.seek(0, os.SEEK_END)
            err_size = err.seek(0, os.SEEK_END)
            out.seek(0)
            err.seek(0)
            error_preview = err.read(PREVIEW_BYTES)
            if reason and reason not in error_preview:
                error_preview += b'\n' + reason
            return Capture(out.read(PREVIEW_BYTES), error_preview, code,
                           folder / 'stdout' if out_size > PREVIEW_BYTES else None,
                           folder / 'stderr' if err_size > PREVIEW_BYTES else None, owner)
    except BaseException:
        owner.cleanup()
        raise
