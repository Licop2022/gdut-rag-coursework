"""Verify transfer integrity against the saved SHA256 list; standard library only."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    manifest=json.loads((ROOT/'99_核验与交接/文件清单_SHA256.json').read_text(encoding='utf-8'))
    errors=[]
    for row in manifest['files']:
        p=ROOT/row['path']
        if not p.is_file():errors.append({'path':row['path'],'issue':'missing'})
        elif p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:
            errors.append({'path':row['path'],'issue':'changed'})
    print(json.dumps({'checked':len(manifest['files']),'errors':errors},ensure_ascii=False,indent=2))
    return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
