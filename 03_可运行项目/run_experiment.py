"""运行固定测试集。参考标注仅用于评价，不进入检索、重排或生成。"""
import argparse
import csv
import json
import platform
import statistics
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import torch
import transformers
from rag_engine import RAG,ROOT,CONFIG,MODELS,fingerprint

def metrics(context,gold):
    if not gold: return None
    matches=[i+1 for i,c in enumerate(context) if c['doc_id'] in gold]
    return {'hit1':int(bool(matches) and matches[0]==1),'hit3':int(bool(matches)),
            'mrr3':1/matches[0] if matches else 0}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--retrieval-only',action='store_true');parser.add_argument('--output',default='results');args=parser.parse_args()
    out=ROOT/args.output;out.mkdir(exist_ok=True)
    questions=json.loads((ROOT/'data'/'questions.json').read_text(encoding='utf-8'))
    t=time.perf_counter();rag=RAG(load_generator=not args.retrieval_only);loading=time.perf_counter()-t
    # 预热不使用测试问题，避免首轮初始化影响计时。
    warm=rag.compare('请介绍本知识库的资料范围。',generate=not args.retrieval_only)
    records=[]
    for q in questions:
        start=time.perf_counter();result=rag.compare(q['question'],generate=not args.retrieval_only)
        result.update(q,baseline_metrics=metrics(result['baseline_context'],q['gold_docs']),rerank_metrics=metrics(result['rerank_context'],q['gold_docs']))
        records.append(result)
        (out/'raw_results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        print(q['id'],q['question'],result['baseline_metrics'],result['rerank_metrics'],f'{time.perf_counter()-start:.2f}s',flush=True)
    valid=[r for r in records if r['gold_docs']]
    summary={'run_utc':datetime.now(timezone.utc).isoformat(),'dataset':'自编教学语料，非外部盲测','documents':len({c['doc_id'] for c in rag.chunks}),'chunks':len(rag.chunks),'vector_dim':rag.vectors.shape[1],
             'questions':len(records),'answerable_questions':len(valid),'out_of_scope_questions':len(records)-len(valid),'models':MODELS,'config':CONFIG,'index_sha256':fingerprint(rag.chunks,rag.config),
             'environment':{'python':sys.version,'torch':torch.__version__,'transformers':transformers.__version__,'numpy':np.__version__,'os':platform.platform(),'processor':platform.processor(),'device':'CPU','threads':CONFIG['threads']},
             'model_load_and_index_s':loading,'generation_enabled':not args.retrieval_only,
             'metric_definition':'文档级相关标注。Hit@3至少命中一个相关文档，MRR@3取首个相关片段排名倒数；资料外题不参与检索指标。重复片段不合并。'}
    for label in ['baseline','rerank']:
        summary[label]={m:statistics.mean(r[label+'_metrics'][m] for r in valid) for m in ['hit1','hit3','mrr3']}
        if not args.retrieval_only: summary[label]['mean_total_s']=statistics.mean(r[label+'_total_s'] for r in records)
    summary['candidate_hit10']=statistics.mean(any(c['doc_id'] in r['gold_docs'] for c in r['candidates']) for r in valid)
    summary['mean_rerank_s']=statistics.mean(r['rerank_s'] for r in records)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    flat=[]
    for r in records:
        row={'题号':r['id'],'类型':r['kind'],'问题':r['question'],'相关文档':','.join(r['gold_docs']),
             '基础前三':','.join(c['id'] for c in r['baseline_context']),'重排前三':','.join(c['id'] for c in r['rerank_context'])}
        for label in ['baseline','rerank']:
            for m in ['hit1','hit3','mrr3']:row[label+'_'+m]=(r[label+'_metrics'] or {}).get(m,'不适用')
            row[label+'_answer']=r.get(label+'_answer','未生成');row[label+'_total_s']=r.get(label+'_total_s','未计时')
        flat.append(row)
    with (out/'逐题结果.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
