"""Build the GitHub Pages frontend from the same server UI, with authenticated API access."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
config=json.loads((ROOT/'public-config.json').read_text(encoding='utf-8'))
html=(ROOT/'demo.html').read_text(encoding='utf-8')
panel='''<section class="card" aria-label="服务器连接"><h2>连接 9B 实验室服务器</h2><p>输入部署者提供的访问密钥，即可实时提问及对比分块。密钥仅用于本标签页会话，请勿分享给无关人员。</p><div class="controls"><label for="accessKey">访问密钥<input id="accessKey" type="password" autocomplete="off" placeholder="粘贴访问密钥"></label><button id="connectBackend">连接服务器</button><button id="disconnectBackend" class="secondary">断开连接</button></div><p id="connectionStatus" role="status">尚未连接。模型运行在实验室服务器，需要服务器及 HTTPS 通道在线。</p><p><a href="https://github.com/Licop2022/gdut-rag-coursework" target="_blank" rel="noopener noreferrer">GitHub 项目源码与部署说明</a></p></section>'''
html=html.replace('<section class="card compare-panel"',panel+'\n<section class="card compare-panel"',1)
html=html.replace('<script>','<script>\nconst API_BASE='+json.dumps(config['api_base'])+';let gatewayKey="",connected=false;\n',1)
html=html.replace('el(id).disabled=value}', 'el(id).disabled=value||!connected;el("connectBackend").disabled=value&&connected;el("disconnectBackend").disabled=value&&connected}')
old=next(line for line in html.splitlines() if line.startswith('async function api('))
new='''async function api(path,body){let headers={'Authorization':'Bearer '+gatewayKey};if(body!==undefined)headers['Content-Type']='application/json';let r;try{r=await fetch(API_BASE+path,{method:body===undefined?'GET':'POST',headers,...(body===undefined?{}:{body:JSON.stringify(body)}),credentials:'omit',cache:'no-store'})}catch(e){throw Error('无法连接服务器，请确认服务器和 HTTPS 通道在线')}let d;try{d=await r.json()}catch(e){throw Error('服务器通道暂时不可用，请稍后重试')}if(!r.ok){if(r.status===401){connected=false;sessionStorage.removeItem('gdut9b-access-key');el('connectionStatus').textContent='密钥失效，请重新连接';}throw Error(d.error||'请求失败')}return d}'''
html=html.replace(old,new)
old="busy(true);api('/api/chunks').then(d=>renderChunks(d,true)).catch(e=>el('chunkStatus').textContent=e.message).finally(()=>busy(false));"
new='''async function connectBackend(key){gatewayKey=key.trim();if(!gatewayKey){el('connectionStatus').textContent='请先输入访问密钥';return}busy(true);el('connectBackend').disabled=true;el('connectionStatus').textContent='正在连接服务器…';try{let d=await api('/api/chunks');connected=true;renderChunks(d,true);sessionStorage.setItem('gdut9b-access-key',gatewayKey);el('connectionStatus').textContent='已连接 · Qwen3.5-9B · 可以提问、调整 chunk 或进行 A/B 对比。'}catch(e){connected=false;el('connectionStatus').textContent=e.message}finally{el('accessKey').value='';busy(false);el('connectBackend').disabled=false}}el('connectBackend').onclick=()=>connectBackend(el('accessKey').value);el('accessKey').onkeydown=e=>{if(e.key==='Enter')connectBackend(el('accessKey').value)};el('disconnectBackend').onclick=()=>{sessionStorage.removeItem('gdut9b-access-key');gatewayKey='';connected=false;busy(false);el('connectionStatus').textContent='已断开连接。'};busy(true);if(sessionStorage.getItem('gdut9b-access-key'))connectBackend(sessionStorage.getItem('gdut9b-access-key'));'''
if old not in html: raise RuntimeError('UI initialization changed; review the public build transformation')
html=html.replace(old,new)
html=html.replace('<title>广工研究生奖学金问答</title>','<title>广工研究生奖学金问答 · 9B 在线实验</title>')
docs=ROOT.parent/'docs'
docs.mkdir(exist_ok=True)
(docs/'index.html').write_text(html,encoding='utf-8')
(docs/'.nojekyll').write_text('',encoding='utf-8')
(docs/'public-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('Public frontend built; no model weights or credentials included.')
