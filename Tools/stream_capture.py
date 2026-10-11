"""Disk-backed subprocess output. Large streams never accumulate in pipes/RAM."""
from dataclasses import dataclass
from pathlib import Path
import os
import signal
import subprocess
import tempfile
import time

PREVIEW_BYTES = 128 * 1024


@dataclass
class Capture:
    stdout: bytes
    stderr: bytes
    returncode: int | None
    stdout_file: Path | None
    stderr_file: Path | None
    owner: object

    def close(self):
        self.owner.cleanup()


def run_capture(command, input_data=None, cancel_event=None, timeout=30, **kwargs):
    """Caller owns Capture until all consumers of its files have finished.

    File input is streamed by the OS; bytes input is spooled without another copy.
    The private temporary directory is outside the command's working directory.
    """
    owner = tempfile.TemporaryDirectory(prefix='unit-stream-')
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
                    deadline = time.monotonic() + timeout if timeout is not None else None
                    reason = None
                    while process.poll() is None:
                        cancelled = cancel_event is not None and cancel_event.is_set()
                        if cancelled or (deadline is not None and time.monotonic() >= deadline):
                            if os.name == 'posix':
                                try:
                                    os.killpg(process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            else:
                                process.kill()
                            process.wait()
                            reason = b'Cancelled' if cancelled else b'Command timeout'
                            break
                        time.sleep(.02)
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
            return Capture(out.read(PREVIEW_BYTES), err.read(PREVIEW_BYTES), code,
                           folder / 'stdout' if out_size > PREVIEW_BYTES else None,
                           folder / 'stderr' if err_size > PREVIEW_BYTES else None, owner)
    except BaseException:
        owner.cleanup()
        raise
