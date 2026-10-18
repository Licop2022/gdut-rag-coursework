import html
import json
import shutil
import zipfile
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];ROOT=WORK/'RAG课程作业交付'
probes=json.loads((ROOT/'results/supplementary_ranking_probes.json').read_text(encoding='utf-8'))
r=next(x for x in probes if x['id']=='S07')
preview=ROOT/'实验结果预览.html';text=preview.read_text(encoding='utf-8')
if 'id="S07"' not in text:
    rows=''.join(f'<tr><td>{i+1}</td><td>{html.escape(a["id"])}</td><td>{html.escape(b["id"])}（原第{b["vector_rank"]}名）</td></tr>' for i,(a,b) in enumerate(zip(r['candidates'],r['reranked_candidates'])))
    block=f'<section id="S07"><h2>补充排序展示：第 4 名升至第 1 名</h2><p>{html.escape(r["question"])}</p><p>从 12 条口语化探索查询中选择的机制展示，不计入固定 12 题统计。</p><table><tr><th>名次</th><th>向量排序</th><th>重排序</th></tr>{rows}</table><p><strong>重排序第一名原文：</strong>{html.escape(r["rerank_context"][0]["text"])}</p></section>'
    text=text.replace('<nav>','<nav><a href="#S07">排序展示</a>',1)
    text=text.replace('</nav>','</nav>'+block,1)
    preview.write_text(text,encoding='utf-8')
shutil.copy2(WORK/'.build/slides/slide-01.png',ROOT/'assets/PPT封面预览.png')
# CMD 使用 CRLF，避免其他 Windows 环境对 LF 批处理的兼容问题。
for path in ROOT.glob('*.cmd'):
    content=path.read_text(encoding='utf-8').replace('\r\n','\n')
    path.write_bytes(content.replace('\n','\r\n').encode('utf-8'))
archive=WORK/'RAG课程作业_轻量提交包.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(x in {'__pycache__','.venv','.ipynb_checkpoints'} for x in rel.parts):continue
        if rel.parts[0]=='models' and p.name not in {'manifest.json','README.md','LICENSE','LICENSE.txt'}:continue
        z.write(p,Path(ROOT.name)/rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert any(n.endswith('/课程汇报.pptx') for n in z.namelist())
    assert any(n.endswith('/RAG课程作业.ipynb') for n in z.namelist())
    assert not any(n.endswith('.safetensors') for n in z.namelist())
print('Created:',archive,'bytes:',archive.stat().st_size)
