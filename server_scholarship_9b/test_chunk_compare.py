"""Comparison isolation and truthful diff annotations without loading GPU models."""
from pathlib import Path
import unittest

from chunk_compare import answer_diff, coverage, evidence_segments, run_comparison
from chunk_config import ChunkStore


class FakeRetriever:
    def __init__(self):
        self.chunks, self.vectors, self.index_fingerprint = ['active'], object(), 'active-index'

    def prepare_index(self, chunks):
        return chunks, object(), str(len(chunks))

    def use_index(self, prepared):
        self.chunks, self.vectors, self.index_fingerprint = prepared

    def retrieve(self, question):
        return {'baseline_context': self.chunks[:2], 'rerank_context': self.chunks[2:4],
                'retrieval_s': 0.01, 'rerank_s': 0.02}


class FakeGenerator:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def generate(self, question, contexts, use_adapter):
        self.calls.append((question, contexts, use_adapter))
        if self.fail and len(self.calls) == 2:
            raise RuntimeError('GPU failure')
        return {'answer': ''.join(c['text'] for c in contexts), 'generation_s': 1.0,
                'generated_tokens': 10, 'reached_token_limit': False}


class CompareTests(unittest.TestCase):
    def test_lossless_diff_and_identical(self):
        for a, b in [('条件：[A07-C01] 无不及格。', '条件：[A07-C02] 无违纪。'), ('', '新增'), ('相同', '相同')]:
            d = answer_diff(a, b)
            self.assertEqual(''.join(x['text'] for x in d['a']), a)
            self.assertEqual(''.join(x['text'] for x in d['b']), b)
            self.assertEqual(d['identical'], a == b)
            if a == b:
                self.assertTrue(all(not x['different'] for x in d['a']))

    def test_evidence_compares_source_spans_not_chunk_ids(self):
        a = {'id': 'A01-C01', 'article_id': 'A01', 'start': 0, 'end': 6, 'text': 'abcdef'}
        b = {'id': 'A01-C01', 'article_id': 'A01', 'start': 0, 'end': 3, 'text': 'abc'}
        self.assertEqual(evidence_segments(a, [b]), [{'text': 'abc', 'different': False}, {'text': 'def', 'different': True}])
        self.assertEqual(len(coverage([a, b])), 6)

    def test_comparison_restores_active_on_success_and_failure(self):
        store = ChunkStore(Path(__file__).resolve().parent)
        profiles = [{'chunk_size': 80, 'overlap': 10}, {'chunk_size': 380, 'overlap': 60}]
        for fail in [False, True]:
            retriever, generator = FakeRetriever(), FakeGenerator(fail)
            old = retriever.chunks, retriever.vectors, retriever.index_fingerprint
            if fail:
                with self.assertRaises(RuntimeError):
                    run_comparison(store, retriever, generator, '同一问题', profiles, 'rerank', False, {'top_k': 5})
            else:
                d = run_comparison(store, retriever, generator, '同一问题', profiles, 'rerank', False, {'top_k': 5})
                self.assertTrue(d['complete'])
                self.assertEqual([p['config'] for p in d['profiles']], profiles)
                self.assertNotEqual(d['profiles'][0]['chunk_count'], d['profiles'][1]['chunk_count'])
                for p, call in zip(d['profiles'], generator.calls):
                    self.assertEqual(call, ('同一问题', p['retrieval']['rerank_context'], False))
            self.assertIs(retriever.chunks, old[0])
            self.assertIs(retriever.vectors, old[1])
            self.assertEqual(retriever.index_fingerprint, old[2])

    def test_invalid_comparisons_do_not_generate(self):
        store, retriever, generator = ChunkStore(Path(__file__).resolve().parent), FakeRetriever(), FakeGenerator()
        for profiles, route in [([{'chunk_size': 80, 'overlap': 10}] * 2, 'rerank'),
                                ([{'chunk_size': 80, 'overlap': 10}, {'chunk_size': 80, 'overlap': 70}], 'rerank'),
                                ([], 'rerank'), ([None, None], 'rerank'), ([], 'wrong')]:
            with self.assertRaises(ValueError):
                run_comparison(store, retriever, generator, '问题', profiles, route, False, {})
        self.assertEqual(generator.calls, [])


if __name__ == '__main__':
    unittest.main()
