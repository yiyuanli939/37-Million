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


# 异译后面紧跟这些字时，多半是另一个更长的音译名（如"潘菲洛斯"里的"菲洛"），不算异译
NAME_TAIL = set("斯罗洛亚娅翁昂尼俄忒特拉达姆")


def load_variants():
    """返回 (异译→正名, 全部正名)。"""
    p = ROOT / "glossary" / "names.tsv"
    out, names = {}, set()
    if not p.exists():
        return out, names
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            names.add(re.sub(r"（.*?）", "", r["中文"]))
            for v in filter(None, (r.get("异译") or "").split("|")):
                out[v.strip()] = r["中文"]
    return out, names


def find_variants(text, variants):
    """找出 text 中的异译，返回 [(起, 止, 异译, 正名)]（不含落在已登记正名里的）。"""
    var, names = variants
    masked = list(text)
    for n in sorted(names, key=len, reverse=True):
        if len(n) < 2:
            continue
        for m in re.finditer(re.escape(n), text):
            for i in range(m.start(), m.end()):
                masked[i] = "\0"
    masked = "".join(masked)
    hits = []
    for v, right in variants[0].items():
        for m in re.finditer(re.escape(v), masked):
            nxt = masked[m.end():m.end() + 1]
            if nxt and nxt in NAME_TAIL:
                continue
            hits.append((m.start(), m.end(), v, re.sub(r"（.*?）", "", right)))
    return sorted(hits)


def fix_variants(text, variants):
    for a, b, v, right in reversed(find_variants(text, variants)):
        text = text[:a] + right + text[b:]
    return text


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
        text_only = "\n".join(l for l in body.split("\n") if not l.startswith("> "))
        outside = PAREN.sub("", text_only)
        g = GREEK.findall(outside)
        if len(g) > 3 and meta.get("keep_greek") != "yes":
            errs.append(f"{tag}：残留希腊文 {''.join(g[:20])}")
        if '"' in body:
            errs.append(f"{tag}：半角双引号，应为“”（可用 tools/punct.py 修正）")
        cj = len(CJK.findall(body))
        if gw >= RATIO_MIN_WORDS:
            r = cj / gw
            if r < RATIO_LO or r > RATIO_HI:
                warns.append(f"{tag}：长度比例 {r:.2f}（{gw} 词 / {cj} 字）")
        for _, _, v, right in find_variants(body, variants):
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
