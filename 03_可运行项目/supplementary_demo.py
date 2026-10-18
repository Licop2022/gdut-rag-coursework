"""补充口语化问题的排序展示，不纳入预先固定的12题统计。"""
import json
from rag_engine import RAG,ROOT

QUESTIONS=[
'为什么同一个答案加个脚注还不够？',
'代码本身没改，原文换了以后为什么还会搜出旧结论？',
'原因和限制条件被切到两段里了，怎样减少这种问题？',
'只把表格文字按顺序排成一行，为什么可能看错金额所属项目？',
'一个指标只看有没有找中，另一个还区分第一和第三，它们有什么区别？',
'为什么同一段材料反复出现会浪费可用的输入位置？',
'搜到的材料来自相关文件，为什么仍不等于能答完整？',
'排序器看不到那段材料，还能把它调到第一名吗？',
'某个网络给0.8，另一个给4，能说明后者的答案更可靠吗？',
'文章出现了几个标准答案里的词，就能说回答正确吗？',
'不改模型参数，只把资料放进回答时的输入，这和训练模型有什么差别？',
'已经做了归一化，再计算方向接近程度还需要除模长吗？'
]
if __name__=='__main__':
    rag=RAG(load_generator=False);results=[]
    for i,q in enumerate(QUESTIONS):
        r=rag.compare(q,generate=False);r['id']=f'S{i+1:02}';results.append(r)
        c=r['rerank_context'][0]
        print(r['id'],q,'TOP:',c['id'],'原排名:',c['vector_rank'],flush=True)
    (ROOT/'results'/'supplementary_ranking_probes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
