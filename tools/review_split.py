"""把一部作品按审校段切成独立文件，供并行审校；审完再合并回去。

  python3 tools/review_split.py split <wid> [--words 4000]   生成 .work/<wid>/rv/*.zh.md 和 .work/rv-<wid>-*.md，列表写入 .work/rvqueue-<wid>.txt
  python3 tools/review_split.py merge <wid>                   把各段改动和审校记录并回 texts/
"""
import argparse, glob, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zh
from common import read_csv, MANIFEST, zh_path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"


def target(wid):
    r = next(r for r in read_csv(MANIFEST) if r["eul_wid"] == wid)
    return zh_path(r["period"], r["author_slug"], wid)


def split(wid, words, frm=1):
    p = target(wid)
    meta, units = zh.load(p)
    out = subprocess.run([sys.executable, str(ROOT / "tools/batch.py"), "review-prompts", wid,
                          f"{frm}-{units[-1][1]}", "--words", str(words)], capture_output=True, text=True, check=True).stdout
    jobs = json.loads(out[out.index("["):])
    rv = WORK / wid / "rv"
    rv.mkdir(parents=True, exist_ok=True)
    full, rvm = str(p), str(p.with_suffix("").with_suffix(".review.md"))
    files = []
    for j in jobs:
        s, e = j["start"], j["end"]
        sl = [u for u in units if u[0] >= s and u[1] <= e]
        assert sl[0][0] == s and sl[-1][1] == e
        seg = rv / f"{s}-{e}.zh.md"
        seg.write_text("".join(f"### @{a}-{b}\n\n{t.strip()}\n\n" for a, b, t in sl), encoding="utf-8")
        pr = j["prompt"].replace(f"python3 {ROOT}/tools/check.py {full}",
                                 f"python3 {ROOT}/tools/check_segment.py {wid} {s}-{e} {seg}")
        pr = pr.replace(full, str(seg)).replace(rvm, str(rv / f"{s}-{e}.review.md"))
        pr = pr.replace("（追加，不要覆盖已有内容）", "（新建此文件）")
        f = WORK / f"rv-{wid}-{s}-{e}.md"
        f.write_text(pr, encoding="utf-8")
        files.append(str(f))
    (WORK / f"rvqueue-{wid}.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
    print(f"{len(files)} 个审校段（见 .work/rvqueue-{wid}.txt）")


def key(f):
    return int(Path(f).name.split("-")[0])


def merge(wid):
    p = target(wid)
    meta, units = zh.load(p)
    rv = WORK / wid / "rv"
    new = []
    for f in sorted(glob.glob(str(rv / "*.zh.md")), key=key):
        new += zh.parse(Path(f).read_text(encoding="utf-8"))[1]
    # 用 split --from 只审了后半部分时，前面已审校的单元照旧保留
    new = [u for u in units if u[1] < new[0][0]] + new
    prev = 0
    for a, b, _ in new:
        assert a == prev + 1, (a, prev)
        prev = b
    assert prev == units[-1][1]
    p.write_text(zh.render(meta, new), encoding="utf-8")
    R = p.with_suffix("").with_suffix(".review.md")
    txt = R.read_text(encoding="utf-8") if R.exists() else ""
    for f in sorted(glob.glob(str(rv / "*.review.md")), key=key):
        txt += "\n" + Path(f).read_text(encoding="utf-8").strip() + "\n"
    R.write_text(txt, encoding="utf-8")
    print(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["split", "merge"])
    ap.add_argument("wid")
    ap.add_argument("--words", type=int, default=4000)
    ap.add_argument("--from", dest="frm", type=int, default=1, help="只切出从这个单元起的审校段（之前的已审校）")
    a = ap.parse_args()
    split(a.wid, a.words, a.frm) if a.cmd == "split" else merge(a.wid)


if __name__ == "__main__":
    main()
