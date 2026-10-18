# PPT 生成与修改

主文件 `build_deck_v2.mjs` 使用 Codex 运行时的 artifact-tool 生成 1280×720 幻灯片；当前 10 页主讲、2 页备答。它从 `../03_可运行项目/results` 读取真实结果，从 `../01_汇报材料/assets` 读取素材，用 MathJax 将 LaTeX 生成 SVG。

普通排版修改可直接编辑 PPT。如用代码重建：

1. 在当前 agent 环境读取 presentation skill，并找到 artifact-tool 的 node_modules、该 skill 目录、Node 与 Python。
2. 将 `runtime-settings.example.json` 复制为 `runtime-settings.json`，填入本机路径。这个本地配置已在 .gitignore 排除。
3. 在 `math-deps` 目录运行 `pnpm install --frozen-lockfile`，或根据 package.json 安装 MathJax 依赖。
4. 回到此目录，运行以下命令：

```powershell
node build_deck_v2.mjs
node finalize.mjs
```

第一步将草稿和逐页预览写入私有 `.build`，第二步校验并输出 `../01_汇报材料/修订输出/课程汇报_修订_时间戳.pptx`。先逐页查看渲染，再确定正式版并同步讲稿。artifact-tool 和校验器依赖 agent 环境，并非此仓库内置的通用独立编译器。

LaTeX 源在 `../01_汇报材料/公式/公式源码.tex`，与 JS 的 LATEX 字典保持同步。手工编辑 PPT 不会自动回写 JS，重建前应确认以哪个版本为准。
