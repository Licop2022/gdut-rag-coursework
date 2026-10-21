"""Two chunk configurations, one model and retrieval route, isolated from active state."""
from difflib import SequenceMatcher
import re
import time


def answer_diff(left, right):
    # Keep citations and numbers together while permitting fine-grained Chinese diffs.
    tokenize = lambda text: re.findall(r"\[[^\]\n]+\]|[A-Za-z0-9_.%]+|\s+|.", text, re.S)
    a, b = tokenize(left), tokenize(right)
    outputs = [[], []]
    for tag, i, j, k, l in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        for output, tokens in [(outputs[0], a[i:j]), (outputs[1], b[k:l])]:
            if tokens:
                output.append({"text": "".join(tokens), "different": tag != "equal"})
    return {"identical": left == right, "a": outputs[0], "b": outputs[1]}


def evidence_segments(chunk, other_contexts):
    covered = set()
    for other in other_contexts:
        if other['article_id'] == chunk['article_id']:
            covered.update(range(other['start'], other['end']))
    segments = []
    for offset, character in enumerate(chunk['text'], chunk['start']):
        different = offset not in covered
        if segments and segments[-1]['different'] == different:
            segments[-1]['text'] += character
        else:
            segments.append({'text': character, 'different': different})
    return segments


def coverage(contexts):
    return {(c['article_id'], i) for c in contexts for i in range(c['start'], c['end'])}


def run_comparison(store, retriever, generator, question, profiles, route, use_lora, settings):
    if route not in ['baseline', 'rerank']:
        raise ValueError('请选择基础 RAG 或 Rerank RAG')
    if not isinstance(profiles, list) or len(profiles) != 2 or not all(isinstance(p, dict) for p in profiles):
        raise ValueError('请提供 A、B 两组分块参数')
    snapshots = [store.preview(p.get('chunk_size'), p.get('overlap')) for p in profiles]
    if snapshots[0]['config'] == snapshots[1]['config']:
        raise ValueError('两组参数相同，请修改 chunk 长度或重叠长度后再对比')
    original = retriever.chunks, retriever.vectors, retriever.index_fingerprint
    results = []
    try:
        for label, snapshot in zip(['A', 'B'], snapshots):
            start = time.perf_counter()
            prepared = retriever.prepare_index(snapshot['chunks'])
            index_s = time.perf_counter() - start
            retriever.use_index(prepared)
            retrieval = retriever.retrieve(question)
            contexts = retrieval[route + '_context']
            generation = generator.generate(question, contexts, use_adapter=use_lora)
            results.append({'label': label, 'config': snapshot['config'], 'chunk_count': len(snapshot['chunks']),
                            'index_fingerprint': retriever.index_fingerprint, 'contexts': contexts,
                            'retrieval': retrieval, 'generation': generation,
                            'metrics': {'index_s': index_s, 'retrieval_s': retrieval['retrieval_s'],
                                        'rerank_s': retrieval['rerank_s'], 'generation_s': generation['generation_s'],
                                        'evidence_characters': sum(len(c['text']) for c in contexts),
                                        'unique_source_characters': len(coverage(contexts)),
                                        'context_count': len(contexts),
                                        'articles': list(dict.fromkeys(c['article_id'] for c in contexts))}})
    finally:
        retriever.use_index(original)
    for own, other in [(results[0], results[1]), (results[1], results[0])]:
        own['evidence_diff'] = [evidence_segments(c, other['contexts']) for c in own['contexts']]
    cover_a, cover_b = [coverage(r['contexts']) for r in results]
    return {'question': question, 'route': route, 'used_lora': use_lora, 'settings': dict(settings),
            'execution_order': ['A', 'B'], 'profiles': results,
            'answer_diff': answer_diff(*[r['generation']['answer'] for r in results]),
            'evidence_comparison': {'shared_characters': len(cover_a & cover_b),
                                    'only_a_characters': len(cover_a - cover_b),
                                    'only_b_characters': len(cover_b - cover_a)},
            'complete': True}
