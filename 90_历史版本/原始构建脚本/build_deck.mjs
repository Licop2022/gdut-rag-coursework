import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const workspaceDir=path.resolve('.');
const root=path.join(workspaceDir,'RAG课程作业交付');
const build=path.join(workspaceDir,'.build');
const SKILL_DIR='<USER_HOME>/.codex/plugins/cache/openai-primary-runtime/presentations/26.1009.11318/skills/presentations';
const RUNTIME_PYTHON='<USER_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='<USER_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {Presentation,PresentationFile}=await import('file:///<USER_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs');
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')).href);
const summary=JSON.parse(await fs.readFile(path.join(root,'results/summary.json'),'utf8'));
const results=JSON.parse(await fs.readFile(path.join(root,'results/raw_results.json'),'utf8'));
const review=JSON.parse(await fs.readFile(path.join(root,'results/answer_review.json'),'utf8'));
const evidence=JSON.parse(await fs.readFile(path.join(root,'results/presentation_evidence.json'),'utf8'));
const probes=JSON.parse(await fs.readFile(path.join(root,'results/supplementary_ranking_probes.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const font='Microsoft YaHei';
const C={navy:'#262626',teal:'#C30D23',muted:'#616161',light:'#FAEEEE',white:'#FFFFFF',paper:'#FFFFFF',orange:'#9A5D00'};
const logoBytes=await fs.readFile(path.join(root,'assets/gdut-wordmark-original.png'));
const sources={rag:'https://arxiv.org/abs/2005.11401',bge:'https://huggingface.co/BAAI/bge-small-zh-v1.5',ce:'https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',qwen:'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct',sbert:'https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html'};
function txt(s,text,x,y,w,h,size=28,color=C.navy,bold=false){
  const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  a.text=text;a.text.insets=0;a.text.style={typeface:font,fontSize:size,color,bold,verticalAlignment:'middle'};return a;
}
function slide(title,notes=''){
  const s=p.slides.add();s.background.fill=C.paper;
  txt(s,title,64,42,1152,82,44,C.navy,true);
  txt(s,String(p.slides.items.length).padStart(2,'0'),1160,670,56,26,17,C.muted);
  txt(s,'广东工业大学',64,670,300,26,17,C.teal);
  s.speakerNotes.text=notes;return s;
}
function table(s,values,x,y,width,height,widths){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width,height,values,columnWidths:widths});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?C.teal:(r%2===0?'#FAF1F2':C.white);
    cell.text.style={typeface:font,fontSize:23,color:r===0?C.white:C.navy,bold:r===0};
  }
  t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({margins:{left:16,right:12,top:10,bottom:10},anchor:'center'});
  t.borders.assign({style:'solid',fill:C.paper,width:2});return t;
}
function diagram(s,labels,y,widths){
  let x=64;
  labels.forEach((label,i)=>{
    let w=widths[i];const box=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:94},fill:C.light,line:{fill:C.teal,width:1}});
    box.text=label;box.text.insets=10;box.text.style={typeface:font,fontSize:25,color:C.navy,bold:true,alignment:'center',verticalAlignment:'middle'};
    x+=w;
    if(i<labels.length-1){s.shapes.add({geometry:'rightArrow',position:{left:x+8,top:y+36,width:30,height:22},fill:C.teal,line:{fill:'none',width:0}});x+=46;}
  });
}
const pct=x=>(x*100).toFixed(0)+'%';

// 1. 简洁封面
{
const s=p.slides.add();s.background.fill=C.white;
s.images.add({blob:logoBytes.buffer.slice(logoBytes.byteOffset,logoBytes.byteOffset+logoBytes.byteLength),contentType:'image/png',alt:'广东工业大学官方横版校徽与校名',fit:'contain',position:{left:64,top:45,width:480,height:109.44}});
txt(s,'大数据与人工智能课程汇报',810,76,406,48,24,C.muted);
txt(s,'课程资料问答助手',64,235,1152,104,68,C.teal,true);
txt(s,'RAG 检索与重排序效果对比',64,355,1152,82,42,C.navy);
txt(s,`${summary.documents} 篇自编资料，${summary.questions} 道固定问题\n中文向量检索、Cross-Encoder 重排、本地生成`,64,466,1120,91,27,C.muted);
txt(s,'成员甲  系统与统筹     成员乙  数据与检索\n成员丙  重排序与演示   成员丁  实验与评价',64,602,1152,70,23,C.navy);
s.speakerNotes.text='甲，约15秒：我们的题目是课程资料问答助手，选择重排序方向。我们用自编学习资料实现了本地RAG，并对同一批候选做有无重排序的对照。四位成员按系统、检索、重排和评价分工。姓名和组号在提交前替换为真实信息。校徽校名原图来源：https://www.gdut.edu.cn/images2020/logo.png；官方页面：https://www.gdut.edu.cn/xxgk/xhxxxg.htm。本PPT为课程汇报自制设计，不是校方发布的官方模板。';
}

