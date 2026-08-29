#!/usr/bin/env python3
"""강의 보완 제안 마커를 검토 결과대로 정리한다.

사용법:
    python3 apply_lecture.py                 # 판정대로 반영
    python3 apply_lecture.py --dry-run       # 반영하지 않고 집계만
    python3 apply_lecture.py --review        # 제안을 앞뒤 맥락과 함께 훑어본다
    python3 apply_lecture.py --review -c 6   # 맥락을 위아래 6줄씩
    python3 apply_lecture.py --review --all  # 판정 끝난 것까지 전부
    python3 apply_lecture.py ch05_오류공간/5.1_오류구조.md   # 한 파일만

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
import re, sys, textwrap
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


BAR = '━' * 74
TTY = sys.stdout.isatty()
B0, B1 = ('\033[1m', '\033[0m') if TTY else ('', '')


def show(path: Path, ctx: int, only_undecided: bool):
    """제안을 앞뒤 맥락과 함께 출력한다. 파일은 건드리지 않는다."""
    lines = path.read_text(encoding='utf-8').split('\n')
    marks = []
    for i, L in enumerate(lines):
        m = OPEN.match(L)
        if not m:
            continue
        j = i + 1
        while j < len(lines) and not CLOSE.match(lines[j]):
            j += 1
        d = DECIDE.search(m.group(1))
        marks.append((i, j, m.group(1), d.group(1) if d else '?'))
    shown = [k for k in marks if not (only_undecided and k[3] != '?')]
    if not shown:
        return 0
    print(f"\n{BAR}\n  {path}   제안 {len(marks)}건"
          f"{f' (미검토 {len(shown)}건)' if only_undecided else ''}\n{BAR}")
    for n, (i, j, meta, d) in enumerate(shown, 1):
        tag = {'y': '채택', 'n': '기각', '?': '미검토'}[d]
        info = ' '.join(t for t in meta.split() if not t.startswith('채택='))
        print(f"\n[{n}/{len(shown)}] {info}   ▶ {tag}")
        # 앞 맥락 — 마커 바로 위에서 내용 있는 줄을 ctx 개 모은다
        before, k = [], i - 1
        while k >= 0 and len(before) < ctx:
            if lines[k].strip():
                before.append((k, lines[k]))
            k -= 1
        for k, L in reversed(before):
            print(f"  {k:5d} │ {L[:96]}")
        print("        ┃")
        body = ' '.join(x.strip() for x in lines[i+1:j] if x.strip())
        for L in textwrap.wrap(body, width=64) or ['']:
            print(f"        ┃ {B0}{L}{B1}")
        print(f"        ┃  ({len(body)}자)")
        after, k = [], j + 1
        while k < len(lines) and len(after) < ctx:
            if lines[k].strip():
                after.append((k, lines[k]))
            k += 1
        for k, L in after:
            print(f"  {k:5d} │ {L[:96]}")
    return len(shown)


def main():
    argv = sys.argv[1:]
    dry = '--dry-run' in argv
    review = '--review' in argv
    show_all = '--all' in argv
    ctx = 3
    if '-c' in argv:
        ctx = int(argv[argv.index('-c') + 1]); argv.pop(argv.index('-c') + 1)
    args = [a for a in argv if not a.startswith('-')]
    root = Path('.')
    targets = [Path(a) for a in args] if args else sorted(root.glob('ch0*/[0-9]*.md'))

    if review:
        n = sum(show(p, ctx, not show_all) for p in targets if p.exists())
        print(f"\n{BAR}\n  {n}건 표시. 판정은 md 파일에서 마커 줄의 채택= 값을 고친다.")
        print(f"  판정을 마치면  python3 apply_lecture.py  를 실행한다.\n{BAR}")
        return

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
