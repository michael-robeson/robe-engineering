#!/usr/bin/env python3
"""Check staged Python blobs rather than the working tree."""

import subprocess
import sys


def main() -> int:
    paths = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    for raw_path in paths:
        if not raw_path.endswith(b".py"):
            continue
        path = raw_path.decode("utf-8", errors="surrogateescape")
        blob = subprocess.run(
            ["git", "show", f":{path}"], check=True, capture_output=True
        ).stdout
        try:
            compile(blob, path, "exec")
        except (SyntaxError, ValueError) as error:
            print(f"Invalid staged Python file {path}: {error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
