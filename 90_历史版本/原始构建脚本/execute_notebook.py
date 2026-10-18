"""用当前项目解释器执行交付 Notebook，不改用户的全局 Jupyter 配置。"""
import json
import os
import sys
from pathlib import Path
print('Stage 1: importing Notebook dependencies',flush=True)
import nbformat
print('Stage 2: nbformat imported',flush=True)
from nbclient import NotebookClient
print('Stage 3: nbclient imported',flush=True)
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

WORK=Path(__file__).resolve().parents[1]
ROOT=WORK/'RAG课程作业交付'
specdir=WORK/'.build'/'kernels'/'rag-project';specdir.mkdir(parents=True,exist_ok=True)
(specdir/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'RAG Project','language':'python','env':{'PYTHONUTF8':'1'}}),encoding='utf-8')
os.environ['JUPYTER_RUNTIME_DIR']=str(WORK/'.build'/'jupyter-runtime')
os.environ['IPYTHONDIR']=str(WORK/'.build'/'ipython')
ksm=KernelSpecManager(kernel_dirs=[str(specdir.parent)])
km=KernelManager(kernel_name='rag-project',kernel_spec_manager=ksm)
path=ROOT/'RAG课程作业.ipynb'
nb=nbformat.read(path,as_version=4)
print('Stage 4: Notebook loaded, starting local kernel',flush=True)
client=NotebookClient(nb,km=km,timeout=300,resources={'metadata':{'path':str(ROOT)}},allow_errors=False)
try:
    client.execute()
finally:
    if km.has_kernel:km.shutdown_kernel(now=True)
nbformat.write(nb,path)
print('Executed notebook:',len([c for c in nb.cells if c.cell_type=='code']),'code cells',flush=True)
