#!/usr/bin/env python3
"""把一批（作品+单元范围）切成约 2000 词的翻译段，切在单元边界上。

诗歌尽量切在句末（单元以 . · ; 结尾），散文尽量切在 [para] 前。
  tools/segments.py <eul_wid> <起>-<止> [--words 2000]
输出每行：eul_wid 起-止 词数
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import parse_greek

END = (".", "·", ";", "!", "]", "·")


def good_cut(units, j):
    """在 units[j] 之前切是否合适。"""
    prev, nxt = units[j - 1], units[j]
    return prev.text.rstrip().endswith(END) or nxt.text.lstrip().startswith("[para]")


def cut(wid, lo, hi, target=2000):
    units = parse_greek.load(wid).units[lo - 1:hi]
    segs, start, n = [], 0, len(units)
    while start < n:
        w, j = 0, start
        while j < n and w < target:
            w += units[j].words
            j += 1
        # j 是候选切点（在 units[j] 之前切）；向后找句末，最多多走 15%
        k, extra = j, 0
        while k < n and not good_cut(units, k) and extra < target * 0.15:
            extra += units[k].words
            k += 1
        if k < n and not good_cut(units, k):
            k = j
        rest = sum(u.words for u in units[k:])
        if rest < target * 0.3:   # 尾巴太短，并入本段
            k = n
        segs.append((units[start].seq, units[k - 1].seq, sum(u.words for u in units[start:k])))
        start = k
    return segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wid")
    ap.add_argument("range")
    ap.add_argument("--words", type=int, default=2000)
    a = ap.parse_args()
    lo, hi = map(int, a.range.split("-"))
    for s in cut(a.wid, lo, hi, a.words):
        print(f"{a.wid}\t{s[0]}-{s[1]}\t{s[2]}")


if __name__ == "__main__":
    main()