// 2. 问题与范围
{
const s=slide('检索到相关资料，仍可能回答不准',`甲，约25秒：系统希望回答有可核对的来源。我们关注两个环节：正确资料是否排在前面，生成模型能否正确利用资料。知识库和题目是自编教学数据，不是教师课件或外部盲测。来源：${sources.rag}`);
txt(s,'本次问题',64,170,380,52,30,C.teal,true);
txt(s,'同一批候选中，重排序能否\n改善前几名的相关性？',64,238,650,112,38,C.navy,true);
txt(s,'检索指标与生成质量分开评价。\n同步显示片段编号，可回看原文。',64,405,650,104,29,C.muted);
txt(s,'20',880,172,300,115,96,C.teal,true);txt(s,'篇自编中文学习资料',880,300,310,48,24);
txt(s,'10 + 2',850,407,366,96,66,C.navy,true);txt(s,'有依据问题 + 资料外问题',850,510,366,48,23);
txt(s,'范围：纯文本、小规模精确检索。未部署 Milvus，未实现多模态解析。',64,604,1152,38,22,C.muted);
}

// 3. 系统流程
{
const s=slide('RAG 系统流程',`乙，约25秒：离线将文档切分并用BGE编码，保留文档编号和字符位置，矩阵与元数据持久化。在线编码问题，召回10个，再按两种方式选3个上下文，最后由同一个Qwen模型生成。向量库采用NumPy精确扫描。来源：${sources.bge}；${sources.sbert}`);
txt(s,'离线建库',64,150,250,46,28,C.teal,true);
diagram(s,['资料读取','字符切分','BGE 编码','向量与来源持久化'],218,[210,210,210,384]);
txt(s,'在线问答',64,365,250,46,28,C.teal,true);
diagram(s,['问题编码','召回 10 个','原序 / 重排','选 3 个','Qwen 回答'],430,[180,180,220,160,228]);
txt(s,`索引规模：${summary.chunks} 个片段，${summary.vector_dim} 维向量。配置或语料变化后自动换用新缓存。`,64,592,1152,52,23,C.muted);
}

// 4. 分块和余弦
{
const s=slide('Chunk 与 Embedding 的实现取舍',`乙，约40秒：size=180与overlap=36在这里指字符，不是token。片段太小容易切断证据，太大容易带入无关信息。重叠缓解边界问题但带来重复。BGE使用CLS池化并L2归一化，此时点积等于余弦。查询加检索指令，文档不加。不要把相似度当答案正确概率。来源：${sources.bge}`);
table(s,[['环节','本项目配置','主要取舍'],['Chunk','180 字符，重叠 36 字符','证据完整性与冗余'],['Embedding','BGE-small-zh-v1.5，CLS + L2','问题和文档使用同一语义空间'],['检索','归一化向量精确点积扫描','便于解释，规模大时需优化']],64,168,1152,294,[170,510,472]);
txt(s,'cos(q, d) = (q · d) / (‖q‖ ‖d‖)',64,506,1152,64,38,C.teal,true);
txt(s,'L2 归一化后：cos(q, d) = q · d',64,590,1152,44,27,C.muted);
}

// 5. 原理
{
const s=slide('Bi-Encoder 召回，Cross-Encoder 精排',`丙，约25秒：Bi-Encoder独立编码，可提前计算文档向量。Cross-Encoder把问题与片段作为文本对输入，逐对评分，所以只重排候选。两种分数的量纲不同，不能直接比较。本项目模型为${summary.models.reranker}。来源：${sources.ce}；${sources.sbert}`);
table(s,[['比较项','Bi-Encoder','Cross-Encoder'],['输入','问题、文档分别输入','问题与候选联合输入'],['输出','可独立保存的向量','文本对相关性分数'],['使用位置','全库候选召回','小批候选精排'],['本次候选','同一批 10 个','重排后选择前 3 个']],64,163,1152,353,[190,481,481]);
txt(s,'边界：初次召回没有正确证据，重排序无法把它补回来。',64,566,1152,64,30,C.orange,true);
}

// 6. 对照设计
{
const s=slide('固定其他条件，只改变是否重排序',`丁，约15秒：两组共享候选、生成器和提示词，上下文都是3个，只改变排序。检索指标按预标注文档计算，仅针对10道有依据题。资料外题单独检查。`);
table(s,[['控制项','基础 RAG','加入 Rerank'],['初次候选','同一批向量召回前 10 个','共享相同候选'],['上下文','按余弦选前 3 个','按重排分数选前 3 个'],['生成','Qwen2.5-0.5B，贪心解码','相同模型、提示词与长度上限'],['评价','文档级 Hit@1 / Hit@3 / MRR@3','同一标注，保留全部题目']],64,160,1152,337,[200,476,476]);
txt(s,'模型预热后计时，加载与建库单独记录。\n小样本、单次运行的耗时不等于严格性能基准。',64,546,1152,94,26,C.muted);
}

