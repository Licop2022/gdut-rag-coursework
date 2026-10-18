"""交付前检查数据一致性、Notebook 输出与 PPTX 结构。"""
import json
import re
import statistics
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'RAG课程作业交付'
def load(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
records=load('results/raw_results.json');summary=load('results/summary.json')
assert len(records)==12 and len([r for r in records if r['gold_docs']])==10
assert len({r['id'] for r in records})==12
for r in records:
    assert {c['id'] for c in r['candidates']}=={c['id'] for c in r['reranked_candidates']}
    assert len(r['baseline_context'])==len(r['rerank_context'])==3
    assert all(c in r['candidates'] for c in r['baseline_context'])
    assert {c['id'] for c in r['rerank_context']}<={c['id'] for c in r['candidates']}
    assert r['baseline_answer'].strip() and r['rerank_answer'].strip()
    for mode in ['baseline','rerank']:
        hits=[i+1 for i,c in enumerate(r[mode+'_context']) if c['doc_id'] in r['gold_docs']]
        expected=None if not r['gold_docs'] else {'hit1':int(bool(hits) and hits[0]==1),'hit3':int(bool(hits)),'mrr3':1/hits[0] if hits else 0}
        assert expected==r[mode+'_metrics']
valid=[r for r in records if r['gold_docs']]
for mode in ['baseline','rerank']:
    for metric in ['hit1','hit3','mrr3']:
        assert abs(statistics.mean(r[mode+'_metrics'][metric] for r in valid)-summary[mode][metric])<1e-10
nb=load('RAG课程作业.ipynb');code=[c for c in nb['cells'] if c['cell_type']=='code']
assert all(c['execution_count'] is not None for c in code)
assert not [o for c in code for o in c['outputs'] if o['output_type']=='error']
with zipfile.ZipFile(ROOT/'课程汇报.pptx') as z:
    slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    assert len(slides)==10
    assert len([n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)])==10
    assert any(n.startswith('ppt/media/') for n in z.namelist())
required=['课程汇报.pptx','RAG课程作业.ipynb','实验报告.md','四人讲稿与答辩.md','实验结果预览.html','README_先读我.md','参考资料.md','results/逐题结果.csv','models/manifest.json','启动现场问答.cmd','打开Notebook.cmd']
assert all((ROOT/f).is_file() and (ROOT/f).stat().st_size>0 for f in required)
print('PASS: 12题原始输出与汇总一致；同候选对照有效；Notebook全部执行无错误；10页PPT含备注与校标；必需文件齐全。')
