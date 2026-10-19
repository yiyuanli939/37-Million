#!/usr/bin/env python3
"""把译文里的半角双引号改成中文引号“”（按对齐单元交替配对）。

  tools/punct.py <译文文件>...
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import zh


def fix_quotes(body):
    out, open_ = [], True
    for ch in body:
        if ch == '"':
            out.append("“" if open_ else "”")
            open_ = not open_
        else:
            out.append(ch)
    return "".join(out)


def main():
    for f in sys.argv[1:]:
        p = Path(f)
        meta, units = zh.load(p)
        new = [(a, b, fix_quotes(t)) for a, b, t in units]
        if new != units:
            p.write_text(zh.render(meta, new), encoding="utf-8")
            print("已改", p)


if __name__ == "__main__":
    main()
