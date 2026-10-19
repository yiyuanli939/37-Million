#!/usr/bin/env python3
"""计算词数，排序，分卷，生成 manifest.csv 和 volumes.csv。

需要先 `tools/fetch_source.py --all`。
排序号 order 一旦生成，人工微调只改 manifest.csv 的 order 列，再加 --keep-order 重跑分卷。
"""
import argparse
import json
import math
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import (GROUP_ORDER, GROUP_ZH, MANIFEST, PERIOD_ZH, PERIODS, SRC, VOLUMES,
                    read_csv, write_csv)
import parse_greek

TARGET = 75_000
MAX_FILL = int(TARGET * 1.1)   # 加入下一部作品后不超过这个量，就留在本卷
SPLIT_OVER = 110_000           # 超过这个量的单部作品拆卷
NEW_GROUP_AT = int(TARGET * 0.4)

MF = ["order", "eul_wid", "eul_aid", "author_slug", "author_en", "author_grc", "work_en",
      "work_grc", "period", "group", "domain", "format", "dialect", "words", "units", "volumes"]
VF = ["volume", "period", "group", "title", "parts", "words"]


def group_of(author):
    aff = author.get("affiliation") or ""
    if aff and aff in GROUP_ORDER:
        return aff
    return author.get("domain") or ""


def book_key(label):
    """取标签里表示"卷/书"的第一级，用来找拆卷边界。"""
    m = re.match(r"\s*(?:book\s+)?([^\s.:,]+)", label, re.I)
    return m.group(1) if m else label


def split_points(units, k):
    """把 units 拆成 k 份，尽量切在书的边界上，返回每份的 (起, 止)。"""
    words = [u.words for u in units]
    total = sum(words)
    cum, s = [], 0
    for w in words:
        s += w
        cum.append(s)
    cuts, prev = [], 0
    for i in range(1, k):
        ideal = total * i / k
        window = total / k * 0.2
        cands = [j for j in range(prev + 1, len(units))
                 if abs(cum[j - 1] - ideal) <= window and book_key(units[j].label) != book_key(units[j - 1].label)]
        if cands:
            j = min(cands, key=lambda j: abs(cum[j - 1] - ideal))
        else:
            j = min(range(prev + 1, len(units)), key=lambda j: abs(cum[j - 1] - ideal))
        cuts.append(j)
        prev = j
    bounds, a = [], 1
    for c in cuts:
        bounds.append((a, c))
        a = c + 1
    bounds.append((a, len(units)))
    return bounds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-order", action="store_true", help="沿用 manifest.csv 已有的 order")
    a = ap.parse_args()

    m = json.load(open(SRC / "manifest.json", encoding="utf-8"))
    csvrows = {r["eul_wid"]: r for r in read_csv(SRC / "manifest.csv")}
    works = []
    for au in m["authors"]:
        grp = group_of(au)
        for w in au["works"]:
            r = csvrows[w["eul_wid"]]
            parsed = parse_greek.load(w["eul_wid"])
            works.append(dict(
                eul_wid=w["eul_wid"], eul_aid=au["eul_aid"], author_slug=au["author_display_string"],
                author_en=au["name_english"], author_grc=au["name_greek"],
                work_en=w["title_english"], work_grc=w["title_greek"],
                period=au["period"] or "Uncertain", group=grp, domain=r["domain"], format=parsed.meta.get("format") or r["format"],
                dialect=r["dialect"], words=parsed.words, units=len(parsed.units), _parsed=parsed))
    if a.keep_order:
        old = {r["eul_wid"]: int(r["order"]) for r in read_csv(MANIFEST)}
        works.sort(key=lambda w: old[w["eul_wid"]])
    else:
        works.sort(key=lambda w: (PERIODS.index(w["period"]), GROUP_ORDER[w["group"]],
                                  w["author_en"].lower(), w["eul_aid"], w["eul_wid"]))

    vols, cur = [], None

    def new_vol(w):
        nonlocal cur
        cur = dict(period=w["period"], group=w["group"], parts=[], words=0)
        vols.append(cur)

    for w in works:
        if w["words"] == 0 and w["units"] == 0:
            continue
        if cur is None or cur["period"] != w["period"]:
            new_vol(w)
        elif cur["group"] != w["group"] and cur["words"] >= NEW_GROUP_AT:
            new_vol(w)
        if w["words"] > SPLIT_OVER:
            if cur["words"]:
                new_vol(w)
            k = math.ceil(w["words"] / TARGET)
            units = w["_parsed"].units
            for i, (lo, hi) in enumerate(split_points(units, k)):
                if i:
                    new_vol(w)
                cur["parts"].append((w["eul_wid"], lo, hi))
                cur["words"] += sum(u.words for u in units[lo - 1:hi])
            continue
        if cur["words"] and cur["words"] + w["words"] > MAX_FILL:
            new_vol(w)
        cur["parts"].append((w["eul_wid"], 1, w["units"]))
        cur["words"] += w["words"]

    vol_of = {}
    vrows = []
    for i, v in enumerate(vols, 1):
        vid = f"V{i:04d}"
        for wid, lo, hi in v["parts"]:
            vol_of.setdefault(wid, []).append(vid)
        vrows.append(dict(volume=vid, period=v["period"],
                          group=v["group"], title="",
                          parts=";".join(f"{wid}@{lo}-{hi}" for wid, lo, hi in v["parts"]),
                          words=v["words"]))
    mrows = []
    for i, w in enumerate(works, 1):
        w = {k: v for k, v in w.items() if not k.startswith("_")}
        w["order"] = i
        w["volumes"] = ";".join(vol_of.get(w["eul_wid"], []))
        mrows.append(w)
    write_csv(MANIFEST, mrows, MF)
    write_csv(VOLUMES, vrows, VF)
    total = sum(w["words"] for w in mrows)
    print(f"作品 {len(mrows)}，希腊词 {total:,}（清单记 {m['counts']['greek_words']:,}，"
          f"差 {(total - m['counts']['greek_words']) / m['counts']['greek_words']:+.2%}），卷数 {len(vrows)}")
    empty = [w["eul_wid"] for w in mrows if not w["units"]]
    if empty:
        print("无正文的作品：", " ".join(empty))


if __name__ == "__main__":
    main()
