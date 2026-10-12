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

    def close(self):
        self.owner.cleanup()

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

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


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
