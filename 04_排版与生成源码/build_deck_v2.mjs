import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
const SOURCE=path.dirname(fileURLToPath(import.meta.url));
const WORK=path.dirname(SOURCE);
const ROOT=path.join(WORK,'01_汇报材料');
const PROJECT=path.join(WORK,'03_可运行项目');
const BUILD=path.join(SOURCE,'.build');
const settings=JSON.parse(await fs.readFile(path.join(SOURCE,'runtime-settings.json'),'utf8'));
const SKILL=process.env.PRESENTATIONS_SKILL_DIR||settings.presentationsSkillDir;
process.env.RUNTIME_NODE_MODULES=process.env.RUNTIME_NODE_MODULES||settings.nodeModules;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(process.env.RUNTIME_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {applyPresentationChartFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const requireMath=createRequire(path.join(SOURCE,'math-deps/package.json'));
const {mathjax}=requireMath('mathjax-full/js/mathjax.js');
const {TeX}=requireMath('mathjax-full/js/input/tex.js');
const {SVG}=requireMath('mathjax-full/js/output/svg.js');
const {liteAdaptor}=requireMath('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler}=requireMath('mathjax-full/js/handlers/html.js');
const {AllPackages}=requireMath('mathjax-full/js/input/tex/AllPackages.js');
const adaptor=liteAdaptor();RegisterHTMLHandler(adaptor);
const mathDocument=mathjax.document('',{InputJax:new TeX({packages:AllPackages}),OutputJax:new SVG({fontCache:'none'})});
const S=JSON.parse(await fs.readFile(path.join(PROJECT,'results/summary.json'),'utf8'));
const RAW=JSON.parse(await fs.readFile(path.join(PROJECT,'results/raw_results.json'),'utf8'));
const REVIEW=JSON.parse(await fs.readFile(path.join(PROJECT,'results/answer_review.json'),'utf8'));
const PROBES=JSON.parse(await fs.readFile(path.join(PROJECT,'results/supplementary_ranking_probes.json'),'utf8'));
const demo=RAW.find(r=>r.id==='Q10');
const rank=PROBES.find(r=>r.id==='S07');
const logo=await fs.readFile(path.join(ROOT,'assets/gdut-wordmark-original.png'));
const campus=await fs.readFile(path.join(ROOT,'assets/gdut-campus-2025-original.jpg'));
const P=Presentation.create({slideSize:{width:1280,height:720}});
const F='Microsoft YaHei';
const C={ink:'#24262B',muted:'#64676E',red:'#C30D23',redDark:'#A0091E',rose:'#F9EFF0',paper:'#FCFBF8',white:'#FFFFFF',line:'#D8DADD',base:'#6C8090',green:'#246F58'};
const refs={rag:'https://arxiv.org/abs/2005.11401',bge:'https://huggingface.co/BAAI/bge-small-zh-v1.5',ce:'https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',qwen:'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct',sbert:'https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html'};
const LATEX={
  cosine:String.raw`s(q,d_i)=\frac{\mathbf{e}_q^{\mathsf T}\mathbf{e}_i}{\lVert\mathbf{e}_q\rVert_2\,\lVert\mathbf{e}_i\rVert_2}`,
  normalized:String.raw`s(q,d_i)=\widehat{\mathbf e}_q^{\mathsf T}\widehat{\mathbf e}_i`,
  rerank:String.raw`r_i=f_{\theta}\!\left([q\,;\,d_i]\right)`,
  hit:String.raw`\operatorname{Hit@3}=\frac{1}{N}\sum_{j=1}^{N}\mathbf{1}\!\left[\rho_j\leq3\right]`,
  mrr:String.raw`\operatorname{MRR@3}=\frac{1}{N}\sum_{j=1}^{N}\begin{cases}\dfrac{1}{\rho_j},&\rho_j\leq3,\\[3pt]0,&\rho_j>3.\end{cases}`,
  vectors:String.raw`\mathbf e_q=E(q),\qquad \mathbf e_i=E(d_i)`
};
const mathCache={};
await fs.mkdir(path.join(ROOT,'公式'),{recursive:true});
for(const [key,tex] of Object.entries(LATEX)){
  const node=mathDocument.convert(tex,{display:true});
  let svg=adaptor.outerHTML(adaptor.firstChild(node));
  if(svg.includes('data-mjx-error')||svg.includes('<merror'))throw Error('LaTeX failed: '+key);
  const box=svg.match(/viewBox="([^"]+)"/)[1].split(/\s+/).map(Number);
  const exWidth=parseFloat(svg.match(/width="([\d.]+)ex"/)[1]);
  svg=svg.replace(/ style="[^"]*"/g,'').replace(/currentColor/g,C.ink)
    .replace(/width="[\d.]+ex"/,`width="${Math.ceil(box[2]/30)}"`)
    .replace(/height="[\d.]+ex"/,`height="${Math.ceil(box[3]/30)}"`);
  mathCache[key]={svg,ratio:box[3]/box[2],exWidth};
  await fs.writeFile(path.join(ROOT,'公式',key+'.svg'),svg);
}
await fs.writeFile(path.join(ROOT,'公式/公式源码.tex'),String.raw`\documentclass{article}
\usepackage{amsmath,amssymb}
\begin{document}
`+'\n'+Object.entries(LATEX).map(([k,t])=>`% ${k}\n\\[\n${t}\n\\]`).join('\n\n')+'\n\\end{document}\n');
await fs.writeFile(path.join(ROOT,'公式/latex-manifest.json'),JSON.stringify(LATEX,null,2));

function text(s,str,x,y,w,h,size=28,color=C.ink,bold=false,align='left'){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=str;sh.text.insets=0;sh.text.style={typeface:F,fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square'};return sh;
}
function rich(s,runs,x,y,w,h,size=26){
  const sh=text(s,'',x,y,w,h,size);
  sh.text=[[...runs.map(r=>({run:r.t,style:{typeface:F,fontSize:`${size}px`,bold:r.b||false,color:r.c||C.ink}}))]];
  return sh;
}
function note(s,str){s.speakerNotes.text=str;}
function slide(section,title,sub=''){
  const s=P.slides.add();s.background.fill=C.paper;
  text(s,section,56,29,1000,35,26,C.red,true);
  text(s,title,56,76,1168,66,42,C.ink,true);
  if(sub)text(s,sub,58,147,1164,58,26,C.muted);
  return s;
}
function formula(s,key,x,y,maxWidth,fontPx=34){
  const m=mathCache[key];const w=Math.min(maxWidth,m.exWidth*fontPx/2);const h=w*m.ratio;
  s.images.add({svg:m.svg,alt:'LaTeX: '+LATEX[key],fit:'contain',position:{left:x,top:y,width:w,height:h}});
  return h;
}
function img(s,bytes,mime,x,y,w,h,alt){s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:mime,alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function arrow(s,x,y,w=35,fill=C.line){s.shapes.add({geometry:'rightArrow',position:{left:x,top:y,width:w,height:17},fill,line:{fill:'none',width:0}});}
function node(s,title,subtitle,x,y,w=175,active=false){
  const shape=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:98},fill:active?C.rose:C.white,line:{fill:active?C.red:C.line,width:active?1.8:1}});
  shape.text='';text(s,title,x+12,y+16,w-24,37,27,active?C.red:C.ink,true,'center');
  text(s,subtitle,x+8,y+59,w-16,35,24,C.muted,false,'center');return shape;
}
function nativeTable(s,values,x,y,width,height,widths,fontSize=23){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width,height,columnWidths:widths,values});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?C.red:(r%2===0?'#F6F2EE':C.white);cell.text.style={typeface:F,fontSize,color:r===0?C.white:C.ink,bold:r===0};
  }
  t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({margins:{top:10,bottom:8,left:16,right:12},anchor:'center'});return t;
}

