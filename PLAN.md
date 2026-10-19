# 执行方案

## 0. 已确定的决定

| 事项 | 决定 |
|---|---|
| 底本 | Eulogikon 开放语料（希腊原文为公有领域，项目自身元数据为 CC0） |
| 版式 | 希腊文—中文对照：每页左栏希腊文、右栏中文，按对齐单元逐段对照 |
| 排序 | 先按时期，时期内按学派或体裁 |
| 专名 | 以通行译名为主；没有通行译名的，按统一音译规则补充 |
| 发布 | 文字和脚本放 GitHub；PDF 放 GitHub Releases；对齐数据（Parquet）和 PDF 同步到 Hugging Face |
| 质量标注 | AI 翻译 + 独立 AI 审校；人工校订另行标注 |

**待用户决定：**译文许可证。Hugging Face 仓库目前是 Apache-2.0（软件许可证，不太适合文本），建议改为 CC0 或 CC BY 4.0。阶段 0 结束时询问用户。

## 1. 数据源（已实地查验）

- 仓库：`https://github.com/eulogikon/ancient-greek-texts`
- 查验时的提交：`646609143098878ccc4a5937917cb71f1808476a`。阶段 0 把它写进 `source.lock`，整个项目固定用这个提交。
- `manifest.json` 中的计数：1358 位作者，4060 部作品，**44,071,889 个希腊词**。
- 各时期作品数：古风 209，古典 1054，希腊化 912，罗马 1076，古代晚期 766，拜占庭 39，不详 4。

### 只取文字的拉取方法

整个仓库约 1.7 万个文件，含 PDF。只拉需要的部分：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none --no-checkout \
  https://github.com/eulogikon/ancient-greek-texts .source/eulogikon
