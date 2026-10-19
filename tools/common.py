"""各脚本共用的常量和读写函数。"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".source" / "eulogikon"

PERIODS = ["Archaic", "Classical", "Hellenistic", "Roman", "Late Antique", "Byzantine", "Uncertain"]
PERIOD_ZH = {"Archaic": "古风", "Classical": "古典", "Hellenistic": "希腊化", "Roman": "罗马",
             "Late Antique": "古代晚期", "Byzantine": "拜占庭", "Uncertain": "不详"}
PERIOD_DIR = {"Archaic": "1-archaic", "Classical": "2-classical", "Hellenistic": "3-hellenistic",
              "Roman": "4-roman", "Late Antique": "5-late-antique", "Byzantine": "6-byzantine",
              "Uncertain": "7-uncertain"}

# 组的先后顺序（PLAN.md 第 4 节）。学派用 affiliation，其余用 domain。
GROUPS = [
    ("Epic", "史诗"), ("Poetry", "诗歌"), ("Drama", "戏剧"), ("Comedy", "喜剧"), ("Fiction", "小说"),
    ("History", "历史"), ("Biography", "传记"), ("Geography", "地理"),
    ("Milesian", "米利都学派"), ("Presocratic", "前苏格拉底哲学"), ("Eleatic", "爱利亚学派"),
    ("Heraclitean", "赫拉克利特派"), ("Pythagorean", "毕达哥拉斯派"), ("Atomist", "原子论"),
    ("Democritean", "德谟克利特派"), ("Sophist", "智者"), ("Socratic", "苏格拉底派"),
    ("Megarian", "麦加拉派"), ("Cynic", "犬儒派"), ("Platonist", "柏拉图派"),
    ("Academic Skeptic", "学园怀疑派"), ("Aristotelian", "亚里士多德派"), ("Peripatetic", "逍遥派"),
    ("Stoic", "斯多亚派"), ("Epicurean", "伊壁鸠鲁派"), ("Pyrrhonian", "皮浪派"),
    ("Eclectic", "折中派"), ("Neoplatonist", "新柏拉图派"), ("Hermetic", "赫尔墨斯文献"),
    ("Gnostic", "诺斯替文献"), ("Jewish", "犹太文献"), ("Christian", "基督教文献"),
    ("Philosophy", "哲学"), ("Oratory", "演说"), ("Law", "法律"), ("Theology", "神学"),
    ("Science", "科学"), ("Mathematics", "数学"), ("Medicine", "医学"),
    ("Grammar", "语法"), ("Lexicography", "辞书"), ("Scholia", "古注"), ("", "其他"),
]
GROUP_ORDER = {k: i for i, (k, _) in enumerate(GROUPS)}
GROUP_ZH = dict(GROUPS)

MANIFEST = ROOT / "manifest.csv"
VOLUMES = ROOT / "volumes.csv"


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def parse_parts(s):
    """'aau-ag@1-1023;aau-ac@1-828' -> [('aau-ag', 1, 1023), ...]"""
    out = []
    for p in filter(None, s.split(";")):
        wid, rng = p.split("@")
        a, b = rng.split("-")
        out.append((wid, int(a), int(b)))
    return out


def zh_path(period, author_slug, wid):
    return ROOT / "texts" / PERIOD_DIR[period] / author_slug / f"{wid}.zh.md"
