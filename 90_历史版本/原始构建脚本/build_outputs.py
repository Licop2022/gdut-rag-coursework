"""从实测 JSON 制作报告、Notebook 和静态预览。"""
import html
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'RAG课程作业交付'
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def write(name,text):(ROOT/name).write_text(text,encoding='utf-8')
def pct(x):return f'{x*100:.0f}%'
S=load('results/summary.json');R=load('results/raw_results.json');V=load('results/answer_review.json');E=load('results/presentation_evidence.json')
demo=next(r for r in R if r['id']==E['demo_id'])
probes=load('results/supplementary_ranking_probes.json')
rank_demo=next(r for r in probes if r['id']==E['rank_demo_id'])
rows='\n'.join(f'| {r["id"]} | {r["question"]} | '+('资料外 | 资料外 | 资料外 | 资料外' if not r['gold_docs'] else f'{r["baseline_metrics"]["hit3"]} | {r["rerank_metrics"]["hit3"]} | {r["baseline_metrics"]["mrr3"]:.3f} | {r["rerank_metrics"]["mrr3"]:.3f}')+' |' for r in R)
report=f'''# 课程资料问答助手：RAG 检索与重排序效果对比

选题 B。成员甲：系统与统筹；成员乙：数据与检索；成员丙：重排序与演示；成员丁：实验与评价。姓名与组号请在提交前替换。

## 摘要

本作业构建了一个在 CPU 上运行的中文 RAG 系统，以 {S['documents']} 篇自编学习资料作为知识库，使用 BGE 编码、NumPy 精确向量检索、Cross-Encoder 重排序和 Qwen2.5-0.5B-Instruct 生成。固定测试集共 {S['questions']} 题，其中 {S['answerable_questions']} 题有资料依据，{S['out_of_scope_questions']} 题在资料范围外。对照组与实验组共享同一候选，仅改变最终上下文的排序依据。

实测文档级 Hit@3 从 {pct(S['baseline']['hit3'])} 变为 {pct(S['rerank']['hit3'])}，MRR@3 从 {S['baseline']['mrr3']:.3f} 变为 {S['rerank']['mrr3']:.3f}。两组平均端到端查询耗时分别为 {S['baseline']['mean_total_s']:.2f} 秒与 {S['rerank']['mean_total_s']:.2f} 秒。{E['conclusion']} 数据和测试题共同构造，结果仅用于这套小规模教学数据的观察。

## 1. 问题与数据

课程问答既要找到相关内容，也要让生成模型正确利用内容。我们把“相关文档能否排到前面”和“答案是否正确且有资料支持”分开检查。

知识库位于 `data/corpus`，主题包括 RAG、切分、Embedding、重排序、评价、向量库与工程局限。所有正文均为自编教学资料，没有冒充教师课件。题目固定在 `data/questions.json`，在运行前确定参考文档与答案要点。共 6 道直接查询题、4 道概念辨析题、2 道资料外题。

参考答案和 gold_docs 只由评价脚本读取，不进入召回、重排序或生成。模型不针对单题编写规则，不用题目答案进行训练，也不删除实验表现不佳的题目。

## 2. 理论梳理

### 2.1 RAG 与微调

RAG 在生成时检索外部资料，便于更新知识并提供来源。微调通过训练改变参数，常用于任务适配等目标。两者可以结合。外部检索仍可能漏召回或召回干扰内容，生成模型也可能误读证据，因此不能声称 RAG 消除了幻觉。[1]

### 2.2 两阶段流程

离线流程：读取 Markdown，按字符切分，生成 BGE 向量，L2 归一化，保存向量和来源。在线流程：编码问题，精确扫描召回前 10 个片段，直接取前 3 个或重排后取前 3 个，组织相同格式提示词，再用同一生成模型回答。

每个片段保存文档编号、标题、文件名、正文字符起止位置和稳定片段 ID。语料或参数改变时，SHA256 指纹变化，系统自动生成新索引缓存。向量存储为 NumPy 矩阵与 JSON 元数据，不冒称使用 Chroma 或 Milvus。

### 2.3 Chunk 的大小与重叠

本次设置为 {S['config']['chunk_size']} 字符和 {S['config']['overlap']} 字符重叠，字符长度不等于模型 token 数。过小可能切断条件和跨句证据，过大可能混入无关内容并增加计算。overlap 缓解边界截断，也造成重复片段与成本。本次固定切分参数，未对切分优劣作单独实验结论。

### 2.4 Embedding 与余弦

使用 `{S['models']['embedding']}`，取 CLS 隐藏状态并作 L2 归一化。问题按模型说明加检索指令，文档不加。向量维度为 {S['vector_dim']}。余弦公式为 cos(q,d)=(q·d)/(||q|| ||d||)，归一化后可直接点积。相似度反映模型给出的相对相关性，不是答案正确概率。[3]

### 2.5 Bi-Encoder 与 Cross-Encoder

Bi-Encoder 分别编码，可预先缓存文档向量。Cross-Encoder 将问题和片段联合编码，逐对输出分数，适合对小批候选精排。本次使用 `{S['models']['reranker']}`。两类分数不能直接比较绝对大小。重排序只能改变候选顺序，初次召回遗漏的文档无法靠重排序补回。[2][4]

## 3. 实现与配置

| 配置项 | 实际取值 |
|---|---|
| 知识库 / 片段 | {S['documents']} 篇 / {S['chunks']} 个 |
| 切分 | {S['config']['chunk_size']} 字符，overlap={S['config']['overlap']} 字符 |
| 编码 | BGE-small-zh-v1.5，CLS + L2，最大输入 384 token |
| 初次召回 / 最终上下文 | 10 / 3 |
| 向量扫描 | NumPy 精确点积，按分数稳定排序 |
| 重排 | mmarco-mMiniLMv2-L12-H384-v1，文本对输入，最大 384 token |
| 生成模型 | {S['models']['generator']} |
| 解码 | do_sample=False，最多 {S['config']['max_new_tokens']} 个新 token |
| 设备与线程 | CPU，{S['config']['threads']} 线程 |
| 随机种子 | {S['config']['seed']} |
| Python / PyTorch / Transformers | {S['environment']['python'].split()[0]} / {S['environment']['torch']} / {S['environment']['transformers']} |

模型通过公开 ModelScope 镜像下载，逐文件校验仓库给出的大小与 SHA256。下载清单在 `models/manifest.json`，这是镜像侧完整性核验，不声称已独立核对原始发布者权重散列。推理加载本地 safetensors，不执行远程代码。生成器使用官方模型卡给出的聊天模板。[5]

## 4. 实验设计与指标

两组共享资料、索引、问题向量、前 10 个候选、生成器、提示词和解码设置。基础组按余弦取前 3 个，实验组按重排分数取前 3 个。没有加入去重或关键词规则，避免把其他处理的效果误归因于 Rerank。

参考相关性按**文档级**标注：只要结果片段的 doc_id 属于预先标注的相关文档就算相关。因此这些指标不保证片段完整覆盖答案所需证据，也不等于答案准确率。重叠产生的同文档片段不合并。

- Hit@1：第一名相关的题目比例。
- Hit@3：前三名至少有一个相关片段的题目比例。
- MRR@3：前三名中第一个相关片段的排名倒数，未命中为 0，再对题目平均。
- 候选 Hit@10：初次前 10 个候选至少命中相关文档的题目比例。
- 资料外题单独检查拒答与编造，不计入上述指标分母。

运行前预热。模型加载与首次建库耗时为 {S['model_load_and_index_s']:.2f} 秒，单独记录。逐题查询耗时为问题编码与检索、可选重排、提示词模板化、分词与生成的阶段合计，不包含用户界面、文件读写及模型初次加载。两组按固定顺序运行，CPU 负载和缓存也会造成波动，没有做严格延迟基准或显著性检验。

## 5. 实际结果

| 指标 | 基础 RAG | 加入 Rerank |
|---|---:|---:|
| Hit@1，n=10 | {pct(S['baseline']['hit1'])} | {pct(S['rerank']['hit1'])} |
| Hit@3，n=10 | {pct(S['baseline']['hit3'])} | {pct(S['rerank']['hit3'])} |
| MRR@3，n=10 | {S['baseline']['mrr3']:.3f} | {S['rerank']['mrr3']:.3f} |
| 平均阶段合计耗时，n=12 | {S['baseline']['mean_total_s']:.2f} 秒 | {S['rerank']['mean_total_s']:.2f} 秒 |

候选 Hit@10={pct(S['candidate_hit10'])}。平均额外重排耗时为 {S['mean_rerank_s']:.3f} 秒。

| 题号 | 问题 | 基础 Hit@3 | 重排 Hit@3 | 基础 MRR@3 | 重排 MRR@3 |
|---|---|---:|---:|---:|---:|
{rows}

### 5.1 排序案例

补充口语化查询：{rank_demo['question']}

该例中 D08-C02 从向量排序第 4 名升到重排序第 1 名，其内容讨论相关片段不代表完整证据覆盖。该案例从 12 条口语化探索查询中选取，完整探索记录保存在 `results/supplementary_ranking_probes.json`，**仅解释排序机制，不计入上面的固定 12 题统计，也不作为普遍收益证据**。

演示题 {demo['id']}：{demo['question']}

基础前三：{', '.join(c['id'] for c in demo['baseline_context'])}。

重排前三：{', '.join(c['id'] for c in demo['rerank_context'])}。

{E['case_finding']}

基础回答原文：

> {demo['baseline_answer'].replace(chr(10),chr(10)+'> ')}

重排回答原文：

> {demo['rerank_answer'].replace(chr(10),chr(10)+'> ')}

### 5.2 回答核验

{E['answer_finding']}

完整逐题初评见 `results/answer_review.json`，初评由助手阅读原始回答和资料完成，须由组员复核。不是独立人工盲评，也没有将关键词出现当作答案正确。0 分为错误或无有效回答，1 分为部分正确或缺关键要点，2 分为主要要点正确且有资料支持。引用是否完整和输出是否截断也另行检查，引用缺失时不会将其描述为可靠的可追溯回答。

{E['oos_finding']}

## 6. 自主整理的思考题

说明：用户提供了作业要求截图，没有提供完整课件，因此以下题目是依据课程主题自主整理的讨论，不冒充教师原题。

**为什么 RAG 不总优于直接生成？** 检索引入的错误、过期内容、冲突或干扰会影响生成。应保证资料质量并核验关键依据，不能只因加入检索就假设答案正确。

**为什么重排可能提高排名，却没有改善最终答案？** 最终上下文可能已包含相同核心证据，或生成模型仍然误读、遗漏限制。文档级排名指标本身也不保证片段包含完整证据。

**为什么不把资料外题放进 Hit@3 分母？** 它们没有相关文档，标准检索命中指标不适用，应单独检查系统是否说明资料不足。

**为什么重排分数不能和余弦直接相减？** 两个模型输出的评分范围与含义不同，应比较相同任务上的排序或下游表现。

**PDF 表格如何扩展？** 保留页码与表格位置，识别结构并生成可检索描述，回答时回看原图核对单位和数字。描述生成也会出错，本次没有实施多模态解析。

**Chroma 与 Milvus 如何选择？** 二者均有专门向量检索功能，具体选择需依据数据量、过滤、并发、运维等条件实测。本作业使用轻量精确扫描，不给出未经测量的产品性能排名。Milvus 的 IVF_FLAT 中 nlist 是建库分区数，nprobe 是查询访问分区数；HNSW 使用图索引，两者参数不可混用。[6][7][8]

## 7. 实施问题与处理

1. 已有 PyTorch 环境导入时报 DLL 错误。采用工作区独立 Python 3.11 环境，不改动用户已有环境。
2. 当前网络访问 Hugging Face 超时。改用公开 ModelScope 同名镜像，保留下载来源与校验清单。
3. 旧 pip 解析 typing-extensions 元数据出错。更新独立环境中的 pip 后重新安装依赖。
4. 为防止资料更新后继续检索旧向量，缓存名包含语料与配置指纹，并检查片段数量。
5. 现场推理存在等待风险。提前加载模型与索引，保存已执行 Notebook 和静态预览。静态预览明确标注为已保存结果，不伪装现场推理。

## 8. 结论与局限

{E['conclusion']}

本次完成了真实本地模型的 RAG 闭环、同候选重排序对照和可追溯结果保存。主要局限是自编语料与题目之间存在构造相关性，样本小，相关性标注粒度为文档，生成器只有 0.5B 参数，运行顺序固定、计时次数少。不能把这些结果推广为通用性能结论。后续应用真实课件构建独立题集，细化证据片段标注，采用双人核验并重复实验。

## 参考资料

完整链接与下载说明见 `参考资料.md`。编号 [1]—[8] 与其中列表一致。
'''
write('实验报告.md',report)

