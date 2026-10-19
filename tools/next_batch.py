#!/usr/bin/env python3
"""按排序找出下一批未完成的作品或片段，默认约 2 万词。

  tools/next_batch.py [--words 20000] [--json]
输出每行：order eul_wid 起-止 词数 作者 · 作品
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from common import MANIFEST, read_csv, zh_path
import zh
import parse_greek


def pending(limit_words, aid=None, skip=()):
    out, total = [], 0
    for r in read_csv(MANIFEST):
        if aid and r["eul_aid"] != aid:
            continue
        if r["eul_wid"] in skip:
            continue
        n = int(r["units"])
        if not n:
            continue
        p = zh_path(r["period"], r["author_slug"], r["eul_wid"])
        done = zh.covered(p)
        if done >= n:
            continue
        units = parse_greek.load(r["eul_wid"]).units
        lo, hi, w = done + 1, done, 0
        for u in units[done:]:
            if total + w and total + w + u.words > limit_words and hi >= lo:
                break
            hi, w = u.seq, w + u.words
        out.append(dict(order=int(r["order"]), eul_wid=r["eul_wid"], start=lo, end=hi, words=w,
                        author=r["author_en"], work=r["work_en"], path=str(p.relative_to(p.parents[3])),
                        units=n))
        total += w
        if total >= limit_words:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", type=int, default=20000)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--author", help="只取这位作者（eul_aid）")
    a = ap.parse_args()
    items = pending(a.words, a.author)
    if a.json:
        json.dump(items, sys.stdout, ensure_ascii=False, indent=1)
        return
    for it in items:
        print(f"{it['order']}\t{it['eul_wid']}\t{it['start']}-{it['end']}/{it['units']}\t{it['words']}\t"
              f"{it['author']} · {it['work']}")
    print(f"共 {sum(i['words'] for i in items)} 词")


if __name__ == "__main__":
    main()
