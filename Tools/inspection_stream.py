"""Streaming strings extraction for File Inspection.

The caller supplies a private temporary destination. An invalid UTF-8 pass
is restarted as binary, emitting printable ASCII runs in ``  run\n`` format,
without retaining a long run in memory.
"""
from pathlib import Path
from typing import Callable
import codecs

CHUNK_SIZE = 64 * 1024


class ExtractionCancelled(Exception):
    """Raised when the caller requests cancellation."""


def _cancel(cancelled: Callable[[], bool]) -> None:
    if cancelled and cancelled():
        raise ExtractionCancelled()


def extract_strings(source: Path, destination: Path,
                    cancelled: Callable[[], bool] = lambda: False) -> None:
    """Extract strings from *source* to *destination* using bounded memory.

    Valid UTF-8 is copied as decoded text with chunk boundaries handled by an
    incremental decoder. Invalid UTF-8 falls back to printable ASCII runs of
    four or more bytes, each prefixed by two spaces and terminated by a newline.
    The binary run keeps at most three bytes pending until its minimum length is
    established; the remainder is written immediately.
    """
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        decoder = codecs.getincrementaldecoder("utf-8")("strict")
        with source.open("rb") as incoming, destination.open("w", encoding="utf-8", newline="") as output:
            for chunk in iter(lambda: incoming.read(CHUNK_SIZE), b""):
                _cancel(cancelled)
                output.write(decoder.decode(chunk))
            output.write(decoder.decode(b"", final=True))
        return
    except UnicodeDecodeError:
        pass

    # The first pass may have written a valid prefix; binary output must start
    # from scratch so that prefix is never duplicated.
    with destination.open("w", encoding="ascii", newline="") as output:
        pending = bytearray()
        active = False
        with source.open("rb") as incoming:
            for chunk in iter(lambda: incoming.read(CHUNK_SIZE), b""):
                _cancel(cancelled)
                for value in chunk:
                    if 0x20 <= value <= 0x7E:
                        if not active:
                            pending.append(value)
                            if len(pending) == 4:
                                output.write("  ")
                                output.write(pending.decode("ascii"))
                                pending.clear()
                                active = True
                        else:
                            output.write(chr(value))
                    else:
                        if active:
                            output.write("\n")
                        pending.clear()
                        active = False
            _cancel(cancelled)
            if active:
                output.write("\n")