speech=f'''# 四人讲稿与答辩

总时长目标：4 分 30 秒，预留 30 秒。姓名与组号在提交前填写。以下是学习和排练用讲稿，不代表四名成员已经亲自完成其中工作。

## 成员甲：40 秒，第 1—2 页

我们的题目是课程资料问答助手，选择重排序方向。我们用二十篇自编的 RAG 学习资料建立知识库，希望回答能够找到可核对的来源。问题不只在于能否检索到相关文字，也在于它是否排在前面，以及生成模型能否正确利用。接下来我们用固定题集，对同一批候选进行有无重排序的比较。四人分别负责系统、检索、重排和评价。

## 成员乙：65 秒，第 3—4 页

系统分为离线建库与在线问答。离线读取资料，按一百八十个字符切分，相邻片段重叠三十六个字符，用中文 BGE 生成向量并保存来源。这里是字符数，不是模型 token 数。片段太小容易切断证据，太大会带入干扰，重叠则会增加冗余。我们取 CLS 向量做 L2 归一化，点积就等于余弦相似度。问题与资料使用相同编码器，在线先召回十个片段。当前共 {S['chunks']} 个片段，使用精确向量扫描，便于检查每一步结果。

## 成员丙：100 秒，第 5 页和第 8 页

第 5 页，约 25 秒：Bi-Encoder 分别编码问题与文档，能提前保存文档向量。Cross-Encoder 把问题和片段联合输入，逐对评分，所以适合重排少量候选。我们重排同一批十个片段，再取前三个。两种模型的分数不是同一量纲，不能直接比较。重排也不能找回初次召回中缺失的证据。

第 8 页，约 75 秒：先看补充查询“{rank_demo['question']}”，D08-C02 从第四名升到第一名。这个例子用于解释机制，没有计入固定题集。再演示“{demo['question']}”。{E['demo_script']} 接着核对回答和引用片段，完整结果保存在作业中。最后交给实验结论。

## 成员丁：65 秒，第 6—7 页、第 9—10 页

我们固定了语料、切分、候选、提示词和生成设置，只改变是否重排序。十二道题中十道有资料依据，两道资料外题单独检查。文档级 Hit@3 从 {pct(S['baseline']['hit3'])} 变为 {pct(S['rerank']['hit3'])}，MRR@3 从 {S['baseline']['mrr3']:.3f} 变为 {S['rerank']['mrr3']:.3f}。这衡量相关资料的排名，不能等同于答案准确率。{E['speech_finding']} 本次资料和题目为自编，小样本和小模型限制了结论。我们完成了可运行、可追溯的对照，后续应使用真实课件题集和双人核验。

## 现场操作

1. 课前双击“打开Notebook.cmd”，运行加载模型单元格并完成一次预热。
2. PPT 第 8 页切到 Notebook 的“现场问答”单元格，使用当前演示题。
3. 运行后先展示候选排名，再展示回答和原文。
4. 若出现明显等待或报错，切换“实验结果预览.html”，明确说明这是已保存的实验记录。
5. 切回第 9 页，丁完成结论。不要在台上安装依赖或下载模型。

## 答辩简答

- **为什么不全部做 Milvus、多模态？** 本组选题 B，重点是受控的重排序实验。其他方向作为理论扩展，没有声称完成其部署。
- **Rerank 一定提升吗？** 不一定。正确资料未被召回时无能为力，重排模型也可能排序错误。
- **怎么保证公平？** 两组复用完全相同的候选，并固定生成与上下文数量。答案参考只进入评价。
- **为什么相关性高仍会回答错？** 相关文档的当前片段可能缺少完整证据，小生成模型也可能误读或编造。
- **为什么拒答也要测试？** 系统面对资料外问题时应说明不足。仅靠提示词无法保证，所以保存实际回答。
- **怎样解释未改善或退化？** 保留原始题目和输出，分别检查候选、上下文和生成，不用单个成功例子代替总体结果。
- **自动指标可靠吗？** 这里的检索指标基于预先标注文档，答案另外阅读初评，需组员复核，不将词语命中当答案正确。
- **速度可推广吗？** 不可以。当前是本机单次 CPU 运行，加载已剔除，计时边界和固定顺序都在报告中披露。
- **课件思考题在哪里？** 现有版本使用自主整理的讨论，原课件尚未提供；若老师要求逐题对应，需要对照课件替换。
'''
write('四人讲稿与答辩.md',speech)

