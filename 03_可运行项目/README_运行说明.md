# 可运行项目

请保持本目录内部结构：代码、Notebook、data、models、cache、results 同级。根路径由代码文件位置确定。

## 本机

双击 `打开Notebook.cmd` 或 `启动现场问答.cmd`。优先使用本目录 `.venv`，其次使用整理前工作区的 `.runtime`。CPU 模型加载需要等待；课前预热，现场只运行提问单元格。退出问答输入 q。

## 换电脑

完整复制协作总文件夹。安装 Windows 64 位 Python 3.11，在本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_models.py
.\.venv\Scripts\python.exe -m unittest test_core.py
.\.venv\Scripts\python.exe rag_engine.py
```

GitHub 版不包含权重。安装依赖后运行 `.\.venv\Scripts\python.exe download_models.py`，下载器使用 manifest.json 的固定版本与散列，或从完整本地副本复制 models。

## 重跑

```powershell
.\.venv\Scripts\python.exe run_experiment.py --output results_rerun_v2
```

原始 results 保留为基线；不要直接覆盖。`requirements-lock.txt` 记录本次完整环境，`requirements.txt` 为运行依赖。

项目不读取 Codex 或 CC Switch 配置，无需 API 密钥。向量索引是 NumPy 精确扫描，未部署 Milvus。

## 结果文件

- results/summary.json：实验配置、环境、聚合指标与计时。
- results/raw_results.json：固定 12 题，完整候选、上下文与 24 条生成回答。
- results/answer_review.json：助手阅读初评，需要组员复核。
- results/supplementary_ranking_probes.json：额外探索查询，S07 排序案例。
- 实验结果预览.html：保存结果展示，不能当作现场推理。
