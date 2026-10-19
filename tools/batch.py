#!/usr/bin/env python3
"""批次编排辅助：生成翻译/审校子任务的说明、合并译名、组装译文文件。

  tools/batch.py prompts <eul_wid> <起>-<止> [--words 2000]   # 打印各段翻译说明的 JSON
  tools/batch.py names <eul_wid>                             # 合并 .work/<wid>/*.meta.json 的新专名，回填各段
  tools/batch.py assemble <eul_wid> --title-zh 神谱 --author-zh 赫西俄德
  tools/batch.py review-prompts <eul_wid> <起>-<止> [--words 4000]
"""
import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import MANIFEST, ROOT, read_csv, zh_path
import parse_greek
import segments
import zh

WORK = ROOT / ".work"
NAMES = ROOT / "glossary" / "names.tsv"
TERMS = ROOT / "glossary" / "terms.tsv"
NAME_FIELDS = ["希腊文", "中文", "类别", "来源", "首见作品", "异译"]


def man(wid):
    return {r["eul_wid"]: r for r in read_csv(MANIFEST)}[wid]


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


def ctx_range(units, lo, hi, side, words=300):
    if side == "before":
        j, w = lo - 1, 0
        while j > 1 and w < words:
            j -= 1
            w += units[j - 1].words
        return f"{j}-{lo - 1}" if lo > 1 else None
    j, w = hi, 0
    while j < len(units) and w < words:
        j += 1
        w += units[j - 1].words
    return f"{hi + 1}-{j}" if hi < len(units) else None


def cmd_prompts(a):
    r = man(a.wid)
    units = parse_greek.load(a.wid).units
    lo, hi = map(int, a.range.split("-"))
    tpl = (ROOT / "tools/prompts/translate.md").read_text(encoding="utf-8")
    segs = segments.cut(a.wid, lo, hi, a.words)
    out = []
    for i, (s, e, w) in enumerate(segs):
        d = WORK / a.wid
        d.mkdir(parents=True, exist_ok=True)
        before, after = ctx_range(units, s, e, "before"), ctx_range(units, s, e, "after")
        prev = ""
        if i:
            ps, pe, _ = segs[i - 1]
            prev = (f"- 前一段（@{ps}–@{pe}）由另一个子任务并行翻译，可能尚未完成；"
                    f"如 `{d}/{ps}-{pe}.zh.md` 已存在，可参考其末尾几个单元以求衔接。")
        p = fill(tpl, ROOT=ROOT, AUTHOR=r["author_en"], TITLE=r["work_en"], WID=a.wid,
                 DOMAIN=r["domain"], FORMAT=r["format"], START=s, END=e, WORDS=w,
                 START_PLUS=min(e, s + 3), CTX_BEFORE=before or "（无，本段在作品开头）",
                 CTX_AFTER=after or "（无，本段在作品结尾）", PREV_NOTE=prev,
                 OUT=d / f"{s}-{e}.zh.md", OUT_META=d / f"{s}-{e}.meta.json")
        out.append({"wid": a.wid, "start": s, "end": e, "words": w, "prompt": p})
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


def norm(g):
    g = unicodedata.normalize("NFD", g)
    # 保留首字母大小写：小写开头的修饰语（χρυσάωρ）不与同形专名（Χρυσάωρ）混同
    g = "".join(c for c in g if not unicodedata.combining(c)).replace("ς", "σ")
    return g[:1] + g[1:].lower()


def read_names():
    with open(NAMES, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_names(rows):
    with open(NAMES, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=NAME_FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in NAME_FIELDS})


def cmd_names(a):
    rows = read_names()
    by_grc = {norm(r["希腊文"]): r for r in rows}
    by_zh = {r["中文"]: r for r in rows}
    d = WORK / a.wid
    replace, added, conflicts = {}, [], []
    for mf in sorted(d.glob("*.meta.json")):
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"无法解析 {mf}: {e}")
            continue
        for n in meta.get("new_names", []):
            g, z = n.get("grc", "").strip(), n.get("zh", "").strip()
            if not g or not z:
                continue
            k = norm(g)
            if k in by_grc:
                have = by_grc[k]["中文"]
                if have != z:
                    replace[z] = have
                    conflicts.append(f"{g}：子任务译作“{z}”，译名表已有“{have}”，以已有为准")
                continue
            if z in by_zh and norm(by_zh[z]["希腊文"]) != k:
                conflicts.append(f"{g}→“{z}” 与 {by_zh[z]['希腊文']} 同译名，请人工区分")
            r = {"希腊文": g, "中文": z, "类别": n.get("type", ""), "来源": n.get("source", "音译"),
                 "首见作品": a.wid, "异译": ""}
            rows.append(r)
            by_grc[k] = r
            by_zh.setdefault(z, r)
            added.append(f"{g}\t{z}")
    # 回填：把被替换的译名改成译名表已有的
    if replace:
        for sf in d.glob("*.zh.md"):
            t = sf.read_text(encoding="utf-8")
            for old, new in sorted(replace.items(), key=lambda x: -len(x[0])):
                if old not in new:
                    t = t.replace(old, new)
            sf.write_text(t, encoding="utf-8")
    write_names(rows)
    # 把异译统一改成译名表的正名
    import check
    variants = check.load_variants()
    fixed = 0
    for sf in d.glob("*.zh.md"):
        t = sf.read_text(encoding="utf-8")
        t2 = check.fix_variants(t, variants)
        if t2 != t:
            fixed += len(check.find_variants(t, variants))
            sf.write_text(t2, encoding="utf-8")
    conflicts.append(f"异译改正名 {fixed} 处")
    log = d / "names.log"
    log.write_text("新增：\n" + "\n".join(added) + "\n\n冲突：\n" + "\n".join(conflicts) + "\n",
                   encoding="utf-8")
    print(f"新增专名 {len(added)}，冲突 {len(conflicts)}（详见 {log}）")


