# GDUT RAG 课程作业

四人小组中文课程资料问答项目：对比基础 RAG 与 Cross-Encoder 重排序。包含汇报 PPT、四人讲稿、LaTeX 公式、Notebook、Python 实现、教学语料、固定题集与真实实验结果。

## 9B 在线问答与 chunk 对比

**[打开在线网页](https://licop2022.github.io/gdut-rag-coursework/)** · [9B源码及部署说明](server_scholarship_9b/README_ONLINE.md)

新版支持 Qwen3.5-9B 实时问答、基础 RAG / Rerank 对照、可调 chunk 和 A/B 分块对比，答案与证据差异并排高亮。输入部署者提供的访问密钥即可连接实验室服务器。GitHub Pages托管网页，推理依赖服务器及HTTPS通道在线；源码不包含密钥或模型权重。

下方原0.5B实验材料及指标保留历史状态，与新9B实验分开。

## 从这里开始

| 目标 | 入口 |
|---|---|
| 查看当前汇报 | [PPT 重制版](01_汇报材料/课程汇报_重制版.pptx)，10 页主讲、2 页备答 |
| 四人排练 | [配套讲稿](01_汇报材料/四人讲稿_重制版.md)，主讲约 270 秒 |
| 修改报告 | [实验报告](02_书面报告/实验报告.md) |
| 查看与运行代码 | [可运行项目](03_可运行项目)，[Notebook](03_可运行项目/RAG课程作业.ipynb) |
| 浏览保存的输出 | 下载后打开 [实验结果预览.html](03_可运行项目/实验结果预览.html) |
| 修改 PPT 生成源码 | [排版与生成源码](04_排版与生成源码/README_排版源码.md) |
| 组员接手 | [修改路线](99_核验与交接/组员修改路线.md) |
| Agent 接手 | [AGENTS.md](AGENTS.md) 与 [交接说明](99_核验与交接/AGENT_HANDOFF.md) |
| 阅读原始课件与教学代码 | [课程资料分类索引](06_课程课件与教学代码/README.md)，与本组汇报及实验分开存放 |
| 对照课程要求 | [附件转录](05_课程要求与规划/课程要求_附件转录.md) |

## 快速运行

建议 Windows 64 位 Python 3.11。克隆仓库后，在 `03_可运行项目` 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_models.py
.\.venv\Scripts\python.exe -m unittest test_core.py
.\.venv\Scripts\python.exe rag_engine.py
```

下载三个模型约 1.59 GB；推理使用本地模型，无需 API 密钥。下载器按 `models/manifest.json` 中保存的版本与 SHA256 恢复文件。模型权重、Python 环境、node_modules、向量缓存与临时草稿不进入 Git；其他协作材料保留。

下载模型后，可双击根目录 `打开Notebook.cmd` 或 `启动现场问答.cmd`。新实验请另存：

```powershell
.\.venv\Scripts\python.exe run_experiment.py --output results_rerun_v2
```

## 已保存结果与适用范围

20 篇自编教学资料、37 个片段，固定 12 题，其中 10 道有依据、2 道资料外题。两组文档级 Hit@1、Hit@3、MRR@3 均为 1.0；回答初评满分均为 3/10。评分是助手阅读初评，待组员复核，并非独立盲评。S07 为额外探索案例，不计入固定题集。

此项目用于课程学习。实验数据与问题为自主整理；教师原始课件另见 `06_课程课件与教学代码`，未据此替换或重跑原实验，结果不代表外部盲测。不要把文档命中率当作答案正确率，或用单个排序成功例子声称普遍提升。

## 协作修改

PPT 可直接用 PowerPoint/WPS 编辑；公式 LaTeX 源码在 `01_汇报材料/公式`。重新运行 JS 会按源码生成一版新的 PPT，手工编辑不会自动回写 JS，需明确当前采用哪份版本。

真实姓名、组号及分工由组员确认后填写。`90_历史版本` 仅供追溯，旧进度不表示当前仍未完成。

## 素材与第三方依赖

学校标识与校园图片来源见 [素材来源](01_汇报材料/assets/来源.txt)，用于课程展示，保留原比例和水印；不将学校素材重新授权为项目自有资产。本仓库不冒称校方官方模板。模型来源、模型卡与许可见 `03_可运行项目/models` 及 [参考资料](02_书面报告/参考资料.md)。第三方素材、模型及依赖遵循各自许可。

