"""Chunk coverage, version isolation, and persistence without GPU dependencies."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chunk_config import ChunkStore, build_chunks, read_jsonl

ROOT = Path(__file__).resolve().parent


class ChunkConfigTests(unittest.TestCase):
    def test_original_matches_and_coverage(self):
        articles = read_jsonl(ROOT / "data/articles.jsonl")
        self.assertEqual(build_chunks(articles, 380, 60), read_jsonl(ROOT / "data/chunks.jsonl"))
        for size, overlap in [(80, 0), (200, 40), (800, 400)]:
            chunks = build_chunks(articles, size, overlap)
            self.assertEqual(len(chunks), len({c['id'] for c in chunks}))
            for article in articles:
                selected = [c for c in chunks if c['article_id'] == article['id']]
                coverage = set()
                for c in selected:
                    self.assertEqual(c['text'], article['text'][c['start']:c['end']])
                    self.assertEqual(c['source_pages'], article['source_pages'])
                    coverage.update(range(c['start'], c['end']))
                self.assertEqual(coverage, set(range(len(article['text']))))

    def test_validation(self):
        for size, overlap in [(0, 0), (801, 0), (True, 0), (200, -1), (200, 101), (200, 1.5)]:
            with self.assertRaises(ValueError):
                build_chunks([], size, overlap)

    def test_commit_reload_reset_and_atomic_failure(self):
        (ROOT / 'cache').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'cache', prefix='chunk-test-') as folder:
            root = Path(folder)
            assert root.resolve().is_relative_to((ROOT / 'cache').resolve())
            (root / 'data').mkdir()
            for name in ['articles.jsonl', 'chunks.jsonl']:
                (root / 'data' / name).write_bytes((ROOT / 'data' / name).read_bytes())
            originals = (root / 'data/chunks.jsonl').read_bytes()
            store = ChunkStore(root)
            self.assertEqual(store.active()['config']['version'], 'original')
            preview = store.preview(200, 40)
            self.assertFalse(store.pointer.exists())
            committed = store.commit(preview)
            self.assertEqual(ChunkStore(root).active(), committed)
            with patch('chunk_config.os.replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    store.commit(store.preview(160, 20))
            self.assertEqual(store.active(), committed)
            store.commit(store.original())
            self.assertEqual(store.active()['config']['version'], 'original')
            self.assertEqual((root / 'data/chunks.jsonl').read_bytes(), originals)


if __name__ == '__main__':
    unittest.main()