cd .source/eulogikon
git sparse-checkout init --no-cone
printf '/manifest.csv\n/manifest.json\n/grc/<所需文件>.grc.md\n' > .git/info/sparse-checkout
git checkout
```

- 全部 `grc/*.md` 约 542MB。每次会话只检出本批次要用的文件即可。
- `.source/` 加进 `.gitignore`。

### 清单字段

`manifest.csv` 的列：

```
eul_aid, eul_wid, author_display_string, author_english, author_greek,
work_display_string, work_english, work_greek, period, dialect, domain,
format, affiliation, passages, grc_pdf, grc_md, grc_txt
```

- `period`：Archaic / Classical / Hellenistic / Roman / Late Antique / Byzantine / Uncertain。
- `affiliation`：学派。约 3100 部作品为空。有值的包括 Platonist、Neoplatonist、Aristotelian、Christian、Stoic、Pythagorean、Sophist、Peripatetic、Eclectic、Presocratic、Jewish、Epicurean、Cynic、Hermetic 等。
- `manifest.json` 的 `authors[]` 里有作者层面的 `period`、`affiliation`、`domain`，排序时用作者层面的值，避免同一作者的作品被拆到不同组。
- **清单里没有逐部作品的词数**，要自己从文本计算：统计含希腊字母的空白分隔词。

### 原文文件格式

文件路径：`grc/<work_display_string>-<eul_wid>.grc.md`

```
---
title: Theogony
title_greek: Θεογονία
author: Hesiod
eul_wid: aau-ag
period: Archaic
dialect: Epic (Homeric)
domain: Epic
format: Verse
license: "https://creativecommons.org/publicdomain/mark/1.0/"
---
# Theogony
...
## Text

### 1
Μουσάων Ἑλικωνιάδων ἀρχώμεθ’ ἀείδειν,

### 2
αἵ θ’ Ἑλικῶνος ἔχουσιν ὄρος μέγα τε ζάθεόν τε,
```

- 正文从 `## Text` 开始，每个 `### <标签>` 是一个段落单元（passage）。诗歌通常一行一个单元，散文是一节或一个页码段。
- **标签格式五花八门**：`1`、`book 1.2`、`1.2.3`、`Metaph.980a.(t1)`、`8 1 (t1)`、`α 12` 等。所以本项目一律用**序号**（第几个单元，从 1 起）定位，原标签只用于显示。
- 正文中的内嵌标记要识别：`[para]`（新段落开始，约 8500 处）、`[bis]`、`[spk_*]`（戏剧说话人，如 `[spk_chorus]`）、`[ln_*]`、`[so]`、`[et]`、`[abrasum]`（残损）。
  - 排版时 `[para]` 转为分段，`[spk_*]` 转为说话人标签，其余按含义处理。
  - 不认识的标记，记录下来，原样保留。

## 2. 仓库结构

```
CLAUDE.md            每次会话自动读取的工作说明
PLAN.md              本方案
STYLE.md             翻译规范
PROGRESS.md          进度与断点记录（每次会话结束前更新）
source.lock          Eulogikon 固定提交号
manifest.csv         全部作品：排序号、eul_wid、作者、标题、时期、组、词数、单元数、所属卷
volumes.csv          分卷表：卷号、标题、包含的作品或作品片段（序号范围）、词数
glossary/
  names.tsv          专名：希腊文 | 中文 | 类别（人/地/神/族）| 来源（通行/音译）| 首见作品
  terms.tsv          术语：希腊文 | 中文 | 说明
  transliteration.md 音译规则表
texts/<时期>/<作者>/<eul_wid>.zh.md     中文译文
texts/<时期>/<作者>/<eul_wid>.review.md 审校记录
tools/               脚本（拉取、建清单、领批次、检查、排版、导出）
build/               Typst 排版模板
.github/workflows/   自动排版发布、同步 Hugging Face
```

为了控制仓库体积，**仓库里不存希腊原文**，排版时按 `source.lock` 现取。全部完成后，中文文字约几百 MB。

## 3. 译文文件格式

`texts/.../<eul_wid>.zh.md`：

```
---
eul_wid: aau-ag
title_zh: 神谱
author_zh: 赫西俄德
source_commit: 6466091
status: reviewed        # draft / reviewed / human-reviewed
translator: Claude (AI)
reviewer: Claude (AI, 独立审校)
---

### @1-4
让我们从赫利孔山的缪斯开始歌唱……

### @5-10
……
```

- 每个对齐单元的标题是 `### @起-止`，起止是原文单元的序号（闭区间）。单个单元写 `### @7`。
- 各单元必须**按顺序、无缝、无重叠**地覆盖 1 到 N，用脚本校验。
- 诗歌可以把几行合成一个对齐单元，以便按完整句子翻译；散文通常一个单元对一个单元。长单元不拆。

## 4. 排序与分卷

### 排序

依次按以下顺序排：

1. 时期：古风 → 古典 → 希腊化 → 罗马 → 古代晚期 → 拜占庭 → 不详。
2. 时期内的组：有学派的按学派归组，没有的按体裁归组。组的先后顺序：
   - 史诗、诗歌、戏剧、喜剧、小说
   - 历史、传记、地理
   - 哲学各学派：米利都、前苏格拉底、爱利亚、赫拉克利特、毕达哥拉斯、原子论、德谟克利特、智者、苏格拉底派、麦加拉、犬儒、柏拉图派、学园怀疑派、亚里士多德派、逍遥派、斯多亚、伊壁鸠鲁、皮浪派、折中派、新柏拉图派、赫尔墨斯、诺斯替、犹太、基督教
   - 无学派的哲学
   - 演说、修辞、法律、神学
   - 科学、数学、医学
   - 语法、辞书、古注
3. 组内按作者排，同一作者的作品排在一起。清单没有生卒年，暂按英文名排序；之后可以人工微调，只调 `manifest.csv` 里的排序号即可。

### 分卷

- 每卷约 **7.5 万希腊词**（中文约 19 万字，对照排版约 500 页），全部约 590 卷。
- 进入新的时期一定另起一卷。换组时，如果当前卷已达目标量的 40%，也另起一卷。
- 超过 11 万词的单部作品，按原文单元边界拆成几卷，尽量在卷、书、章的边界处拆。
- 卷号 `V0001` 起编。卷标题在该卷译完后由会话生成，例如"古风时期·史诗（一）：赫西俄德"。

## 5. 分阶段推进

### 阶段 0：搭建（1–2 次会话）

1. 写 `tools/fetch_source.py`：按上面的方法拉取，只检出需要的文件。
2. 写 `tools/parse_greek.py`：解析原文文件（单元、标签、标记、词数）。
3. 写 `tools/build_manifest.py`：计算词数，生成 `manifest.csv` 和 `volumes.csv`。核对总词数与 44,071,889 是否基本一致（容许统计口径带来的小差异）。
4. 写 `tools/next_batch.py`：按排序找出下一批未完成的作品或片段，默认约 2 万词。
5. 写 `tools/check.py`，检查以下几项：
   - 对齐覆盖：无缝、无重叠、无遗漏。
   - 中文与原文的长度比例异常。
   - 译文里残留的希腊文。
   - 专名用法与译名表不一致。
   - 空单元。
6. 建 `glossary/transliteration.md`：
   - 以罗念生、王焕生等前辈译者通行的古希腊语音译惯例为基础，整理成一张对照表，包括常见词尾的处理（-ος、-ης、-ων 等）和希腊字母组合与汉字的对应。
7. 预填 `glossary/names.tsv`：
   - 先收录约 500 个最常见的神名、人名、地名，采用通行译名，例如宙斯、雅典娜、荷马、柏拉图、雅典、斯巴达。
8. 写 Typst 模板和 `tools/build_volume.py`（见第 7 节），以及两个 GitHub Actions 工作流（见第 8 节）。
9. **停下来请用户确认三件事**：
   - 音译规则表和预填译名表。
   - 许可证。
   - 分卷表概览：前 20 卷的内容，以及全部卷数。

### 阶段 1：试样（1–2 次会话）

1. 试样作品：**赫西俄德全部作品**，即《神谱》1023 行、《工作与时日》827 行、《赫拉克勒斯之盾》480 行，以及残篇和证言，约 1.7 万词。
   - 选它的理由：属古风时期；是诗体，最能检验"雅"；已有中译本可供用户对比质量。按规则，不得参照这些中译本的文字。
2. 按第 6 节的流程完整走一遍，包括翻译、独立审校、检查、更新译名表。
3. 排出试样 PDF，作为预发布版本挂到 Releases。
4. 在 `PROGRESS.md` 里记录实测数据：
   - 处理了多少词，用了几次会话。
   - 大致消耗了多少额度，比如是否碰到 5 小时限额。
   - 按这个速度推算全部完成需要的时间。
5. **停下来请用户审阅试样**，按反馈修订 `STYLE.md`，再进入阶段 2。

### 阶段 2：量产

- 每次会话处理一批，按第 6 节的流程。
- 可以由用户手动开会话，也可以设定时任务。每次运行的提示词就一句："按 CLAUDE.md 继续下一批。"
- 每完成一卷，执行一次整卷统稿：统一专名、文体和注释格式；生成卷标题、凡例和专名索引；然后打标签 `v<卷号>`，触发发布。

### 阶段 3：发布

由 GitHub Actions 自动完成，见第 8 节。

## 6. 单批次工作流

1. `git pull`，运行 `tools/next_batch.py` 领取下一批，用 `tools/fetch_source.py` 检出这批的原文。
2. **切段**：把这批切成约 2000 词的翻译段，切在对齐单元边界上，尽量切在 `[para]` 处。
3. **并行翻译**：每段交给一个子任务。子任务拿到的材料是：
   - `STYLE.md` 全文。
   - 译名表中与本段相关的条目（按本段出现的希腊专名检索）。
   - 本段原文（附序号）。
   - 前后各约 300 词的原文，以及前一段已完成的译文，用来衔接。

   子任务的产出：
   - 本段译文，用 `### @起-止` 格式。
   - 本段新出现的专名和术语，附建议译名。
   - 存疑之处的清单。
4. **合并译名**：新专名先与译名表查重。查到通行译名就采用；查不到就按音译规则生成。登记后，回填各段译文。
5. **独立审校**：另起子任务。它只拿到原文、译文、`STYLE.md` 和译名表，看不到翻译时的上下文。逐单元检查：
   - 漏译、增译、误译。
   - 专名和术语是否统一。
   - 文体是否合体裁。
   - 标点。

   直接修改译文，并把每处改动和理由写进 `.review.md`。改不了或拿不准的地方用〔 〕标出并说明。
6. 运行 `tools/check.py`，全部通过才能提交。
7. 提交，提交信息格式：`译：<作者> <作品>（@起-止）`。然后推送，并更新 `PROGRESS.md`。

## 7. 排版规格

- **工具**：Typst（`pip install typst`，已验证可装）。字体：中文用思源宋体（Noto Serif CJK SC），希腊文用 GFS Porson 或 GFS Didot。
  - 在 CI 中安装：`apt-get install fonts-noto-cjk fonts-gfs-porson fonts-gfs-didot`。
- **开本**：B5（176×250mm）。
- **版式**：每个对齐单元一行两栏，左希腊文、右中文，行可以跨页断开。原文单元标签放在页边，诗行每 5 行标一次行号。
- **每卷的组成**：
  - 卷首：封面；扉页（卷号、标题、所含作品）；凡例；底本说明（Eulogikon 提交号、许可）；AI 翻译与审校声明。
  - 目录。
  - 正文。
  - 卷末：注释；专名索引（中文—希腊文）。
- **体积**：必须做字体子集化（Typst 默认会做）。实测纯中文 400 页约 2.2MB，对照卷预计每卷 3–5MB。
- **导出**：每卷除了 PDF，再导出一份对齐数据（JSONL 或 Parquet），字段为 `eul_wid, unit, labels, grc, zh, status`。

## 8. 发布与同步

- `.github/workflows/release.yml`：推送 `v*` 标签时触发。安装字体和 Typst，拉取原文，排版该卷 PDF 并生成对齐数据，然后发布到 Releases。每个文件小于 2GiB，每个发布最多 1000 个文件，总量和流量不限。
- `.github/workflows/sync-hf.yml`：发布后，把 PDF 和对齐数据上传到 Hugging Face 数据集 `TimaeusWorld/37-Million-Words`。
  - 用仓库 Secret `HF_TOKEN`，由用户自己在 GitHub 设置，只对该数据集有写权限。
  - 云端会话本身连不上 huggingface.co，所以同步只能走 Actions。
- 同时更新 Hugging Face 的数据集说明：来源、许可、AI 翻译和审校的说明、各卷进度表。

## 9. 额度与节奏

- 云端会话和定时任务消耗的是用户 Max 订阅的额度：5 小时会话限额和每周限额，与用户平时用 Claude 共用。
- 批次大小以阶段 1 的实测为准，并给用户自己的日常使用留出余量。
- 想加快进度，可以另外用 Max 每月附送的 API 额度，通过批处理 API 跑翻译，但这需要另写脚本，阶段 2 稳定后再考虑。
- 粗略估算：每次会话处理 2 万词，全部需要约 2200 次会话。阶段 1 结束后，按实测数据重新估算。
