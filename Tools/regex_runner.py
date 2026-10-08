"""Run user-provided regex outside Tk's process with bounded time/results."""
import json
from pathlib import Path
import re
import subprocess
import sys


def find_match_spans(pattern, text, timeout=2, max_matches=10000):
    request = json.dumps({'pattern': pattern, 'text': text, 'max_matches': max_matches})
    try:
        result = subprocess.run(
            [sys.executable, '-I', str(Path(__file__).resolve())],
            input=request.encode('utf-8'), capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(f'Regex exceeded {timeout:g}s; simplify the pattern or reduce input') from error
    if result.returncode != 0:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip() or 'Regex worker failed')
    return json.loads(result.stdout)


def main():
    try:
        request = json.load(sys.stdin)
        matches = []
        for match in re.finditer(request['pattern'], request['text'], re.IGNORECASE):
            if len(matches) >= request['max_matches']:
                raise ValueError('Regex exceeded match limit; narrow the pattern or reduce input')
            matches.append(match.span())
        print(json.dumps(matches))
    except (ValueError, KeyError, TypeError, re.error) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