// 01 封面：学校识别、课题和汇报者，避免在封面塞入实验细节。
{
  const s=P.slides.add();s.background.fill=C.paper;
  img(s,logo,'image/png',56,38,360,82.08,'广东工业大学官方校徽校名');
  text(s,'大数据与人工智能',56,173,620,35,23,C.muted);
  text(s,'课程资料问答\nRAG 重排序实验',56,232,660,175,61,C.red,true);
  text(s,'从候选片段排序，到最终回答核验',59,446,620,52,29,C.ink);
  text(s,'四人小组课程汇报',59,559,600,32,23,C.muted);
  text(s,'成员甲 / 成员乙 / 成员丙 / 成员丁',59,605,650,36,24,C.ink);
  img(s,campus,'image/jpeg',755,219,470,313.333,'广东工业大学官方图库校园照片，保留完整原图与水印');
  text(s,'2026 年 10 月 22 日',755,576,470,40,26,C.muted,false,'right');
  note(s,`成员甲，10秒：我们做的是课程资料问答中的重排序实验。今天沿着一个问题展开：找到相关资料以后，增加重排能否让证据和回答都更可靠？\n校园照片来源：https://photo.gdut.edu.cn/info/1026/2675.htm ，原图：https://photo.gdut.edu.cn/__local/E/F1/23/A1D38E3525FFD9567769896F424_087ABE40_AF8E31.jpg 。校徽校名：https://www.gdut.edu.cn/images2020/logo.png 。本设计为课程汇报自制版，不是校方官方模板。`);
}
// 02 听众先理解问题，再理解我们打算怎样回答这个问题。
{
  const s=slide('01 研究问题','加入重排序，究竟改善了哪一步？','应用场景：模型依据课程资料回答问题，并给出可核对的来源。');
  text(s,'我们比较同一批候选，回答两个问题',58,215,1160,53,32,C.red,true);
  text(s,'证据层',58,312,230,44,30,C.ink,true);
  text(s,'更相关的片段，是否排到了前面？',305,312,900,52,32,C.ink);
  text(s,'答案层',58,412,230,44,30,C.ink,true);
  text(s,'模型是否正确理解并使用了这些证据？',305,412,900,52,32,C.ink);
  text(s,'汇报路径',58,550,230,35,23,C.muted);
  text(s,'系统与原理     对照实验     排序案例     回答核验',305,549,900,46,26,C.muted);
  note(s,`成员甲，25秒：我们先区分证据排序和答案生成。重排序直接改变的是候选片段的顺序，最终回答还依赖生成模型。因此不能只看一个检索指标就宣布系统更好了。我们先讲方法，再给出同题对照、排序案例和回答核验。来源：${refs.rag}。`);
}
// 03 一张系统图，明确离线建库与在线推理的关系。
{
  const s=slide('02 方法','RAG 系统：建库在前，问答在后');
  text(s,'离线建库',58,172,220,34,25,C.muted,true);
  node(s,'课程资料','20 篇自编学习资料',250,166,235);arrow(s,504,207,50);
  node(s,'切分并编码','180 字符 / 重叠 36',575,166,245);arrow(s,839,207,50);
  node(s,'向量索引','37 个片段，512 维',910,166,306);
  text(s,'在线问答',58,329,220,35,25,C.muted,true);
  const X=[58,298,538,778,1018];
  const items=[['问题编码','BGE 编码'],['向量召回','前 10 个候选'],['候选重排','Cross-Encoder'],['选择上下文','保留 3 个片段'],['生成回答','Qwen2.5-0.5B']];
  items.forEach((a,i)=>{node(s,a[0],a[1],X[i],404,198,i===2);if(i<4)arrow(s,X[i]+207,445,27,i===1||i===2?C.red:C.line);});
  text(s,'本次研究对象',538,535,198,36,23,C.red,true,'center');
  text(s,'基础组跳过重排，其他设置保持一致。',58,604,1160,47,28,C.muted);
  note(s,`成员乙，25秒：离线把资料切分，用BGE编码为向量，并保存片段来源。在线先编码问题，召回十个候选，重排组增加红色这一环节，两组最后都只给生成器三个片段。向量检索用NumPy精确扫描，本次没有部署Milvus。来源：${refs.bge}；${refs.sbert}。`);
}
// 04 按系统步骤介绍切分与向量化，公式独立排版并解释符号。
{
  const s=slide('02 方法','第一步：把资料切成可检索的语义片段');
  text(s,'切分决定证据是否完整',58,176,550,43,30,C.red,true);
  text(s,'180',58,242,230,73,58,C.ink,true);text(s,'字符 / 片段',245,270,280,39,24,C.muted);
  text(s,'36',58,337,230,73,58,C.ink,true);text(s,'字符相邻重叠',245,363,300,39,24,C.muted);
  text(s,'片段太短：条件与结论可能分离\n片段太长：无关信息增加\n重叠：缓解边界截断，也带来冗余',58,450,555,137,26,C.ink);
  text(s,'向量表示决定怎样比较相关性',666,176,555,44,30,C.red,true);
  formula(s,'cosine',666,253,550,32);
  text(s,'q：问题     dᵢ：第 i 个片段\ne：BGE 编码后的向量',666,366,550,89,25,C.muted);
  text(s,'本项目先做 L2 归一化',666,466,555,36,24,C.ink,true);
  formula(s,'normalized',666,524,550,36);
  note(s,`成员乙，40秒：切分参数是一百八十字符，重叠三十六字符。太短会切断条件，太长会混入干扰。编码后比较的是向量方向，也就是余弦相似度，公式中的q是问题，d_i是片段，e是BGE向量。我们先归一化，所以计算时直接点积即可。这里的相关分数不是答案正确概率。LaTeX源码：${LATEX.cosine}\n${LATEX.normalized}\n来源：${refs.bge}`);
}
// 05 用输入组织方式解释重排，不再堆一个五行对照大表。
{
  const s=slide('02 方法','第二步：召回候选，再联合判断相关性');
  text(s,'向量召回',58,176,520,44,32,C.base,true);
  text(s,'Bi-Encoder',58,224,520,35,22,C.muted);
  text(s,'问题 q',58,290,165,45,28,C.ink,true);arrow(s,225,304,40,C.base);
  text(s,'BGE 编码',285,290,200,45,28,C.base,true);
  text(s,'片段 dᵢ',58,365,165,45,28,C.ink,true);arrow(s,225,379,40,C.base);
  text(s,'BGE 编码',285,365,200,45,28,C.base,true);
  formula(s,'vectors',58,441,525,32);
  text(s,'文档向量提前计算，适合从全库找候选',58,515,540,81,26,C.ink);
  text(s,'候选精排',674,176,540,44,32,C.red,true);
  text(s,'Cross-Encoder',674,224,540,35,22,C.muted);
  node(s,'问题 + 候选片段','作为文本对联合输入',674,285,334,true);arrow(s,1024,325,35,C.red);
  text(s,'相关性\n评分',1090,292,126,87,27,C.red,true,'center');
  formula(s,'rerank',674,421,540,36);
  text(s,'逐对计算更细的相关性，只处理召回候选',674,515,540,81,26,C.ink);
  text(s,'证据没有进入候选集，重排就无法将它补回。',58,624,1160,45,28,C.muted);
  note(s,`成员丙，35秒：两种模型的区别在于如何看输入。Bi-Encoder分别编码问题和片段，便于先缓存文档向量。Cross-Encoder把问题与候选联合输入，逐对评分，所以我们只精排十个候选。公式f_theta是训练好的文本对打分模型。它只能改变已有候选，不能补回漏召回的证据。LaTeX：${LATEX.vectors}\n${LATEX.rerank}\n来源：${refs.ce}；${refs.sbert}`);
}
// 06 先明确实验控制，再读结果。
{
  const s=slide('03 实验','对照设计：两组只相差一道重排序');
  text(s,'同一数据与同一问题',58,176,1160,45,30,C.red,true);
  text(s,'20 篇自编资料 / 37 个片段',58,238,1160,44,29,C.ink);
  text(s,'12 道固定题：10 道有资料依据，2 道资料外问题单独检查',58,292,1160,44,27,C.muted);
  text(s,'共享每题相同的 10 个候选',58,371,1160,47,30,C.ink,true,'center');
  text(s,'↓',280,425,180,50,32,C.base,true,'center');
  text(s,'↓',820,425,180,50,32,C.red,true,'center');
  text(s,'基础 RAG',120,490,500,45,30,C.base,true,'center');
  text(s,'按向量原序选前 3 个',120,548,500,48,28,C.ink,false,'center');
  text(s,'加入 Rerank',660,490,500,45,30,C.red,true,'center');
  text(s,'按精排分数选前 3 个',660,548,500,48,28,C.ink,false,'center');
  text(s,'相同生成器、相同提示词、相同上下文数量、贪心解码',58,632,1160,45,28,C.muted,false,'center');
  note(s,'成员丁，20秒：我们用二十篇自编资料、十二道固定题。两组每题共享同一批十个候选，最后上下文都是三个，生成设置相同。资料外题不参与检索命中率，而单独看拒答。参考答案只用于评价。该题集是教学内部测试，不是外部盲测。');
}
// 07 有真实原文与清楚的名次变化，避免只能看懂编号。
{
  const s=slide('03 实验','一个重排案例：关键片段从第 4 名升至第 1 名');
  text(s,'问题：搜到的材料来自相关文件，为什么仍不等于能答完整？',58,166,1160,72,28,C.ink,true);
  text(s,'向量召回顺序',58,273,470,40,28,C.base,true);
  text(s,'Cross-Encoder 重排后',753,273,470,40,28,C.red,true);
  for(let i=0;i<4;i++){
    const a=rank.candidates[i],b=rank.reranked_candidates[i];
    const y=335+i*55;
    text(s,String(i+1).padStart(2,'0'),58,y,50,38,24,a.id==='D08-C02'?C.red:C.muted,true);
    text(s,a.title.slice(4),124,y,430,42,25,a.id==='D08-C02'?C.red:C.ink,a.id==='D08-C02');
    text(s,String(i+1).padStart(2,'0'),753,y,50,38,24,b.id==='D08-C02'?C.red:C.muted,true);
    text(s,b.title.slice(4),819,y,399,42,25,b.id==='D08-C02'?C.red:C.ink,b.id==='D08-C02');
  }
  text(s,'4 → 1',560,398,175,68,45,C.red,true,'center');
  text(s,'关键原文：“只找到一个相关片段，不代表覆盖了全部必要事实。”',58,581,1160,43,27,C.redDark,true);
  text(s,'补充案例 S07：仅展示排序机制，不计入固定题集统计。',58,639,1160,42,26,C.muted);
  note(s,`成员丙，30秒：先看向量原序，讨论证据完整性的片段只排第四。重排后，它到了第一，原文明确说明相关片段不等于覆盖全部事实。这个例子证明排序确实发生了变化。它来自额外的口语化探索，只展示机制，不与固定十二题混算。片段ID为D08-C02，完整候选及分数见results/supplementary_ranking_probes.json。`);
}
// 08 用一张图同时回答两层问题，保留实际零提升结果。
{
  const s=slide('03 实验','找到相关文档，仍可能生成错误回答');
  const chart=s.charts.add('bar',{
    position:{left:48,top:169,width:770,height:400},title:'10 道有依据题：同题对照',titleTextStyle:{typeface:F,fontSize:24,fill:C.ink},
    categories:['相关文档命中\nHit@3','回答初评满分\n3/10'],
    series:[{name:'基础 RAG',values:[S.baseline.hit3,REVIEW.answerable_summary.baseline.fully_correct_count/S.answerable_questions],fill:C.base},{name:'加入重排',values:[S.rerank.hit3,REVIEW.answerable_summary.rerank.fully_correct_count/S.answerable_questions],fill:C.red}],
    hasLegend:true,legend:{position:'bottom',overlay:false,textStyle:{typeface:F,fontSize:22,fill:C.ink}},
    barOptions:{direction:'column',grouping:'clustered',gapWidth:110},
    yAxis:{min:0,max:1.15,majorUnit:0.25,numberFormatCode:'0%',majorGridlines:{fill:'#E4E3DF',width:1,style:'solid'},line:{fill:'none',width:0},textStyle:{typeface:F,fontSize:19,fill:C.muted}},
    xAxis:{line:{fill:C.line,width:1},textStyle:{typeface:F,fontSize:22,fill:C.ink}},
    dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0%',textStyle:{typeface:F,fontSize:25,bold:true,fill:C.ink}},
    chartFill:'none',plotAreaFill:'none',chartLine:{fill:'none',width:0}
  });
  applyPresentationChartFont(chart,{fontFamily:F});
  text(s,'检索已达本题集上限',879,219,336,84,32,C.ink,true);
  text(s,'两组文档级指标相同，\n结论限于当前题集。',879,321,336,105,26,C.muted);
  text(s,`${S.mean_rerank_s.toFixed(3)} s`,879,463,336,65,46,C.red,true);
  text(s,'每题额外重排平均耗时',879,538,336,43,26,C.muted);
  note(s,`成员丁，25秒：图左是检索，两个Hit@3都是百分之百。图右是回答，初评满分都只有三题。检索指标在这个简单题集上已达上限，但生成模型仍会犯错。重排步骤平均增加约${S.mean_rerank_s.toFixed(2)}秒。初评由助手阅读完成，需要组员复核，不能称作独立盲评。主实验原始数值见results/summary.json，回答见results/answer_review.json。`);
}
// 09 现场演示的落脚点是核验答案，不在台上读一屏代码。
{
  const s=slide('03 实验','现场核验：同维度，为什么还要重新建库？','问题 Q10：修改 Embedding 模型后，即使向量维度没变，为什么仍要重建？');
  text(s,'基础 RAG 回答节选',58,232,550,42,28,C.base,true);
  text(s,'“需要重新建立库以确保\n所有相关组件都已正确配置和更新。”',58,302,548,136,30,C.ink);
  text(s,'没有说清“为什么不兼容”',58,470,548,48,25,C.muted);
  text(s,'重排后回答节选',676,232,550,42,28,C.red,true);
  rich(s,[{t:'“由于'},{t:'语义空间可能已经变化',c:C.red,b:true},{t:'，\n因此需要重新建立索引\n以确保其兼容性。”'}],676,302,548,145,30);
  text(s,'与原文 D15-C01 的关键理由一致',676,470,548,48,25,C.green,true);
  text(s,'核验标准：答案中的理由，必须能在引用原文中找到。',58,571,1160,75,30,C.ink,true);
  note(s,`成员丙，45秒，包含切屏：打开已预热Notebook的Q10单元格，运行一次查询。两组都有D15-C01，前两名不变，第三个上下文改变。基础回答泛泛说配置更新，重排后明确说到语义空间变化，随后打开D15-C01核对。这个个例只说明上下文变化可能影响生成，不能推出普遍收益。若现场等待或失败，使用保存的实验结果预览并说明。此页使用原始回答的节选，未改写模型原意。`);
}
// 10 回到开头提出的两层问题，每项结论都对应前面的证据。
{
  const s=slide('04 结论','重排序改变了证据优先级，可靠回答仍需核验');
  text(s,'01',58,197,78,54,38,C.red,true);text(s,'排序层：确实能够改变候选顺序',173,197,1042,51,31,C.ink,true);
  text(s,'补充案例中，第 4 名的关键片段进入第 1 名。',173,259,1042,49,25,C.muted);
  text(s,'02',58,347,78,54,38,C.red,true);text(s,'整体层：当前题集没有观察到指标提升',173,347,1042,51,31,C.ink,true);
  text(s,'检索指标均已达上限，回答初评满分题数仍为 3/10。',173,409,1042,49,25,C.muted);
  text(s,'03',58,497,78,54,38,C.red,true);text(s,'下一步：换独立课件题集，重点核验生成',173,497,1042,51,31,C.ink,true);
  text(s,'当前是自编小样本与 0.5B 模型，结论限定于本次实验。',173,559,1042,80,27,C.muted);
  note(s,'成员丁，15秒：回到开头的问题，排序层可以改变优先级，但整体指标在这个小题集上没有提升，生成仍有明显错误。下一步应先换真实课件的独立题集，再做双人核验和重复实验。到这里结束主讲，后两页只用于备答。');
}
// 11 备答公式：所有数学表达式都从 LaTeX 生成矢量。
{
  const s=slide('备答 01 指标','检索指标怎样计算？');
  text(s,'Hit@3：前三名是否至少命中一个相关片段',58,181,1160,43,28,C.red,true);
  formula(s,'hit',58,247,1140,35);
  text(s,'MRR@3：首个相关结果越靠前，得分越高',58,376,1160,43,28,C.red,true);
  formula(s,'mrr',58,437,1140,32);
  text(s,'N = 10；ρⱼ 是第 j 题首个相关结果的排名，未召回时为 ∞。',58,597,1160,43,27,C.muted);
  text(s,'相关性按文档编号判断；资料外题单独检查。',58,643,1160,42,27,C.muted);
  note(s,`备答，不计入5分钟主讲。两组Hit@1、Hit@3均为1，MRR@3均为1。定义基于文档级gold_docs，并不保证片段覆盖所有必要证据。LaTeX源：${LATEX.hit}\n${LATEX.mrr}`);
}
// 12 复现与分工的细节放在备答，主讲不被模型版本和文件名打断。
{
  const s=slide('备答 02 复现与分工','模型、材料与四人职责');
  nativeTable(s,[['成员','负责模块','主要交付'],['甲','研究问题与系统统筹','资料范围、流程图、材料整合'],['乙','切分与向量检索','BGE 编码、向量索引、来源定位'],['丙','重排序与现场演示','Cross-Encoder、Notebook、查询演示'],['丁','实验设计与评价','固定题集、逐题核验、结果分析']],58,172,1164,262,[130,355,679],23);
  text(s,'本地模型',58,466,210,39,25,C.red,true);
  text(s,'BGE-small-zh-v1.5 / mmarco-mMiniLMv2 / Qwen2.5-0.5B',271,466,943,70,24,C.ink);
  text(s,'完整材料',58,553,210,39,25,C.red,true);
  text(s,'Notebook、逐题原始结果、实验报告、LaTeX 公式源码',271,553,943,70,24,C.ink);
  note(s,`备答。完整参数与软件版本见results/summary.json，模型来源见models/manifest.json，原始回答见results/raw_results.json。参考文献：${Object.values(refs).join('；')}。四人分工为建议安排，提交前用真实姓名并核实实际贡献。`);
}

await fs.mkdir(path.join(BUILD,'slides'),{recursive:true});
for(let i=0;i<P.slides.items.length;i++){
  const png=await P.export({slide:P.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(BUILD,'slides',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const draft=path.join(BUILD,'candidate-v2.pptx');
await (await PresentationFile.exportPptx(P)).save(draft);
console.log('Draft exported:',draft,'; next run finalize.mjs');
