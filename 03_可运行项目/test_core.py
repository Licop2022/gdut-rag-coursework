"""检查边界、索引失效和对照实验所需的不变量，不评价模型好坏。"""
import unittest
from rag_engine import split_text,corpus_chunks,fingerprint,CONFIG

class TestCore(unittest.TestCase):
    def test_split_boundaries_and_coverage(self):
        for n in [0,1,179,180,181,500]:
            text=''.join(chr(0x4e00+i) for i in range(n));chunks=list(split_text(text,180,36))
            covered=set()
            for start,end,part in chunks:
                self.assertEqual(part,text[start:end]);self.assertLessEqual(len(part),180);covered.update(range(start,end))
            self.assertEqual(covered,set(range(n)))
            self.assertEqual(len({start for start,_,_ in chunks}),len(chunks))
    def test_invalid_overlap(self):
        for size,overlap in [(0,0),(10,-1),(10,10),(10,11)]:
            with self.assertRaises(ValueError):list(split_text('正文',size,overlap))
    def test_corpus_and_cache_invalidation(self):
        chunks=corpus_chunks();self.assertEqual(len({c['id'] for c in chunks}),len(chunks));self.assertEqual(len({c['doc_id'] for c in chunks}),20)
        before=fingerprint(chunks,CONFIG);changed=[dict(c) for c in chunks];changed[0]['text']+='更新'
        self.assertNotEqual(before,fingerprint(changed,CONFIG));self.assertNotEqual(before,fingerprint(chunks,dict(CONFIG,overlap=0)))

if __name__=='__main__':unittest.main()
