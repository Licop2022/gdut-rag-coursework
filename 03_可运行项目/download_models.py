"""从 ModelScope 的公开模型镜像下载，逐文件核对仓库给出的 SHA256。"""
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import urllib.parse
import time

ROOT=Path(__file__).resolve().parent
MODELS={'embedding':'BAAI/bge-small-zh-v1.5','reranker':'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1','generator':'Qwen/Qwen2.5-0.5B-Instruct'}

def download(role_repo):
    role,repo=role_repo
    print('Downloading',role,repo,flush=True)
    loc=ROOT/'models'/role
    loc.mkdir(parents=True,exist_ok=True)
    api=f'https://modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true'
    frozen_path=ROOT/'models'/'manifest.json'
    frozen=json.loads(frozen_path.read_text(encoding='utf-8')).get(role,{}) if frozen_path.exists() else {}
    if frozen.get('repo')==repo and frozen.get('repository_entries'):
        all_entries=frozen['repository_entries']
    else:
        metadata=json.load(urllib.request.urlopen(api,timeout=40))
        if not metadata.get('Success'): raise RuntimeError(f'无法读取仓库 {repo}')
        all_entries=metadata['Data']['Files']
    allowed={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.txt','vocab.json','merges.txt','model.safetensors','sentencepiece.bpe.model','README.md','LICENSE','LICENSE.txt'}
    entries=[f for f in all_entries if f['Type']=='blob' and f['Path'] in allowed]
    if not any(f['Path']=='model.safetensors' for f in entries): raise RuntimeError('仓库缺少 safetensors 权重，不回退到 pickle 权重')
    def fetch(entry):
        path=loc/entry['Path'];expected=entry['Sha256']
        if path.exists() and path.stat().st_size==entry['Size']:
            if hashlib.sha256(path.read_bytes()).hexdigest()==expected:return
        url=f'https://modelscope.cn/models/{repo}/resolve/{entry["Revision"]}/{urllib.parse.quote(entry["Path"])}'
        for attempt in range(3):
            try:
                digest=hashlib.sha256();downloaded=0;last_report=0
                req=urllib.request.Request(url,headers={'User-Agent':'RAG-Course-Project/1.0'})
                with urllib.request.urlopen(req,timeout=120) as response,path.with_suffix(path.suffix+'.part').open('wb') as out:
                    while True:
                        block=response.read(1024*1024)
                        if not block:break
                        out.write(block);digest.update(block);downloaded+=len(block)
                        if downloaded-last_report>100*1024*1024:
                            print(role,entry['Path'],round(downloaded/entry['Size']*100),'%',flush=True);last_report=downloaded
                if downloaded!=entry['Size'] or digest.hexdigest()!=expected: raise RuntimeError(f'校验失败 {role}/{entry["Path"]}')
                path.with_suffix(path.suffix+'.part').replace(path)
                print('Verified',role,entry['Path'],downloaded,flush=True)
                return
            except Exception:
                if attempt==2:raise
                time.sleep(2)
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,entries))
    files={}
    for f in loc.iterdir():
        if f.is_file():
            h=hashlib.sha256()
            with f.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
            files[f.name]={'bytes':f.stat().st_size,'sha256':h.hexdigest()}
    return role,{'repo':repo,'original_model_card':f'https://huggingface.co/{repo}','download_source':'ModelScope public mirror','files':files,'repository_entries':entries}

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool: manifest=dict(pool.map(download,MODELS.items()))
    (ROOT/'models'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('全部模型已下载，后续推理仅使用本地文件。')