# 离线结果预览保留原始输出，不假装动态推理。
parts=[]
def esc(s):return html.escape(str(s))
for r in R:
    ranking='<table><tr><th>名次</th><th>向量排序</th><th>重排序</th></tr>'
    for i in range(10):
        a=r['candidates'][i];b=r['reranked_candidates'][i]
        ranking+=f'<tr><td>{i+1}</td><td>{esc(a["id"])} {esc(a["title"])}<br><small>cosine {a["vector_score"]:.4f}</small></td><td>{esc(b["id"])} {esc(b["title"])}<br><small>rerank {b["rerank_score"]:.4f}</small></td></tr>'
    ranking+='</table>'
    contexts=''.join(f'<p><strong>[{esc(c["id"])}] {esc(c["title"])}</strong><br>{esc(c["text"])}</p>' for c in r['rerank_context'])
    parts.append(f'<section id="{r["id"]}"><h2>{r["id"]} {esc(r["question"])}</h2><p class="sub">{esc(r["kind"])}，参考文档：{esc(", ".join(r["gold_docs"]) or "资料外")}</p><details><summary>查看全部 10 个候选的前后排序</summary>{ranking}</details><h3>基础 RAG 回答</h3><pre>{esc(r["baseline_answer"])}</pre><h3>重排序后回答</h3><pre>{esc(r["rerank_answer"])}</pre><p>基础阶段合计 {r["baseline_total_s"]:.2f} 秒，重排组阶段合计 {r["rerank_total_s"]:.2f} 秒。</p><details><summary>核对重排序上下文原文</summary>{contexts}</details></section>')
