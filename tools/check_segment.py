#!/usr/bin/env python3
"""检查一个翻译段文件（无 YAML 头）是否覆盖指定范围、无残留希腊文、无空单元。

  tools/check_segment.py <eul_wid> <起>-<止> <段文件>
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import parse_greek
import zh
from check import CJK, GREEK, PAREN


def main():
    wid, rng, path = sys.argv[1:4]
    lo, hi = map(int, rng.split("-"))
    _, units = zh.parse(Path(path).read_text(encoding="utf-8"))
    src = parse_greek.load(wid).units
    errs, expect = [], lo
    for a, b, t in units:
        if a != expect:
            errs.append(f"@{a}：应从 @{expect} 开始")
        if b < a or b > hi:
            errs.append(f"@{a}-{b}：范围错误")
        expect = max(expect, b + 1)
        body = "\n".join(l for l in t.split("\n") if not l.startswith("> "))
        if not body.strip() and any(u.words for u in src[a - 1:b]):
            errs.append(f"@{a}：空单元")
        g = GREEK.findall(PAREN.sub("", body))
        if len(g) > 3:
            errs.append(f"@{a}：残留希腊文 {''.join(g[:15])}")
    if expect != hi + 1:
        errs.append(f"未覆盖到 @{hi}（止于 @{expect - 1}）")
    for e in errs:
        print("错误", e)
    print("通过" if not errs else f"{len(errs)} 处错误")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
