# 模型恢复

GitHub 仓库不包含约 1.59 GB 的三个模型权重。先安装运行依赖，再执行 `python download_models.py`。下载器使用此目录 manifest.json 内的固定版本、大小与 SHA256，恢复 embedding、reranker、generator 三个模型。

本地协作总文件夹已保存完整权重；若有该文件夹，也可以将其 models 内容复制到这里。模型卡和许可在各子目录中保留，模型使用遵循对应许可。
