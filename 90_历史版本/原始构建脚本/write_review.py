import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'RAG课程作业交付'
records=json.loads((ROOT/'results/raw_results.json').read_text(encoding='utf-8'))
# 助手逐条阅读原始回答和相关原文后的初评，不是自动关键词评分。
judgments={
'Q01':[(2,'直接回答通常无需重训，符合 D01。没有提供引用编号。'),(0,'资料明确包含答案，却拒答，属于无依据拒答。')],
'Q02':[(0,'引入搜索引擎抓取、广告点击率等无资料支持内容，没有正确解释小片段切断证据。'),(1,'提及条件与跨句证据，但把混入无关信息错误归于小片段，又加入原文没有的结构混乱等说法。')],
'Q03':[(1,'给出一般余弦公式，未说明归一化后直接点积的简化。'),(1,'提及归一化后点积，但“不是通过模长计算”表述不严谨，未清楚限定归一化前后。')],
'Q04':[(1,'总体区分了召回与联合处理，但“候选片段如片段向量”不准确，结尾出现截断。'),(0,'把 Bi-Encoder 说成文本对联合输入，关键区分错误，结尾也出现截断。')],
'Q05':[(0,'D05 已明确重排不能补回漏召回，模型却拒答。'),(0,'D05 已明确重排不能补回漏召回，模型却拒答。')],
'Q06':[(0,'引用“可靠拒答”后得出添加来源可增加可信度，未回答引用不等于证据支持，推理错位。'),(0,'明确声称有来源编号即可证明支持，与 D06、D16 相反，即使显示引用编号也不能算正确。')],
'Q07':[(2,'准确解释 Hit@3 和首个相关结果倒数的平均，并给出有效片段编号。'),(2,'准确解释两项指标，相关上下文支持，但未提供引用编号。')],
'Q08':[(0,'回答应该计入，与 D08 的不计入原则相反。'),(0,'回答应该计入，与 D08 的不计入原则相反。')],
'Q09':[(2,'准确区分建库分区数与查询访问分区数，引用 D12-C01。'),(2,'准确区分建库分区数与查询访问分区数，引用 D12-C01。')],
'Q10':[(1,'知道需要重建，但未解释语义空间变化，把理由说成配置更新及避免重复工作。'),(2,'明确说明语义空间变化导致旧向量不再兼容，符合 D15。未给引用编号。')],
'Q11':[(2,'正确说明资料不足，没有编造私人号码。'),(2,'正确说明资料不足，没有编造私人号码。')],
'Q12':[(0,'编造考试标准答案由学生自我评估得出，没有资料依据。'),(0,'把 Hit@3 资料说成考试标准答案，构成编造，即使片段编号可能存在也不能支持结论。')]
}
items=[]
for r in records:
    for i,mode in enumerate(['baseline','rerank']):
        score,reason=judgments[r['id']][i]
        ids=re.findall(r'D\d{2}-C\d{2}',r[mode+'_answer'])
        ctx={c['id'] for c in r[mode+'_context']}
        items.append({'question_id':r['id'],'mode':mode,'answerable':bool(r['gold_docs']),'score_0_to_2':score,'reason':reason,
                      'cited_ids':ids,'citations_all_in_current_context':all(c in ctx for c in ids) if ids else None,
                      'citation_presence_is_not_factual_support':True})
review={'reviewer':'助手阅读初评，需小组成员复核','not_blinded':True,'rubric':'0=错误或无有效回答，1=部分正确或缺关键点，2=主要要点正确且有上下文支持。引用格式另查，不把存在编号视为事实支持。资料外题单独评价。',
        'items':items,'answerable_summary':{m:{'fully_correct_count':sum(x['score_0_to_2']==2 for x in items if x['mode']==m and x['answerable']),
          'score_sum':sum(x['score_0_to_2'] for x in items if x['mode']==m and x['answerable']),'max_score_sum':20} for m in ['baseline','rerank']}}
(ROOT/'results/answer_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
evidence={'demo_id':'Q10','rank_demo_id':'S07',
'answer_finding':'两组检索 Hit@3 均为 100%\n回答初评满分题数均为 3/10',
'case_finding':'Q10 重排后说清了“语义空间变化”。Q06 两组都未正确解释来源编号与证据支持的区别。检索命中与答案质量需要分开检查。',
'oos_finding':'2 道资料外题中，两组均仅 1 道可靠拒答，考试答案问题出现编造。',
'conclusion':'本题集检索指标已达上限，重排没有带来指标提升。生成端仍是主要误差来源。',
'demo_script':'两组前两名相同，第三名从向量库资料变为 RAG 原理片段。两组都有关键证据，但基础回答没讲清原因，重排后明确说出语义空间变化。这个个例不能证明重排普遍改善回答。',
'speech_finding':'回答初评满分题数两组都是三道，且资料外题各有一道出现编造。重排不保证最终回答更好。'}
(ROOT/'results/presentation_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(review['answerable_summary'],ensure_ascii=False))
