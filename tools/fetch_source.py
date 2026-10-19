#!/usr/bin/env python3
"""拉取 Eulogikon 原文（固定提交见 source.lock），只检出需要的文件。

用法：
  tools/fetch_source.py                 # 只检出清单
  tools/fetch_source.py aau-ag aau-ah   # 再检出这些作品的 .grc.md
  tools/fetch_source.py --all           # 检出全部 grc/*.grc.md（约 540MB）
"""
import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".source" / "eulogikon"
REPO = "https://github.com/eulogikon/ancient-greek-texts"


def lock():
    for line in (ROOT / "source.lock").read_text().splitlines():
        if line.startswith("commit="):
            return line.split("=", 1)[1].strip()
    sys.exit("source.lock 中没有 commit=")


def git(*args, **kw):
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
    return subprocess.run(["git", "-C", str(SRC), *args], check=True, env=env, **kw)


def ensure_clone(commit):
    if not (SRC / ".git").exists():
        SRC.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO, str(SRC)],
                       check=True, env=dict(os.environ, GIT_LFS_SKIP_SMUDGE="1"))
    have = subprocess.run(["git", "-C", str(SRC), "cat-file", "-t", commit],
                          capture_output=True, text=True).stdout.strip()
    if have != "commit":
        git("fetch", "origin", commit)


def grc_paths(wids, all_):
    rows = list(csv.DictReader(open(SRC / "manifest.csv", encoding="utf-8")))
    if all_:
        return [r["grc_md"].lstrip("/") for r in rows if r["grc_md"]]
    by = {r["eul_wid"]: r for r in rows}
    out = []
    for w in wids:
        if w not in by:
            sys.exit(f"清单中没有 {w}")
        out.append(by[w]["grc_md"].lstrip("/"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wids", nargs="*")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    commit = lock()
    ensure_clone(commit)
    git("sparse-checkout", "init", "--no-cone")
    pats = ["/manifest.csv", "/manifest.json"]
    sp = SRC / ".git" / "info" / "sparse-checkout"
    old = set(sp.read_text().split()) if sp.exists() else set()
    git("checkout", "-q", "--detach", commit)
    if a.wids or a.all:
        pats += ["/" + p for p in grc_paths(a.wids, a.all)]
    sp.write_text("\n".join(sorted(old | set(pats))) + "\n")
    git("checkout", "-q", "--detach", commit)
    git("sparse-checkout", "reapply")


if __name__ == "__main__":
    main()
