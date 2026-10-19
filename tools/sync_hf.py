#!/usr/bin/env python3
"""把发布文件上传到 Hugging Face 数据集，并刷新数据集说明（只在 GitHub Actions 中运行）。

  tools/sync_hf.py <下载目录> <releases.json>
环境变量：HF_TOKEN，HF_REPO（默认 TimaeusWorld/37-Million-Words）
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import MANIFEST, ROOT, VOLUMES, read_csv
import build_volume

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import CommitOperationAdd, HfApi

REPO = os.environ.get("HF_REPO", "TimaeusWorld/37-Million-Words")
GH = "https://github.com/yiyuanli939/37-Million"


def card(released):
    vols = read_csv(VOLUMES)
    titles = build_volume.volume_titles()
    total = sum(int(v["words"]) for v in vols)
    done = [v for v in vols if v["volume"] in released]
    dw = sum(int(v["words"]) for v in done)
    rows = "\n".join(f"| {v['volume']} | {titles[v['volume']]} | {int(v['words']):,} | "
                     f"[PDF](volumes/{v['volume']}.pdf) · [Parquet](data/{v['volume']}.parquet) |"
                     for v in done) or "| — | 尚无正式发布的卷 | | |"
    return f"""---
license: cc-by-4.0
language:
- grc
- zh
task_categories:
- translation
pretty_name: 古希腊文献希中对照全译（37 Million Words）
tags:
- ancient-greek
- parallel-corpus
- machine-translation
configs:
- config_name: default
  data_files: data/*.parquet
---

# 古希腊文献希中对照全译

把 [Eulogikon](https://github.com/eulogikon/ancient-greek-texts) 开放语料中的全部古希腊文献（4060 部作品，约 4400 万希腊词）译成中文，分卷排成希腊文—中文对照 PDF。

- **来源**：希腊原文取自 Eulogikon（公有领域，Public Domain Mark 1.0；元数据 CC0），固定提交见 [source.lock]({GH}/blob/main/source.lock)。
- **翻译与审校**：译文由 AI（Claude）直接从希腊原文译出，再由独立的 AI 审校流程逐单元复核，**未经人工校订**（经人工校订的部分会单独标注）。未参照任何受版权保护的现代中译本。
- **许可**：中文译文以 CC BY 4.0 发布；希腊原文为公有领域。
- **工作仓库**：{GH}（译文文字、译名表、脚本；PDF 也发布在其 Releases）。

## 数据格式

`data/<卷号>.parquet` 每行一个对齐单元，字段：`eul_wid`（作品编号）、`unit`（原文单元序号范围）、`labels`（原文单元标签）、`grc`（希腊原文）、`zh`（中文译文）、`status`（draft / reviewed / human-reviewed）、`volume`（卷号）。

`volumes/<卷号>.pdf` 是对照排版的成书。

## 进度

已发布 {len(done)} / {len(vols)} 卷，{dw:,} / {total:,} 希腊词（{dw / total:.2%}）。

| 卷号 | 标题 | 希腊词数 | 文件 |
|---|---|---|---|
{rows}
"""


def main():
    dl, rel = Path(sys.argv[1]), json.load(open(sys.argv[2]))
    released = {"V" + r["tagName"][1:] for r in rel if not r["isPrerelease"] and r["tagName"].startswith("v")}
    api = HfApi(token=os.environ["HF_TOKEN"])
    ops = []
    for pdf in sorted(dl.glob("*.pdf")):
        ops.append(CommitOperationAdd(f"volumes/{pdf.name}", str(pdf)))
    for jl in sorted(dl.glob("*.jsonl")):
        rows = [json.loads(l) for l in jl.read_text(encoding="utf-8").splitlines() if l.strip()]
        out = jl.with_suffix(".parquet")
        pq.write_table(pa.Table.from_pylist(rows), out)
        ops.append(CommitOperationAdd(f"data/{out.name}", str(out)))
    if os.environ.get("TAG", "").startswith("sample-"):
        # 试样只放到 samples/，不进 data/ 和 volumes/
        ops = [CommitOperationAdd("samples/" + o.path_in_repo.split("/", 1)[1], o.path_or_fileobj) for o in ops]
    ops.append(CommitOperationAdd("README.md", card(released).encode("utf-8")))
    tag = os.environ.get("TAG") or "说明"
    api.create_commit(REPO, repo_type="dataset", operations=ops, commit_message=f"同步 {tag}")
    print(f"已同步到 https://huggingface.co/datasets/{REPO}：{[o.path_in_repo for o in ops]}")


if __name__ == "__main__":
    main()
