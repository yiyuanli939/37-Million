"""按希腊文单元有条件地统一修饰语译法。

用法：python3 tools/unify_epithets.py <wid> <zh.md>
规则写在 RULES 里：(希腊文须含的正则, 希腊文须不含的正则, 旧译, 新译)。
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import parse_greek, zh

RULES = [
    (r"δῖ[οαε]|δί[οε]", r"θεοειδ|ἀντίθε|θεοείκελ|ἰσόθε", "容貌如神的", "神样的"),
    (r"ἀγήνορ", None, "高傲的心灵", "傲慢的心灵"),
    (r"τρίπο", None, "三脚鼎", "三足鼎"),
]

def main(wid, path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    units = {u.seq: u.text for u in parse_greek.load(wid).units}
    out, counts = [], [0] * len(RULES)
    for block in re.split(r"(?m)^(?=### @)", text):
        m = re.match(r"### @(\d+)-(\d+)", block)
        if m:
            gr = " ".join(units.get(i, "") for i in range(int(m[1]), int(m[2]) + 1))
            for k, (need, avoid, old, new) in enumerate(RULES):
                if old in block and re.search(need, gr) and not (avoid and re.search(avoid, gr)):
                    counts[k] += block.count(old)
                    block = block.replace(old, new)
        out.append(block)
    path.write_text("".join(out), encoding="utf-8")
    for (need, avoid, old, new), c in zip(RULES, counts):
        print(f"{old}→{new}: {c}")

if __name__ == "__main__":
    main(*sys.argv[1:])
