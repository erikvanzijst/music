#!/usr/bin/env python3
import os
import sys
from collections import defaultdict
from hashlib import file_digest
from itertools import groupby
from pathlib import Path

extensions = {'.mp3', '.flac', '.ogg', '.oga', '.mogg', '.opus', '.vox', '.webm', '.m4a', '.wav', '.wma', '.aac', '.aax', '.m4b'}

if __name__ == "__main__":
    by_size = (paths for size, paths in ((size, list(it)) for size, it in groupby(
        filter(lambda p: Path(p).suffix.lower() in extensions,
               sorted((os.path.join(parent, fn) for parent, _, fns in os.walk(sys.argv[1]) for fn in fns),
                      key=lambda p: os.stat(p).st_size)),
        key=lambda p: os.stat(p).st_size)) if len(paths) > 1)

    for fns in by_size:
        by_csum: dict[str, list[str]] = defaultdict(list)
        for fn in fns:
            with open(fn, 'rb') as f:
                by_csum[file_digest(f, 'md5').hexdigest()].append(fn)

        dups: list[list[str]] = [sorted(fns, key=len) for _, fns in by_csum.items() if len(fns) > 1]
        for fns in dups:
            print('\n'.join((f'[{i}]  {fn}' for i, fn in enumerate(fns, start=1))))
            while True:
                try:
                    if (k := int(input(f'Which one would you like to keep? [1] ') or '1') - 1) >= 0 and k < len(fns):
                        break
                except ValueError:
                    pass
            fns.pop(k)
            print(f'Removing {fns}\n')
            for fn in fns:
                os.unlink(fn)
