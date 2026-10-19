#!/usr/bin/env python3
"""排出一卷的 PDF，并导出对齐数据（JSONL）。

  tools/build_volume.py V0007 [--out out/] [--allow-partial]

需要先用 tools/fetch_source.py 检出该卷的原文。
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import (GROUP_ZH, MANIFEST, PERIOD_ZH, ROOT, VOLUMES, parse_parts, read_csv, zh_path)
import parse_greek
import zh

SERIES = "古希腊文献希中对照全译"
LICENSE = "CC BY 4.0（https://creativecommons.org/licenses/by/4.0/）"
MARK = re.compile(r"\[(para|bis|so|et|abrasum|spk_[^\]]*|ln_[^\]]*)\]")
STATUS_ZH = {"draft": "AI 初译，未审校", "reviewed": "AI 翻译、AI 审校",
             "human-reviewed": "AI 翻译、人工校订"}
NUM = "〇一二三四五六七八九十"


def zh_num(n):
    if n <= 10:
        return NUM[n]
    if n < 20:
        return "十" + (NUM[n - 10] if n > 10 else "")
    t, o = divmod(n, 10)
    return NUM[t] + "十" + (NUM[o] if o else "")


def segments(text, verse_join):
    segs, pos = [], 0
    text = text.replace("\n\n", "\n")
    for m in MARK.finditer(text):
        if m.start() > pos:
            segs += split_lines(text[pos:m.start()], verse_join)
        k = m.group(1)
        if k == "para":
            segs.append({"k": "para"})
        elif k.startswith("spk_"):
            segs.append({"k": "spk", "v": k[4:]})
        elif k.startswith("ln_"):
            segs.append({"k": "ln", "v": k[3:]})
        else:
            segs.append({"k": "mk", "v": k})
        pos = m.end()
    segs += split_lines(text[pos:], verse_join)
    return segs


def split_lines(t, verse_join):
    out = []
    for i, l in enumerate(t.split("\n")):
        if i:
            out.append({"k": "vl"} if verse_join else {"k": "t", "v": " "})
        if l:
            out.append({"k": "t", "v": l})
    return out


def margin_labels(units, verse, first):
    if not verse:
        return [units[0].label] if units else []
    out = []
    for i, u in enumerate(units):
        m = re.search(r"(\d+)\D*$", u.label)
        if (first and i == 0) or (m and int(m.group(1)) % 5 == 0) or not m:
            out.append(u.label)
        else:
            out.append("")
    while out and out[-1] == "":
        out.pop()
    return out


def volume_titles():
    vols = read_csv(VOLUMES)
    seen, total = {}, {}
    for v in vols:
        total[(v["period"], v["group"])] = total.get((v["period"], v["group"]), 0) + 1
    out = {}
    for v in vols:
        key = (v["period"], v["group"])
        seen[key] = seen.get(key, 0) + 1
        base = f"{PERIOD_ZH[v['period']]}时期·{GROUP_ZH.get(v['group'], v['group'])}"
        auto = base + (f"（{zh_num(seen[key])}）" if total[key] > 1 else "")
        out[v["volume"]] = v["title"] or auto
    return out


def build(vid, out_dir, allow_partial, only=None):
    vols = {v["volume"]: v for v in read_csv(VOLUMES)}
    man = {r["eul_wid"]: r for r in read_csv(MANIFEST)}
    v = vols[vid]
    title = volume_titles()[vid]
    names = []
    p = ROOT / "glossary" / "names.tsv"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            names = list(csv.DictReader(f, delimiter="\t"))
    commit = [l.split("=", 1)[1] for l in (ROOT / "source.lock").read_text().splitlines()
              if l.startswith("commit=")][0]
    works, notes, jsonl, missing = [], [], [], []
    statuses, note_no = set(), 0
    for wid, lo, hi in parse_parts(v["parts"]):
        if only and wid not in only:
            continue
        r = man[wid]
        src = parse_greek.load(wid).units
        path = zh_path(r["period"], r["author_slug"], wid)
        meta, units = zh.load(path) if path.exists() else ({}, [])
        status = meta.get("status", "draft")
        statuses.add(status)
        verse = r["format"] == "Verse"
        rows, wnotes, done = [], [], set()
        for a, b, t in units:
            if b < lo or a > hi:
                continue
            body, nts = [], []
            for line in t.split("\n"):
                if line.startswith("> "):
                    note_no += 1
                    nts.append(note_no)
                    wnotes.append({"n": note_no, "label": src[a - 1].label, "text": line[2:].strip()})
                else:
                    body.append(line)
            us = src[a - 1:b]
            done.update(range(a, b + 1))
            grc = []
            labels = margin_labels(us, verse, not rows)
            for i, u in enumerate(us):
                if i:
                    grc.append({"k": "vl"} if verse else {"k": "t", "v": " "})
                if verse and i < len(labels) and labels[i]:
                    grc.append({"k": "vn", "v": labels[i]})
                grc += segments(u.text, verse)
            rows.append({"margin": [] if verse else labels, "first": us[0].label, "grc": grc,
                         "zh": "\n".join(body).strip(), "notes": [str(n) for n in nts]})
            jsonl.append({"eul_wid": wid, "unit": f"{a}-{b}", "labels": [u.label for u in us],
                          "grc": "\n".join(u.text for u in us), "zh": "\n".join(body).strip(),
                          "status": status, "volume": vid})
        gap = [i for i in range(lo, hi + 1) if i not in done]
        if gap:
            missing.append(f"{wid}: {len(gap)} 个单元未译（自 @{gap[0]}）")
        n = int(r["units"])
        rng = "" if (lo, hi) == (1, n) else f"@{lo}–{hi}"
        tz = meta.get("title_zh", r["work_en"])
        wk = {"eul_wid": wid, "author_zh": meta.get("author_zh", r["author_en"]),
              "title_zh": tz, "author_grc": r["author_grc"], "title_grc": r["work_grc"],
              "author_en": r["author_en"], "title_en": r["work_en"], "range": rng,
              "status_zh": STATUS_ZH.get(status, status), "rows": rows}
        works.append(wk)
        if wnotes:
            notes.append({"work": f"{wk['author_zh']}《{tz}》", "items": wnotes})
    if missing and not allow_partial:
        sys.exit("本卷尚未译完：\n" + "\n".join(missing))
    # 专名索引：中文译名在本卷译文中出现的
    index = []
    for e in names:
        key = re.sub(r"（.*?）", "", e["中文"])
        if len(key) < 2:
            continue
        where = []
        for w in works:
            for row in w["rows"]:
                if key in row["zh"]:
                    where.append(f"《{w['title_zh']}》{row['first']}")
                    break
        if where:
            index.append({"zh": e["中文"], "grc": e["希腊文"], "where": "；".join(where[:4])})
    index.sort(key=lambda e: e["zh"].encode("gb18030"))
    data = {"volume": vid, "title": title, "series": SERIES, "period_zh": PERIOD_ZH[v["period"]],
            "source_commit": commit, "license": LICENSE, "works": works, "notes": notes,
            "index": index, "human_reviewed": "human-reviewed" in statuses}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dpath = ROOT / "build" / f".{vid}.json"
    dpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    pdf = out_dir / f"{vid}.pdf"
    import typst
    typst.compile(str(ROOT / "build" / "volume.typ"), output=str(pdf), root=str(ROOT),
                  sys_inputs={"data": f".{vid}.json"})
    with open(out_dir / f"{vid}.jsonl", "w", encoding="utf-8") as f:
        for j in jsonl:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    dpath.unlink()
    print(f"{pdf}（{pdf.stat().st_size / 1e6:.1f} MB），{len(jsonl)} 个对齐单元")
    for m in missing:
        print("缺：", m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--only", nargs="*", help="只排这些作品（试样用）")
    a = ap.parse_args()
    build(a.volume, a.out, a.allow_partial, set(a.only or []))


if __name__ == "__main__":
    main()
