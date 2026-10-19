"""读写中文译文文件 texts/.../<eul_wid>.zh.md。"""
import re

HEAD = re.compile(r"^### @(\d+)(?:-(\d+))?\s*$")


def parse(text):
    """返回 (meta, [(起, 止, 译文), ...])。"""
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.index("\n---", 4)
        for line in text[4:end].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.split("#")[0].strip()
        body = text[end + 4:]
    units, cur, buf = [], None, []
    for line in body.split("\n"):
        m = HEAD.match(line)
        if m:
            if cur:
                units.append((*cur, "\n".join(buf).strip()))
            a = int(m.group(1))
            cur, buf = (a, int(m.group(2) or a)), []
        elif cur:
            buf.append(line)
    if cur:
        units.append((*cur, "\n".join(buf).strip()))
    return meta, units


def load(path):
    return parse(path.read_text(encoding="utf-8"))


def covered(path):
    """已译到第几个单元（假定从 1 起连续）。文件不存在返回 0。"""
    if not path.exists():
        return 0
    _, units = load(path)
    return max((b for _, b, _ in units), default=0)


def render(meta, units):
    head = "---\n" + "".join(f"{k}: {v}\n" for k, v in meta.items()) + "---\n"
    parts = []
    for a, b, t in units:
        parts.append(f"### @{a}" + (f"-{b}" if b != a else "") + "\n" + t.strip() + "\n")
    return head + "\n" + "\n".join(parts)