def cmd_assemble(a):
    r = man(a.wid)
    d = WORK / a.wid
    segs = sorted(d.glob("*.zh.md"), key=lambda p: int(p.name.split("-")[0]))
    units = []
    for s in segs:
        _, u = zh.parse(s.read_text(encoding="utf-8"))
        units += u
    path = zh_path(r["period"], r["author_slug"], a.wid)
    commit = [l.split("=", 1)[1] for l in (ROOT / "source.lock").read_text().splitlines()
              if l.startswith("commit=")][0][:7]
    old_meta, old_units = zh.load(path) if path.exists() else ({}, [])
    if old_units:
        first = units[0][0] if units else 0
        units = [u for u in old_units if u[1] < first] + units
    meta = {"eul_wid": a.wid, "title_zh": a.title_zh or old_meta.get("title_zh", ""),
            "author_zh": a.author_zh or old_meta.get("author_zh", ""), "source_commit": commit,
            "status": a.status, "translator": "Claude (AI)", "reviewer": "Claude (AI, 独立审校)"
            if a.status == "reviewed" else ""}
    meta = {k: v for k, v in meta.items() if v}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(zh.render(meta, units), encoding="utf-8")
    # 存疑汇总进审校记录
    rv = path.with_name(f"{a.wid}.review.md")
    doubts = []
    for mf in sorted(d.glob("*.meta.json"), key=lambda p: int(p.name.split("-")[0])):
        try:
            for x in json.loads(mf.read_text(encoding="utf-8")).get("doubts", []):
                doubts.append(f"- @{x.get('unit')}：{x.get('note')}")
        except json.JSONDecodeError:
            pass
    if not rv.exists():
        rv.write_text(f"# 审校记录：{meta.get('author_zh','')}《{meta.get('title_zh','')}》（{a.wid}）\n\n",
                      encoding="utf-8")
    if doubts and a.doubts:
        with open(rv, "a", encoding="utf-8") as f:
            f.write("## 翻译时的存疑\n" + "\n".join(doubts) + "\n\n")
    print(path)


def cmd_review_prompts(a):
    r = man(a.wid)
    lo, hi = map(int, a.range.split("-"))
    path = zh_path(r["period"], r["author_slug"], a.wid)
    meta, units = zh.load(path)
    tpl = (ROOT / "tools/prompts/review.md").read_text(encoding="utf-8")
    # 按对齐单元切成约 a.words 词的审校段
    src = parse_greek.load(a.wid).units
    out, cur, w = [], None, 0
    for s, e, _ in units:
        if e < lo or s > hi:
            continue
        if cur is None:
            cur = [s, e]
        cur[1] = e
        w += sum(u.words for u in src[s - 1:e])
        if w >= a.words:
            out.append(tuple(cur))
            cur, w = None, 0
    if cur:
        if out and w < a.words * 0.3:
            out[-1] = (out[-1][0], cur[1])
        else:
            out.append(tuple(cur))
    res = []
    for s, e in out:
        res.append({"wid": a.wid, "start": s, "end": e, "prompt": fill(
            tpl, ROOT=ROOT, AUTHOR=meta.get("author_zh", r["author_en"]),
            TITLE=meta.get("title_zh", r["work_en"]), WID=a.wid, START=s, END=e, FILE=path,
            REVIEW=path.with_name(f"{a.wid}.review.md"))})
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prompts"); p.add_argument("wid"); p.add_argument("range")
    p.add_argument("--words", type=int, default=2000)
    p = sub.add_parser("names"); p.add_argument("wid")
    p = sub.add_parser("assemble"); p.add_argument("wid")
    p.add_argument("--title-zh"); p.add_argument("--author-zh")
    p.add_argument("--status", default="draft")
    p.add_argument("--no-doubts", dest="doubts", action="store_false")
    p = sub.add_parser("review-prompts"); p.add_argument("wid"); p.add_argument("range")
    p.add_argument("--words", type=int, default=4000)
    a = ap.parse_args()
    {"prompts": cmd_prompts, "names": cmd_names, "assemble": cmd_assemble,
     "review-prompts": cmd_review_prompts}[a.cmd](a)


if __name__ == "__main__":
    main()
