#!/usr/bin/env python3
"""강의 보완 제안 마커를 검토 결과대로 정리한다.

사용법:
    python3 apply_lecture.py            # 저장소 전체
    python3 apply_lecture.py ch05_오류공간/5.1_오류구조.md
    python3 apply_lecture.py --dry-run  # 반영하지 않고 집계만

마커 규약:
    <!-- +강의 id=... 채택=? -->
    본문
    <!-- /+강의 -->

  채택=y  → 마커 두 줄만 제거하고 본문을 교재에 남긴다
  채택=n  → 블록 전체를 제거한다
  채택=?  → 손대지 않고 '미검토'로 보고한다

한 파일에 미검토가 하나도 남지 않으면 파일 머리의 안내 주석도 함께 지운다.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

OPEN = re.compile(r'^<!--\s*\+강의\s+(.*?)\s*-->\s*$')
CLOSE = re.compile(r'^<!--\s*/\+강의\s*-->\s*$')
HEAD_OPEN = re.compile(r'^<!--\s*─+\s*강의 음성 기반 보완 제안')
HEAD_CLOSE = re.compile(r'─+\s*-->\s*$')
DECIDE = re.compile(r'채택=([yn?])')


def process(path: Path, dry: bool):
    lines = path.read_text(encoding='utf-8').split('\n')
    out, i = [], 0
    n_y = n_n = n_q = 0
    head = []
    while i < len(lines):
        if HEAD_OPEN.match(lines[i]):
            j = i
            while j < len(lines) and not HEAD_CLOSE.search(lines[j]): j += 1
            head = lines[i:j+1]
            i = j + 1
            if i < len(lines) and not lines[i].strip(): i += 1
            continue
        m = OPEN.match(lines[i])
        if m:
            j = i + 1
            body = []
            while j < len(lines) and not CLOSE.match(lines[j]):
                body.append(lines[j]); j += 1
            if j >= len(lines):                      # 닫는 마커 없음 — 원본 유지
                out.append(lines[i]); i += 1; continue
            d = DECIDE.search(m.group(1))
            d = d.group(1) if d else '?'
            if d == 'y':
                n_y += 1
                out.extend(body)
            elif d == 'n':
                n_n += 1
                while out and not out[-1].strip(): out.pop()   # 앞선 빈 줄 정리
                if j + 1 < len(lines) and lines[j+1].strip():
                    out.append('')
            else:
                n_q += 1
                out.append(lines[i]); out.extend(body); out.append(lines[j])
            i = j + 1
            continue
        out.append(lines[i]); i += 1

    if n_q and head:                                  # 미검토가 남으면 안내를 되돌린다
        out = head + [''] + out
    txt = re.sub(r'\n{4,}', '\n\n\n', '\n'.join(out))
    if not dry and (n_y or n_n):
        path.write_text(txt, encoding='utf-8')
    return n_y, n_n, n_q


def main():
    args = [a for a in sys.argv[1:] if a != '--dry-run']
    dry = '--dry-run' in sys.argv
    root = Path('.')
    targets = [Path(a) for a in args] if args else sorted(root.glob('ch0*/[0-9]*.md'))
    T = [0, 0, 0]
    print(f"{'파일':44} {'채택':>5}{'기각':>5}{'미검토':>7}")
    for p in targets:
        if not p.exists():
            print(f"  !! 없음: {p}"); continue
        y, n, q = process(p, dry)
        if y or n or q:
            print(f"{str(p):44} {y:5d}{n:5d}{q:7d}")
        T[0] += y; T[1] += n; T[2] += q
    print(f"{'합계':44} {T[0]:5d}{T[1]:5d}{T[2]:7d}")
    if dry: print("\n(--dry-run: 파일을 고치지 않았다)")
    elif T[2]: print(f"\n미검토 {T[2]}건이 남아 있다. 다 정하면 한 번 더 실행하라.")
    else: print("\n전부 정리됐다. 남은 마커 없음.")


if __name__ == '__main__':
    main()
