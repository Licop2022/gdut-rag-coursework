import json
import re
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'RAG课程作业交付'
assets=ROOT/'assets';assets.mkdir(exist_ok=True)
url='https://www.gdut.edu.cn/__local/3/C3/9F/801A80A5725DCD34C5E62C95E6B_E6F75E67_FEA5.jpg'
with urllib.request.urlopen(url,timeout=30) as r:(assets/'gdut-emblem-original.jpg').write_bytes(r.read())
page=urllib.request.urlopen('https://www.gdut.edu.cn/xxgk/xhxxxg.htm',timeout=30).read().decode('utf-8','replace')
imgs=re.findall(r'<img[^>]+src=[\'\"]([^\'\"]+)',page,re.I)
print(json.dumps([s for s in imgs if any(x in s.lower() for x in ['logo','name','校名'])],ensure_ascii=False))
(assets/'来源.txt').write_text('校徽来源：广东工业大学官方网站“校徽校训校歌”\nhttps://www.gdut.edu.cn/xxgk/xhxxxg.htm\n原图：'+url+'\n使用原始比例，不重绘校徽。本PPT为课程汇报自制设计，不是校方发布的官方模板。\n',encoding='utf-8')
