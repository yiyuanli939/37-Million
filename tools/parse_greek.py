#!/usr/bin/env python3
"""解析 Eulogikon 的 .grc.md 原文文件。

每个 `### <标签>` 是一个单元（passage），按出现顺序从 1 起编号。
  python3 tools/parse_greek.py <eul_wid> [--units 起-止] [--json]
"""
import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".source" / "eulogikon"

GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
MARKER = re.compile(r"\[(para|bis|so|et|abrasum|spk_[^\]]*|ln_[^\]]*)\]")
KNOWN = {"para", "bis", "so", "et", "abrasum"}


@dataclass
class Unit:
    seq: int
    label: str
    text: str
    words: int = 0
    markers: list = field(default_factory=list)


@dataclass
class Work:
    wid: str
    meta: dict
    units: list

    @property
    def words(self):
        return sum(u.words for u in self.units)


def count_words(text):
    return sum(1 for tok in text.split() if GREEK.search(tok))


def parse_text(raw, wid=""):
    meta = {}
    lines = raw.split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            if ":" in lines[i]:
                k, v = lines[i].split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
            i += 1
        i += 1
    try:
        start = next(j for j in range(i, len(lines)) if lines[j].strip() == "## Text") + 1
    except StopIteration:
        return Work(wid or meta.get("eul_wid", ""), meta, [])
    end = len(lines)
    for j in range(len(lines) - 1, start - 1, -1):
        if lines[j].startswith("## License and provenance"):
            end = j
            break
    units, label, buf = [], None, []

    def flush():
        if label is not None:
            text = "\n".join(buf).strip()
            u = Unit(len(units) + 1, label, text, count_words(text),
                     [m.group(1) for m in MARKER.finditer(text)])
            units.append(u)

    for line in lines[start:end]:
        if line.startswith("### "):
            flush()
            label, buf = line[4:].strip(), []
        elif label is not None:
            buf.append(line)
    flush()
    return Work(wid or meta.get("eul_wid", ""), meta, units)


_paths = None


def path_for(wid):
    global _paths
    if _paths is None:
        _paths = {r["eul_wid"]: SRC / r["grc_md"].lstrip("/")
                  for r in csv.DictReader(open(SRC / "manifest.csv", encoding="utf-8"))}
    return _paths[wid]


def load(wid):
    return parse_text(path_for(wid).read_text(encoding="utf-8"), wid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wid")
    ap.add_argument("--units", help="起-止（闭区间）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    w = load(a.wid)
    lo, hi = 1, len(w.units)
    if a.units:
        p = a.units.split("-")
        lo, hi = int(p[0]), int(p[-1])
    sel = w.units[lo - 1:hi]
    if a.json:
        json.dump([u.__dict__ for u in sel], sys.stdout, ensure_ascii=False, indent=1)
    else:
        print(f"# {a.wid} {w.meta.get('author','')} · {w.meta.get('title','')} "
              f"（{len(w.units)} 单元，{w.words} 词）")
        for u in sel:
            print(f"\n@{u.seq} [{u.label}]\n{u.text}")


if __name__ == "__main__":
    main()
