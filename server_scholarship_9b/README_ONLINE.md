# 9B 奖学金问答：GitHub 在线版

网页入口：**https://licop2022.github.io/gdut-rag-coursework/**

网页由 GitHub Pages 托管；实时推理由实验室服务器提供，需要部署者给出的访问密钥。GitHub 不运行 9B 模型。源码不包含密钥、SSH 配置、模型权重及私人服务器日志。

## 使用

1. 打开网页，输入访问密钥，点击“连接服务器”。
2. 在“不同 chunk，回答有什么变化？”中填写相同问题与两组参数，运行 A/B 对比。两组统一使用所选模型和检索路线。
3. 结果并排展示答案、高亮文字差异、原文证据差异以及块数、上下文字数、生成耗时等；可下载真实 JSON 记录。
4. 页面下方可修改当前问答的分块，预览后重建索引，并使用基础 RAG / Rerank RAG 生成两组回答。

模型为 Qwen3.5-9B，Embedding 为 BGE-M3，重排序为 bge-reranker-v2-m3。默认使用原始9B，可选择本次LoRA实验adapter。知识范围是用户提供手册的奖学金评审办法，印刷页193—198。网页为课程实验，不是学校官方服务。

答案和证据的黄色标记说明两组内容不同，不代表自动评定正确性。两组按 A→B 顺序复用同一模型，耗时受共享GPU、缓存和预热影响。对比结果独立保存，不改变当前问答配置，不写入历史固定测试指标。

## 部署结构

- `../docs/index.html`：公开网页，由 `build_public_site.py` 从 `demo.html` 生成。
- `public-config.json`：公开后端URL，不含密钥。
- `web_demo.py`：服务器回环地址上的模型服务。
- `public_gateway.py`：独立回环网关，校验访问密钥、网页来源、JSON大小，限制并发和请求频率；HTTPS隧道只连接该网关。
- `chunk_config.py`、`chunk_compare.py`：版本化分块和隔离的A/B实验。
- `.public-private/access.key`：部署者私有密钥文件，必须排除于Git，Linux权限为600。

目前后端使用 **Cloudflare Quick Tunnel 临时地址**。隧道停止或重启后，URL可能变化；更新 `public-config.json` 的 `api_base`，重新运行 `python build_public_site.py`，推送 `docs` 后即可更新网页。服务器、网关、隧道任何一个离线时，网页可打开但不能生成回答。长期运行应由实验室管理员配置固定域名及受管理的隧道。

## 复现与维护

服务器使用独立Python环境；模型文件放在本目录 `models/`。通过 `download_models.py` 下载并校验模型；`prepare_source.py` 和 `prepare_experiment.py` 用于重建资料及数据。模型推理环境与训练依赖见 `requirements-server.txt`，安装适配显卡驱动的PyTorch，再安装其余依赖。快速验证：

```bash
python -m unittest test_chunk_config test_chunk_compare -v
GDUT_GPU=2 bash start_demo.sh
```

公开网关从 `cache/demo_endpoint.json` 读取本机模型服务端口。网关和隧道启动由部署者管理；不要将未加鉴权的 `web_demo.py` 直接公开。访问密钥只应通过私下渠道分享，不放在仓库、URL或网页配置里。网页只在当前标签页的sessionStorage中保存密钥。

Linux可用下列命令在模型已启动且官方cloudflared已安装到`.tools/cloudflared`后启动公开入口：

```bash
bash start_public.sh
```

GitHub Pages 设置为 `main` 分支的 `/docs` 目录。只发布经过选择的源码、数据与网页，不上传运行环境、权重、adapter、私密配置或原始整本PDF。
