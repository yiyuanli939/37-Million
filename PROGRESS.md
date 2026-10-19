# 进度记录

每次会话结束前在最上面追加一条：日期、阶段、完成了什么、断点在哪、遇到的问题、给下一次会话的提示。

## 当前状态

- 阶段：**阶段 1（试样：赫西俄德）进行中**
- 已完成卷数：0 / 712
- 已翻译希腊词数：0 / 44,071,889

## 记录

### 2026-10-19 阶段 0 完成
- 用户指示此后不再逐项确认、全部自行完成，目标是先完成全部翻译的 1/10（约 440 万希腊词，按排序从 V0001 起）。阶段 0 原定请用户确认的三件事，按默认处理：
  - **许可证**：译文用 CC BY 4.0（Hugging Face 数据集说明同步改为 cc-by-4.0）。
  - **音译规则和译名表**：`glossary/transliteration.md` 按罗念生、王焕生的通行惯例整理；`names.tsv` 预填常见专名。
  - **分卷表**：按方案生成，共 **712 卷**（多于原估的 590 卷，因为时期和组的换卷规则会留下一些不满的卷），中位数约 6.6 万词。
- 总词数实测 44,027,362，比清单少 0.10%（统计口径差异）。
- Hugging Face 的 Secret 实际名为 `HUGGINGFACE_TOKEN`（不是方案里写的 `HF_TOKEN`），工作流已按此写。
- 清单 CSV 的 `format` 列与原文文件头不一致（如《神谱》在 CSV 里是 Collection，文件头是 Verse），`manifest.csv` 以文件头为准。
- 原文中的 `## ` 行可能是正文内容，解析时只以最后一个 `## License and provenance` 为正文终点。
- 已写脚本：`fetch_source.py`、`parse_greek.py`、`build_manifest.py`、`next_batch.py`、`segments.py`、`check.py`、`check_segment.py`、`batch.py`（生成子任务说明、合并译名、组装译文）、`build_volume.py`、`sync_hf.py`；子任务说明在 `tools/prompts/`。
- 工作流：`release.yml`（推送 `v0001` 这样的标签即排版发布；也可手动运行出试样预发布）、`sync-hf.yml`（发布成功后同步 Hugging Face）。`workflow_run` 和手动触发只认默认分支上的工作流文件，所以要合并到 main 后才生效。
- 下一步：阶段 1，试译赫西俄德全部作品。

### 2026-10-19 方案建立
- 写入 `CLAUDE.md`、`PLAN.md`、`STYLE.md`、`PROGRESS.md`。
- 已查验 Eulogikon 仓库结构和清单格式，提交号为 `646609143098878ccc4a5937917cb71f1808476a`，细节见 `PLAN.md` 第 1 节。
- 下一步：按 `PLAN.md` 第 5 节执行阶段 0。
