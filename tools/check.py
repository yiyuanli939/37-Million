#!/usr/bin/env python3
"""检查译文文件。全部通过返回 0。

  tools/check.py texts/.../aau-ag.zh.md ...   # 检查指定文件
  tools/check.py --all                        # 检查 texts/ 下全部译文

检查项：对齐覆盖（无缝、无重叠、不越界，完成状态下须覆盖全部单元）、
长度比例异常、残留希腊文（术语括注除外）、专名异译、空单元、元数据。
"""
import argparse
import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import MANIFEST, ROOT, read_csv
import zh
import parse_greek

GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
PAREN = re.compile(r"（[^（）]*）")
CJK = re.compile(r"[一-鿿]")
STATUSES = {"draft", "reviewed", "human-reviewed"}
REQUIRED = ["eul_wid", "title_zh", "author_zh", "source_commit", "status", "translator"]
# 每个希腊词对应的汉字数，正常约 1.5–3.5。只对较长单元判断。
RATIO_LO, RATIO_HI, RATIO_MIN_WORDS = 0.6, 7.0, 25


def load_variants():
    p = ROOT / "glossary" / "names.tsv"
    out = {}
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            for v in filter(None, (r.get("异译") or "").split("|")):
                out[v.strip()] = r["中文"]
    return out


def check_file(path, man, variants):
    errs, warns = [], []
    meta, units = zh.load(path)
    wid = meta.get("eul_wid") or path.name.split(".")[0]
    for k in REQUIRED:
        if not meta.get(k):
            errs.append(f"元数据缺少 {k}")
    if meta.get("status") and meta["status"] not in STATUSES:
        errs.append(f"status 不合法：{meta['status']}")
    if wid not in man:
        errs.append(f"清单中没有 {wid}")
        return errs, warns
    src = parse_greek.load(wid).units
    n = len(src)
    expect = 1
    for a, b, t in units:
        tag = f"@{a}" + (f"-{b}" if b != a else "")
        if a != expect:
            errs.append(f"{tag}：应从 @{expect} 开始（{'重叠' if a < expect else '缺漏'}）")
        if b < a:
            errs.append(f"{tag}：止小于起")
        if b > n:
            errs.append(f"{tag}：超出原文单元数 {n}")
        expect = max(expect, b + 1)
        body = t.strip()
        gw = sum(u.words for u in src[a - 1:min(b, n)])
        if not body:
            if gw:
                errs.append(f"{tag}：空单元")
            continue
        outside = PAREN.sub("", body)
        g = GREEK.findall(outside)
        if len(g) > 3 and meta.get("keep_greek") != "yes":
            errs.append(f"{tag}：残留希腊文 {''.join(g[:20])}")
        cj = len(CJK.findall(body))
        if gw >= RATIO_MIN_WORDS:
            r = cj / gw
            if r < RATIO_LO or r > RATIO_HI:
                warns.append(f"{tag}：长度比例 {r:.2f}（{gw} 词 / {cj} 字）")
        for v, right in variants.items():
            if v in body:
                errs.append(f"{tag}：异译“{v}”，应为“{right}”")
    if meta.get("status") in ("reviewed", "human-reviewed") and expect - 1 < n:
        errs.append(f"状态为 {meta['status']}，但只覆盖到 @{expect - 1}/{n}")
    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--strict", action="store_true", help="警告也算失败")
    a = ap.parse_args()
    files = [Path(f) for f in a.files]
    if a.all:
        files = sorted((ROOT / "texts").rglob("*.zh.md"))
    man = {r["eul_wid"]: r for r in read_csv(MANIFEST)}
    variants = load_variants()
    bad = 0
    for f in files:
        errs, warns = check_file(f, man, variants)
        for e in errs:
            print(f"错误 {f}: {e}")
        for w in warns:
            print(f"警告 {f}: {w}")
        if errs or (a.strict and warns):
            bad += 1
    print(f"检查 {len(files)} 个文件，{bad} 个未通过")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
