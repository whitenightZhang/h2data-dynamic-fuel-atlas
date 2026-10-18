"""Verify the delivered package files against its SHA-256 manifest."""
from pathlib import Path
import hashlib
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    count=0
    for line in (ROOT/'checksums.sha256').read_text(encoding='utf-8').splitlines():
        expected,name=line.split('  ',1)
        p=ROOT/name
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):
                h.update(block)
        if h.hexdigest()!=expected:
            raise RuntimeError(f'Checksum mismatch: {name}')
        count+=1
    print(f'PASS: {count} delivered files match checksums.sha256')

if __name__=='__main__':
    main()
