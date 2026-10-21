import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


cells = [
md("# 研究生奖学金资料问答：Rerank 与 9B LoRA 对照\n\n课程选题B。仅使用《2026广东工业大学研究生手册》印刷页193—198的奖学金评审办法。真实成员姓名与分工由组员填写。"),
md("## 1. 研究问题\n\n大模型可能知识过时、无法直接获知校内细则、生成缺乏依据。RAG在回答时提供可核查证据，适合更新资料；LoRA更新少量模型参数，适合适配回答行为，但需要训练数据且可能过拟合。本文先比较有无Rerank，再将LoRA作为独立扩展，不能把两种变化混为一个因素。"),
md("## 2. 两阶段架构\n\n离线：PDF六页 → 核对表格及跨页条款 → 26条 → 27片段 → BGE-M3向量 → 持久化索引。\n\n在线：问题 → Top-5粗召回 → Cross-Encoder重排 → 前2条证据 → Qwen3.5-9B回答与引用。\n\n基线直接按向量顺序取前2条；实验组从同一Top-5中重排后取前2条。"),
code("from pathlib import Path\nimport json\nfrom IPython.display import display, Markdown\nROOT=Path.cwd()\nif not (ROOT/'data/source_manifest.json').exists():\n    raise RuntimeError('请从server_scholarship_9b目录打开Notebook')\nsource=json.loads((ROOT/'data/source_manifest.json').read_text(encoding='utf-8'))\ndisplay(source)\n"),
md("## 3. 切分与表格处理\n\n每块至多380个Unicode字符，重叠60字符，优先保留条款边界。长度不是token数。合并跨页条款，表格补全博士/硕士类型，并保留金额与比例对应关系。此处为选题B的文本表格整理，没有实现选题C-1的表格检测、截图和VLM描述流程。"),
code("chunks=[json.loads(x) for x in (ROOT/'data/chunks.jsonl').read_text(encoding='utf-8').splitlines()]\nprint('片段数量:',len(chunks))\ndisplay(next(c for c in chunks if c['article_id']=='A05'))\n"),
md("## 4. Embedding与Cross-Encoder\n\nBi-Encoder分别编码问题和片段，向量可预计算。使用CLS池化与L2归一化，归一化向量点积等于余弦相似度；此时平方欧氏距离为2−2cos，排序等价。未归一化时，两种度量的排序可能不同。\n\nCross-Encoder同时读取问题与候选片段，计算更细致的相关性，成本较高，因此只精排Top-5。两种分数尺度不同，不直接比较数值大小。"),
md("## 5. 实验设计\n\n固定知识库、切分、检索器、Top-5、上下文数量、生成模型、提示词和解码设置，只改变是否重排。扩展实验再固定同一检索结果，比较基础权重与LoRA adapter。\n\n固定测试16题，其中4题资料不足。LoRA训练27题、开发3题，按条款与测试隔离。此规模只能验证流程，不能证明泛化提升。"),
code("def load_run(name):\n    p=ROOT/'runs'/name/'answers.json'\n    if not p.exists():\n        raise RuntimeError(f'{name}完整结果尚未生成或尚未从服务器同步')\n    return json.loads(p.read_text(encoding='utf-8'))\nbase=load_run('base')\nfor route in ['baseline','rerank']:\n    print(route,base[6][route+'_generation']['answer'])\n"),
md("## 6. 排序变化与答案核验\n\n展示真实的候选顺序、前2条上下文和最终回答。第4升第1的案例从独立探索题中寻找，不手工调整排名，也不混入固定测试汇总。排序变化不必然意味着答案改善。"),
code("p=ROOT/'runs/ranking_probes_situational/verified_candidate_cases.json'\ncases=json.loads(p.read_text(encoding='utf-8')) if p.exists() else []\nprint('实际发现的探索案例数:',len(cases))\nif cases:\n    case=cases[0]\n    print(case['question'])\n    display([{'片段':c['id'],'向量名次':c['vector_rank'],'重排名次':c['rerank_rank'],'正文':c['text']} for c in case['reranked_candidates']])\nelse:\n    print('尚无已验证的第4升第1案例，不能声称已满足这一现象。')\n"),
md("## 7. LoRA训练与留出评测\n\n冻结9B基础权重和视觉模块，只训练文本decoder中的LoRA参数。r=8、3 epoch、学习率5e-5、batch=1、累积4，仅回答token参与损失。配置预先固定，未根据测试表现选择checkpoint。\n\n检查实际训练清单与开发损失，再对照相同问题和证据。关键词覆盖与引用格式只辅助检查，不当作答案正确率。"),
code("p=ROOT/'adapters/lora_pilot/training_manifest.json'\nif p.exists():\n    training=json.loads(p.read_text(encoding='utf-8'))\n    display({k:training[k] for k in ['complete','train_examples','dev_examples','epochs','rank','training_metrics','dev_metrics']})\nelse:\n    print('本地尚无完整训练清单，请先同步服务器结果。')\nlora=load_run('lora')\nfor old,new in zip(base,lora):\n    print(old['test']['id'],old['question'])\n    print('原始9B:',old['rerank_generation']['answer'])\n    print('LoRA:',new['rerank_generation']['answer'])\n    print()\n"),
md("## 8. 现场演示\n\n先保持Windows SSH端口转发，再在浏览器打开 http://127.0.0.1:18765 。网页显示基础/重排两组答案、Top-5排名变化和实际证据；可切换原始9B与LoRA。现场记录单独保存。\n\n每位组员都应发言；汇报含切换不超过5分钟。提前在演示设备录制备用视频，但现场优先实机运行。"),
md("## 9. 局限与思考\n\n正确证据若未进入Top-5，重排无法找回。片段太短会丢条件，太长可能稀释相关性。27个训练样本容易过拟合；同一政策章节的留出题不代表外部泛化。引用编号不代表引用内容正确，需要逐条对照原文。仅代表给定手册版本，未核实后续政策更新。\n\n本实现用NumPy精确扫描持久化小型索引；Chroma适合轻量本地向量库，Milvus适合更大规模服务，两者都不自动解决证据质量和幻觉。实际坑点及结果需依据服务器日志补充。"),
]
notebook={"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"}},"nbformat":4,"nbformat_minor":5}
for index,cell in enumerate(cells): cell['id']=f'gdut9b-{index:02d}'
(ROOT/'9B奖学金RAG与LoRA实验.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
print('Notebook created; saved outputs are intentionally empty until real runs complete.')
