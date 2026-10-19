// 希腊文—中文对照卷排版模板。数据由 tools/build_volume.py 生成的 JSON 提供：
//   typst compile --input data=<相对路径> build/volume.typ out.pdf
#let data = json(sys.inputs.at("data", default: "data.json"))

#let zh-font = ("Noto Serif CJK SC",)
#let grc-font = ("GFS Didot", "GFS Porson", "Noto Serif CJK SC")

#set document(title: data.volume + " " + data.title, author: "Claude (AI)")
#set page(
  width: 176mm, height: 250mm,
  margin: (inside: 18mm, outside: 14mm, top: 20mm, bottom: 18mm),
  header: context {
    let p = here().page()
    if p > 4 {
      set text(size: 7.5pt, fill: luma(90))
      if calc.even(p) [#data.volume　#data.title] else [#h(1fr) #data.series]
      v(-4pt); line(length: 100%, stroke: 0.3pt + luma(150))
    }
  },
  footer: context {
    let p = here().page()
    if p > 2 { set text(size: 8pt); align(center, counter(page).display()) }
  },
)
#set text(font: zh-font, size: 9.5pt, lang: "zh", region: "cn")
#set par(leading: 0.75em, justify: true)
#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  set text(size: 15pt, weight: "bold")
  block(above: 0pt, below: 1.2em, it.body)
}
#show heading.where(level: 2): it => {
  set text(size: 11.5pt, weight: "bold")
  block(above: 1.4em, below: 0.9em, it.body)
}

// 原文排版：处理内嵌标记已在脚本中转成 segments。
#let grc-run(segs) = {
  set text(font: grc-font, size: 8.7pt, lang: "el")
  set par(justify: false, leading: 0.6em, spacing: 0.6em, hanging-indent: 1.2em)
  for s in segs {
    if s.k == "t" { s.v }
    else if s.k == "br" { linebreak() }
    else if s.k == "vl" { parbreak() }
    else if s.k == "vn" { place(left, dx: -9mm, box(width: 7mm, align(right, text(size: 6.5pt, fill: luma(110), s.v)))) }
    else if s.k == "para" { parbreak() }
    else if s.k == "spk" { text(weight: "bold", size: 8.5pt, fill: luma(60))[#s.v] + h(0.3em) }
    else if s.k == "ln" { super(text(size: 6.5pt, fill: luma(110), s.v)) }
    else if s.k == "mk" { text(size: 7pt, fill: luma(110))[\[#s.v\]] }
  }
}

#let zh-run(t, notes) = {
  set par(justify: true, first-line-indent: 0pt)
  for (i, para) in t.split("\n\n").enumerate() {
    if i > 0 { parbreak() }
    let lines = para.split("\n")
    for (j, l) in lines.enumerate() { if j > 0 { linebreak() }; l }
  }
  for n in notes { super(text(size: 6.5pt, fill: rgb("#8a3b12"), n)) }
}

// ---------- 卷首 ----------
#page(header: none, footer: none)[
  #v(42mm)
  #align(center)[
    #text(size: 11pt, tracking: 0.2em)[#data.series] \
    #v(14mm)
    #text(size: 24pt, weight: "bold")[#data.title] \
    #v(6mm)
    #text(size: 13pt)[#data.volume] \
    #v(26mm)
    #text(size: 9pt, fill: luma(80))[希腊文—中文对照 · AI 翻译、AI 审校]
  ]
]
#page(header: none, footer: none)[
  #v(30mm)
  #align(center, text(size: 14pt, weight: "bold")[#data.title])
  #v(8mm)
  #align(center)[#data.volume　#data.period_zh;时期]
  #v(12mm)
  #set par(justify: false)
  *本卷所收作品*
  #v(2mm)
  #for w in data.works [
    - #w.author_zh《#w.title_zh》#if w.range != "" [（#w.range）] #text(font: grc-font, size: 9pt, fill: luma(80))[ #w.author_grc, #w.title_grc]
  ]
]

= 说明
== 凡例
+ 本卷为希腊文—中文对照本。左栏为希腊原文，右栏为中文译文，按对齐单元逐段对照；页边数字为原文单元的原有编号，诗行每五行标注一次。
+ 原文与译文的对齐单元由译者划定：诗歌可数行合为一个单元，以便按完整句子翻译；散文通常一节对应一节。
+ 译文中〔　〕内的文字为译者为语法通顺所补，或标示存疑之处；"……"表示原文缺文、残损或中断；"〔残〕"对应原文的残损标记。
+ 专名以本项目译名表（glossary/names.tsv）为准；关键术语在每部作品中首次出现时括注希腊文。卷末附注释和专名索引。
+ 原文中的整理者符号（如 [ ] 〈 〉 † 等）照录原文，不作改动。

== 底本
希腊原文取自 Eulogikon 开放语料（#link("https://github.com/eulogikon/ancient-greek-texts")），固定提交 #raw(data.source_commit)。原文为公有领域（Public Domain Mark 1.0），Eulogikon 项目的元数据以 CC0 发布。本卷未改动希腊原文；原文可疑之处见审校记录。

== 翻译与审校声明
本卷译文由人工智能（Claude）直接从希腊原文译出，并由另一独立的人工智能审校流程逐单元复核#if data.human_reviewed [；其中部分内容经过人工校订，已在目录中注明]。#if not data.human_reviewed [本卷*未经人工校订*。] 译文未参照任何受版权保护的现代中译本。欢迎指正：#link("https://github.com/yiyuanli939/37-Million/issues")。

译文以 #data.license 许可发布。

#outline(title: [目录], depth: 1, indent: 0pt)

// ---------- 正文 ----------
#for w in data.works [
  #heading(level: 1)[#w.author_zh《#w.title_zh》#if w.range != "" [（#w.range）]]
  #block(below: 1em)[
    #text(font: grc-font, size: 10.5pt)[#w.author_grc · #w.title_grc] \
    #text(size: 8pt, fill: luma(90))[#w.author_en, _#w.title_en _ · eul_wid #raw(w.eul_wid) · #w.status_zh]
  ]
  #table(
    columns: (7mm, 1.3fr, 1fr),
    stroke: none,
    inset: (x: 3pt, y: 3.5pt),
    column-gutter: 4pt,
    ..w.rows.map(r => (
      align(right, text(size: 6.5pt, fill: luma(110), r.margin.join("\n"))),
      grc-run(r.grc),
      zh-run(r.zh, r.notes),
    )).flatten()
  )
]

// ---------- 卷末 ----------
#if data.notes.len() > 0 [
  = 注释
  #set text(size: 8.5pt)
  #for g in data.notes [
    == #g.work
    #for n in g.items [
      #block(below: 0.5em)[#text(fill: rgb("#8a3b12"))[#n.n] #text(fill: luma(90))[〔#n.label〕] #n.text]
    ]
  ]
]

#if data.index.len() > 0 [
  = 专名索引
  #set text(size: 8.5pt)
  #columns(2, gutter: 8mm)[
    #for e in data.index [
      #e.zh #h(0.5em) #text(font: grc-font)[#e.grc] #h(1fr) #text(fill: luma(90))[#e.where] \
    ]
  ]
]