preview=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAG 实验结果预览</title><style>body{{max-width:1100px;margin:42px auto;padding:0 28px;font:18px/1.7 "Microsoft YaHei",sans-serif;color:#152d44;background:#f7f9fa}}h1{{font-size:36px}}h2{{font-size:25px}}h3{{font-size:20px;color:#007f7c}}section{{background:white;padding:28px;margin:26px 0;border-top:3px solid #007f7c}}.sub,small{{color:#526474}}table{{border-collapse:collapse;width:100%;margin:18px 0}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #dbe4e9}}th{{background:#e8eff2}}pre{{font:inherit;white-space:pre-wrap;background:#f0f5f5;padding:16px;overflow-wrap:anywhere}}summary{{cursor:pointer;color:#007f7c}}nav a{{margin-right:14px;color:#007f7c}}@media print{{details{{display:block}}section{{break-inside:avoid}}}}</style><h1>课程资料问答助手：实验记录</h1><p><strong>这是保存的真实实验输出，供离线查看，不是现场推理界面。</strong></p><p>自编资料 {S['documents']} 篇，片段 {S['chunks']} 个，测试题 {S['questions']} 道。检索指标分母为 10 道有依据题。</p><table><tr><th>指标</th><th>基础 RAG</th><th>加入 Rerank</th></tr><tr><td>Hit@3</td><td>{pct(S['baseline']['hit3'])}</td><td>{pct(S['rerank']['hit3'])}</td></tr><tr><td>MRR@3</td><td>{S['baseline']['mrr3']:.3f}</td><td>{S['rerank']['mrr3']:.3f}</td></tr></table><p>{esc(E['conclusion'])}</p><nav>{''.join(f'<a href="#{r["id"]}">{r["id"]}</a>' for r in R)}</nav>{''.join(parts)}<p>模型、软件环境与参数见 results/summary.json。回答初评见 results/answer_review.json。参考资料见同目录文件。</p></html>'''
write('实验结果预览.html',preview)

# Notebook 用标准 nbformat 结构，执行步骤独立于生成步骤。
cells=[]
def md(text):cells.append({'cell_type':'markdown','metadata':{},'source':text})
def code(text):cells.append({'cell_type':'code','metadata':{},'source':text,'execution_count':None,'outputs':[]})
md('''# 课程资料问答助手：RAG 检索与重排序效果对比

**选题 B，可运行本地模型版本。** 四位成员的分工和讲稿见配套材料。

知识库为 20 篇自编教学资料，测试题为 12 道内部构造题，结果不代表外部盲测。模型与参数完整记录在 `results/summary.json`。本 Notebook 同时包含理论、代码说明、已保存结果与现场问答入口。''')
md('''## 1. 理论与流程

离线：读取资料 → 字符切分 → BGE 向量化 → 持久化向量与来源。\n在线：编码问题 → 召回 10 个 → 原始顺序或 Cross-Encoder 重排 → 选 3 个 → 同一 Qwen 模型生成。

RAG 利用外部资料提供依据，微调改变模型参数，二者可以结合。RAG 仍可能因检索失败或生成误读而出错。Chunk 太小容易切断证据，太大可能带入干扰；overlap 缓解边界问题，也会增加冗余。

BGE 使用 CLS 池化和 L2 归一化，归一化后点积等于余弦相似度。Bi-Encoder 独立编码便于缓存，Cross-Encoder 联合编码文本对，适合精排候选。余弦分数与重排分数不能直接比较大小。''')
code('''from pathlib import Path
import json, sys
from IPython.display import display, Markdown
ROOT = Path.cwd()
if not (ROOT / "rag_engine.py").exists():
    if (ROOT / "RAG课程作业交付" / "rag_engine.py").exists():
        ROOT = ROOT / "RAG课程作业交付"
    else:
        raise RuntimeError("请从交付文件夹打开 Notebook")
sys.path.insert(0, str(ROOT))
from rag_engine import RAG, CONFIG, MODELS, corpus_chunks, split_text
print("Python:", sys.executable)
print("模型:", json.dumps(MODELS, ensure_ascii=False, indent=2))
print("配置:", CONFIG)''')
md('''## 2. 资料与切分

正文字符位置可回到原始资料核验。这里的 180/36 指字符，不是 token。参考答案保存在独立测试文件，不进入检索、重排或生成。''')
code('''chunks = corpus_chunks()
print("文档数:", len({c["doc_id"] for c in chunks}), "片段数:", len(chunks))
for c in chunks[:2]:
    print(c["id"], "正文字符范围:", (c["start"], c["end"]))
    print(c["text"], "\\n")
example = list(split_text("甲乙丙丁戊己庚辛壬癸", size=6, overlap=2))
print("切分边界示例:", example)''')
md('''## 3. 加载本地模型并预热

首次运行本单元格需要等待。模型准备好以后，台上只运行下面的查询单元格。向量扫描采用 NumPy 精确检索，并未部署 Chroma 或 Milvus。所有模型强制从本地目录加载。''')
code('''rag = RAG()
_ = rag.compare("请介绍本知识库的资料范围。", generate=False)
print("模型已加载，向量矩阵形状:", rag.vectors.shape)
print("可以执行现场查询。")''')
md('''## 4. 现场问答：修改 question 后运行

输出前 10 个候选的排序、最终上下文、两组生成回答和计时。两个分数只在各自模型内部用于排序。资料外问题也可以直接输入，观察小模型能否说明资料不足。''')
md('''### 补充排序演示：原第 4 名提升到第 1 名

从 12 条口语化探索查询中选择的实际案例，仅解释排序机制，不计入固定 12 题的实验统计。''')
code(f'''ranking_question = {rank_demo['question']!r}
ranking_demo = rag.compare(ranking_question, generate=False)
print("问题:", ranking_question)
for i, (a,b) in enumerate(zip(ranking_demo["candidates"], ranking_demo["reranked_candidates"]),1):
    print(f"{{i}}\\t向量: {{a['id']}}\\t重排: {{b['id']}}（原第{{b['vector_rank']}}名）")
print("重排序第一名原文:", ranking_demo["rerank_context"][0]["text"])''')
md('''### 固定题集 Q10 的生成对比

修改下面的问题可继续提问。模型只看到当前资料，不读取参考答案。''')
code(f'''question = {demo['question']!r}
demo = rag.compare(question)
print("问题:", question)
print("名次\\t向量排序\\t\\t重排序")
for i, (a,b) in enumerate(zip(demo["candidates"], demo["reranked_candidates"]),1):
    print(f"{{i}}\\t{{a['id']}} ({{a['vector_score']:.3f}})\\t{{b['id']}} ({{b['rerank_score']:.3f}})")
print("\\n基础回答:\\n", demo["baseline_answer"])
print("\\n重排回答:\\n", demo["rerank_answer"])
print("\\n阶段合计耗时:", round(demo["baseline_total_s"],2), round(demo["rerank_total_s"],2), "秒")''')
md('''## 5. 回看原文与实现

引用编号仅是定位方式，不能替代事实核验。下面显示实际送给生成器的片段。原理对应的真实实现来自 `rag_engine.py`，可以直接阅读与修改。''')
code('''for c in demo["rerank_context"]:
    print(f"[{c['id']}] {c['file']}，正文字符 {c['start']}:{c['end']}")
    print(c["text"], "\\n")
import inspect
print(inspect.getsource(RAG.encode))
print(inspect.getsource(RAG.rerank))''')
md('''## 6. 固定测试集的已保存实验

固定候选、最终上下文数量、生成器与提示词，仅改变排序方式。以下读取交付时已执行的完整题集，避免台上重新生成 24 条回答。

Hit@3 按预先标注的相关文档计算，MRR@3 取首个相关片段排名倒数；资料外题不计入检索分母。同文档重叠片段不合并，因此文档命中不保证完整证据或答案正确。''')
code('''summary = json.loads((ROOT/"results/summary.json").read_text(encoding="utf-8"))
records = json.loads((ROOT/"results/raw_results.json").read_text(encoding="utf-8"))
lines = ["|指标|基础 RAG|加入 Rerank|", "|---|---:|---:|"]
for m in ["hit1", "hit3", "mrr3"]:
    lines.append(f"|{m}|{summary['baseline'][m]:.3f}|{summary['rerank'][m]:.3f}|")
lines.append(f"|平均阶段合计秒|{summary['baseline']['mean_total_s']:.2f}|{summary['rerank']['mean_total_s']:.2f}|")
display(Markdown("\\n".join(lines)))
for r in records:
    print(r["id"], r["question"], "\\n", r["baseline_metrics"], r["rerank_metrics"])
print("环境:", summary["environment"])''')
md('''## 7. 回答、资料外问题与失败案例

助手初评在 `answer_review.json`，需要组员复核，不是独立人工盲评。检索相关性与回答正确性分开检查。''')
code('''findings = json.loads((ROOT/"results/presentation_evidence.json").read_text(encoding="utf-8"))
for key in ["answer_finding","case_finding","oos_finding","conclusion"]:
    print(findings[key], "\\n")
for r in records:
    if not r["gold_docs"]:
        print(r["id"], r["question"])
        print("基础:", r["baseline_answer"])
        print("重排:", r["rerank_answer"], "\\n")''')
md('''## 8. 自主思考题与拓展

- **为什么重排不能弥补漏召回？** 它只能处理已进入候选集合的片段。
- **为什么不把资料外题放进命中率分母？** 没有相关文档，检索指标不适用，应单独检查拒答和编造。
- **为什么重排改善排名却可能不改善答案？** 文档级指标并不保证片段完整，生成器也可能误读证据。
- **PDF 表格如何扩展？** 识别表格区域、保留行列单位，生成可检索描述，回答回查原图；本次未实现。
- **Milvus 参数如何理解？** IVF_FLAT 的 nlist 是建库分区数、nprobe 是查询访问分区数；HNSW 使用邻近图，参数不能混用。本次未部署 Milvus。

这些是依据课程主题自主整理的讨论，原课件思考题尚未提供，未冒充教师原题。完整理论、实际问题与来源见 `实验报告.md` 和 `参考资料.md`。''')
md('''## 9. 复现实验与检查

完整实验会对每题生成两组回答，耗时明显长于单题 Demo。下面默认不运行，以保护已交付结果。

程序测试覆盖切分边界、覆盖与缓存失效。重新实验使用新的结果目录，保留原始数据。''')
code('''RUN_FULL_EXPERIMENT = False
if RUN_FULL_EXPERIMENT:
    import subprocess
    subprocess.run([sys.executable, str(ROOT/"run_experiment.py"), "--output", "results_rerun"], cwd=ROOT, check=True)
else:
    print("完整实验未重新执行。交付时的实测结果已展示，现场使用第4节单题演示。")
import subprocess
check = subprocess.run([sys.executable, "-m", "unittest", "test_core.py"], cwd=ROOT, capture_output=True, text=True)
print(check.stdout, check.stderr)
assert check.returncode == 0''')
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3 (项目环境)','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'}},'cells':cells}
for i,c in enumerate(cells):c['id']=f'rag-{i:02}'
write('RAG课程作业.ipynb',json.dumps(nb,ensure_ascii=False,indent=2))
print('报告、讲稿、静态预览与 Notebook 已生成。')