// 7. 实际结果
{
const s=slide('实测检索结果',`丁，约20秒：数值来自results/summary.json，分母是10道有依据题。两组Hit@3均为100%，MRR均为1.000，在这个题集上已达上限，不能据此证明重排普遍无效。平均重排约${summary.mean_rerank_s.toFixed(2)}秒，查询耗时还受生成长度影响。`);
table(s,[['指标（10 道有依据题）','基础 RAG','加入 Rerank'],['Hit@1',pct(summary.baseline.hit1),pct(summary.rerank.hit1)],['Hit@3',pct(summary.baseline.hit3),pct(summary.rerank.hit3)],['MRR@3',summary.baseline.mrr3.toFixed(3),summary.rerank.mrr3.toFixed(3)],['平均查询耗时（12 题）',summary.baseline.mean_total_s.toFixed(2)+' 秒',summary.rerank.mean_total_s.toFixed(2)+' 秒']],64,162,1152,370,[500,326,326]);
txt(s,`初次召回 Hit@10：${pct(summary.candidate_hit10)}    平均重排耗时：${summary.mean_rerank_s.toFixed(3)} 秒`,64,568,1152,45,27,C.teal,true);
txt(s,'文档级相关标注。完整片段、回答、参数与计时随作业保存。',64,628,1152,31,21,C.muted);
}

// 8. 现场演示
{
const r=probes.find(r=>r.id===evidence.rank_demo_id);const s=slide('现场演示：第 4 名片段升至第 1 名',`丙，约75秒，含切屏与现场运行：先运行Notebook的补充排序示例“${r.question}”，D08-C02由原第4名升至第1名。此例从12条口语化探索查询中选取，仅解释排序机制，不计入固定题集统计。再运行Q10的生成对比，查看回答和原文。若等待较久，切到保存的实验预览并说明。`);
txt(s,r.question,64,145,1152,98,32,C.navy,true);
table(s,[['名次','基础候选片段','重排序候选片段'],...Array.from({length:3},(_,i)=>[String(i+1),r.baseline_context[i].id+' '+r.baseline_context[i].title.slice(4),r.rerank_context[i].id+' '+r.rerank_context[i].title.slice(4)])],64,268,1152,240,[100,526,526]);
txt(s,'D08-C02：原排名 4，重排后排名 1',64,548,1152,51,29,C.teal,true);
txt(s,'补充探索案例，不计入固定 12 题统计。随后查看 Q10 的回答与原文。',64,615,1152,37,23,C.muted);
}

// 9. 发现与思考
{
const s=slide('排名变化与回答质量需要分别检查',`丁，约20秒：保存的24条回答已由助手阅读初评，需要组员复核，不是独立盲评。满分题数两组均为3/10。Q10解释有改善，Q06却仍把引用与证据混淆。资料外题也各有一道编造，检索命中不能替代答案核验。`);
txt(s,evidence.answer_finding,64,165,1152,120,37,C.navy,true);
txt(s,'助手阅读初评，需组员复核，非独立盲评。',64,287,1152,33,21,C.muted);
txt(s,evidence.case_finding,64,330,1152,154,29,C.muted);
txt(s,'自主讨论：资料不足时，提示词能否保证可靠拒答？',64,540,1152,52,30,C.teal,true);
txt(s,evidence.oos_finding,64,608,1152,48,24,C.muted);
}

// 10. 收束
{
const s=slide('结论与局限',`丁，约10秒：结果只适用于自编小样本。主要误差在生成端。后续需要真实课件、独立题集和双人核验。四人发言预算合计约4分30秒。完整参考资料见交付包。`);
txt(s,evidence.conclusion,64,162,1152,126,40,C.teal,true);
txt(s,'自编资料与题目共同构造，样本仅 12 道。\n0.5B 生成模型能力有限，引用与拒答仍需核验。\n固定顺序、单次 CPU 计时，仅用于本次教学观察。',64,337,1152,190,29,C.muted);
txt(s,'下一步：真实课件题集、双人复核、更多重复实验。',64,589,1152,58,30,C.navy,true);
}

await fs.mkdir(path.join(build,'slides'),{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
  const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(build,'slides',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const draft=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(draft);
const finalPath=path.join(root,'课程汇报.pptx');
await finalizePresentation({workspaceDir,candidatePath:draft,finalPath,pythonExecutable:RUNTIME_PYTHON,
integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[4,5,6,7,8].flatMap(n=>['--require-native-table-slide',String(n)])],
explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[4,5,6,7,8],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(build,'deck.validation.json')});
console.log(finalPath);
