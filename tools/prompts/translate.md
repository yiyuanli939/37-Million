# 翻译子任务说明

你负责把一段古希腊原文译成中文。仓库根目录：`{ROOT}`。

## 先读

1. `{ROOT}/STYLE.md`（翻译规范，必须遵守）。
2. 译名表：`{ROOT}/glossary/names.tsv`、`{ROOT}/glossary/terms.tsv`。用 `grep` 按本段出现的专名检索，不必通读。没有的专名按 `{ROOT}/glossary/transliteration.md` 音译。

## 本段

- 作品：{AUTHOR} 《{TITLE}》（eul_wid `{WID}`，体裁 {DOMAIN}，{FORMAT}）
- 范围：原文单元 @{START}–@{END}（约 {WORDS} 词）
- 读原文：`python3 {ROOT}/tools/parse_greek.py {WID} --units {START}-{END}`
  （每个单元前的 `@序号 [标签]` 是定位用的，不是原文。）
- 上文衔接：`python3 {ROOT}/tools/parse_greek.py {WID} --units {CTX_BEFORE}`；下文：`--units {CTX_AFTER}`。只用来理解，不译。
{PREV_NOTE}

## 要求

- 直接从希腊原文翻译。**不得抄录、回忆或参照任何现代中译本的文字。**可以借助你对公有领域旧英译本的理解来把握原意，但译文必须是你对希腊原文的直接翻译。
- 不改动希腊原文。原文中的整理者符号（[ ]、〈 〉、† 等）说明有疑问或补字，按 STYLE.md 处理。
- 原文的内嵌标记：`[para]` 只表示分段，不译；`[spk_X]` 是说话人，译文对应处写成"X："的中文译名；`[ln_N]` 是行号，不译；`[abrasum]` 译作"〔残〕"。
- 诗歌：可把几行合为一个对齐单元，使每个单元是完整的句子；每个原文行大致对应一行译文（中文行数可略有出入）。散文：一个单元对一个单元。长单元不拆。
- 全部单元 @{START} 到 @{END} 必须按顺序、无缝、无重叠地覆盖。
- 必要的简注（人物、地点、典故、度量）写在该单元正文之后，单独一行，以 `> ` 开头，例如 `> 赫利孔山：玻俄提亚的山，缪斯的圣地。`。注释要少而精。
- 术语首次出现时括注希腊文，如：德性（ἀρετή）。除此之外译文正文里不要出现希腊字母。

## 产出（写文件，不要在回复里贴译文）

1. 译文写入 `{OUT}`，格式严格如下（不要 YAML 头）：

```
### @{START}-{START_PLUS}
译文……

### @…
译文……
```

单个单元写 `### @7`，多个写 `### @7-9`。

2. 写入 `{OUT_META}`（JSON）：
```json
{"new_names": [{"grc": "Ἑλικών", "zh": "赫利孔", "type": "地", "source": "通行"}],
 "new_terms": [{"grc": "…", "zh": "…", "note": "…"}],
 "doubts": [{"unit": 12, "note": "原文 … 有两种读法……"}]}
```
new_names 只列 names.tsv 里**没有**的专名（希腊文用主格）。

3. 写完后运行 `python3 {ROOT}/tools/check_segment.py {WID} {START}-{END} {OUT}` 自检，有错误就改到通过。

最后只回复一行：`完成 {WID} @{START}-{END}，N 个单元，新专名 X 个，存疑 Y 处`。
